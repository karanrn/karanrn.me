#!/usr/bin/env python3
"""Download missing game covers for data/games.yaml.

For every entry whose cover is not yet in assets/images/games/:
  1. if it has no `image:` field, one is added (slug of the title + .jpg);
  2. the cover is fetched from, in order:
       - `cover_url:` on the entry, if set
       - Steam (`steam_id:` on the entry, or a store search by title)
       - the infobox image of the game's English Wikipedia article
  3. it is cropped/resized to a 300x450 JPEG, like the existing covers.

Existing covers are never overwritten; delete one to refetch it.

Usage: fetch-game-covers.py [--dry-run]
"""

import difflib
import io
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import yaml
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "games.yaml"
COVERS = ROOT / "assets" / "images" / "games"
SIZE = (300, 450)
UA = "karanrn.me-cover-fetcher/1.0"
STEAM_COVER = "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/{}/library_600x900.jpg"
# Below this title similarity a Steam search hit is treated as no match.
MIN_MATCH = 0.75


def get(url, params=None):
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def get_json(url, params=None):
    return json.loads(get(url, params))


def slugify(title):
    title = title.lower().replace("'", "").replace("’", "")
    return re.sub(r"[^a-z0-9]+", "-", title).strip("-")


def normalize(name):
    """Comparable form of a game name: drop marks, publisher prefixes and edition suffixes."""
    name = re.sub(r"[™®©]", "", name).lower().replace("’", "'")
    name = re.sub(r"^marvel'?s\s+", "", name)
    name = re.sub(r"\b(definitive|director'?s cut|remastered|game of the year|goty|complete)\b.*$", "", name)
    name = re.sub(r"\b(edition)\b", "", name)
    return re.sub(r"[^a-z0-9]+", " ", name).strip()


ROMAN = {"i": "1", "ii": "2", "iii": "3", "iv": "4", "v": "5", "vi": "6", "vii": "7", "viii": "8", "ix": "9", "x": "10"}


def numbers(name):
    """Sequel numbers in a normalized name, with roman numerals as digits ("ii" -> "2")."""
    return {ROMAN.get(w, w) for w in name.split() if w.isdigit() or w in ROMAN}


def steam_search(title):
    """Best-matching Steam app (id, name) for a title, or None."""
    want = normalize(title)
    scored = []
    # Steam's search can miss "II" when the store name says "2", so also try the digit form.
    terms = dict.fromkeys([title, " ".join(ROMAN.get(w.lower(), w) for w in title.split())])
    for term in terms:
        for item in get_json("https://store.steampowered.com/api/storesearch/",
                             {"term": term, "cc": "us", "l": "en"}).get("items", []):
            name = normalize(item["name"])
            # Fuzzy matching can't tell "ii" from "iii", so sequel numbers must agree exactly.
            if numbers(name) != numbers(want):
                continue
            scored.append((difflib.SequenceMatcher(None, want, name).ratio(), item))
    scored = [s for s in scored if s[0] >= MIN_MATCH]
    if not scored:
        return None
    _, best = max(scored, key=lambda s: s[0])
    return best["id"], best["name"]


def steam_cover(app_id):
    try:
        return get(STEAM_COVER.format(app_id))
    except urllib.error.HTTPError:
        return None


def wikipedia_cover(title):
    """Infobox image of the English Wikipedia article for the title, or None."""
    api = "https://en.wikipedia.org/w/api.php"
    try:
        page = get_json(api, {"action": "parse", "format": "json", "prop": "wikitext",
                              "section": 0, "redirects": 1, "page": title})
    except urllib.error.HTTPError:
        return None
    if "error" in page:
        return None
    wikitext = page["parse"]["wikitext"]["*"]
    m = re.search(r"\|\s*image\s*=\s*(?:\[\[(?:File|Image):)?([^|\]\n]+)", wikitext)
    if not m or not m.group(1).strip():
        return None
    info = get_json(api, {"action": "query", "format": "json", "prop": "imageinfo",
                          "iiprop": "url", "titles": "File:" + m.group(1).strip()})
    page = next(iter(info["query"]["pages"].values()))
    if "imageinfo" not in page:
        return None
    return get(page["imageinfo"][0]["url"])


def fetch(game):
    """(image bytes, description of source) for a game, or (None, reason)."""
    title = game["title"]
    if game.get("cover_url"):
        return get(game["cover_url"]), "cover_url"
    if game.get("steam_id"):
        data = steam_cover(game["steam_id"])
        if data:
            return data, f"Steam app {game['steam_id']} (steam_id)"
    else:
        hit = steam_search(title)
        if hit:
            data = steam_cover(hit[0])
            if data:
                return data, f"Steam app {hit[0]} \"{hit[1]}\""
    data = wikipedia_cover(title)
    if data:
        return data, "Wikipedia"
    if game.get("steam_id"):
        return None, f"Steam app {game['steam_id']} has no portrait cover and Wikipedia has none; set cover_url"
    return None, "no cover found on Steam or Wikipedia; set steam_id or cover_url"


def save_cover(data, path):
    im = Image.open(io.BytesIO(data)).convert("RGB")
    ImageOps.fit(im, SIZE, Image.LANCZOS).save(path, quality=82, optimize=True, progressive=True)


def add_image_fields(text, games):
    """Insert `image:` after the title line of entries that lack one, keeping the file's formatting."""
    lines = text.splitlines(keepends=True)
    out, i = [], 0
    for line in lines:
        out.append(line)
        m = re.match(r"^- title:\s*(.+?)\s*$", line)
        if m:
            game = games[i]
            i += 1
            if "image" not in game:
                game["image"] = slugify(game["title"]) + ".jpg"
                out.append(f"  image: {game['image']}\n")
    return "".join(out)


def main():
    dry_run = "--dry-run" in sys.argv[1:]
    text = DATA.read_text()
    games = yaml.safe_load(text) or []
    if sum(1 for l in text.splitlines() if re.match(r"^- title:", l)) != len(games):
        sys.exit(f"{DATA}: every entry must start with a `- title:` line")

    new_text = add_image_fields(text, games)
    if new_text != text and not dry_run:
        DATA.write_text(new_text)

    COVERS.mkdir(parents=True, exist_ok=True)
    missing = [g for g in games if not (COVERS / g["image"]).exists()]
    if not missing:
        print("all covers present")
        return

    failed = 0
    for game in missing:
        path = COVERS / game["image"]
        try:
            data, source = fetch(game)
        except Exception as e:  # network or parse errors: report and move on
            data, source = None, f"error: {e}"
        if data is None:
            failed += 1
            print(f"FAIL  {game['title']}: {source}")
            continue
        if not dry_run:
            save_cover(data, path)
        print(f"{'would fetch' if dry_run else 'saved'}  {path.relative_to(ROOT)}  <- {source}")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
