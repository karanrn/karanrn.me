# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Personal blog (karanrn.me) built with Hugo, using the `hugo-book` theme with heavy local overrides.

## Commands

- `make post <title>` (or `make post title="..."`) — create `content/posts/<slugified-title>.md` with the standard front matter (`title`, `date`, `categories`, `draft: true`). Use this instead of `hugo new`, and remove `draft: true` to publish.
- `make serve` — local dev server at http://localhost:1313 with live reload (includes drafts)
- `make build` — production build (`hugo --minify`) into `public/`, the same command CI runs
- `make covers` — run `scripts/fetch-game-covers.py`: for games in `data/games.yaml` without a cover, add the `image:` field and download the cover (Steam portrait art, falling back to the Wikipedia infobox image), saved as a 300×450 JPEG in `assets/images/games/`. Never overwrites existing covers. `--dry-run` shows what it would fetch. Needs `pyyaml` and `pillow`.
- `make books` — run `scripts/fetch-books.py` to regenerate `data/books.yaml` from the Goodreads RSS feeds of the `read` and `currently-reading` shelves (user `GOODREADS_USER` in the Makefile; the profile must be public). The file is generated, so never hand-edit it. `make build` runs it first, and so does CI on every push. A failed sync only warns, and the build uses the committed copy. The script also refuses to overwrite the file if the read shelf shrinks by more than 20% (a sign of a broken feed). The committed copy is just a fallback snapshot.
- `make check` — checks for `go` and for Hugo **extended** at or above `HUGO_MIN_VERSION`. `serve` and `build` run it first.
- `make install-hugo` — `go install -tags extended` of `HUGO_VERSION` (needs cgo/gcc). A plain `go install` produces a non-extended Hugo that can't compile the theme's SCSS.

There are no tests or linters; verify changes by building and viewing the site.

CI (`.github/workflows/gh-pages.yaml`) pins Hugo extended to the same version as `HUGO_VERSION` in the Makefile, so keep the two in sync. Hugo before 0.128 won't work because the head partial uses `css.Sass`.

## Deployment

A push to `master` syncs Goodreads, builds the site and publishes `public/` to the `gh-pages` branch via `peaceiris/actions-gh-pages`. PRs build but don't deploy. `static/CNAME` sets the custom domain. `public/` and `resources/_gen/` are generated and gitignored, so never edit them.

## Architecture

- **Theme is vendored, not a submodule.** `themes/hugo-book/` is committed directly. `.gitmodules` still lists an old `themes/devise` submodule that no longer exists, which is stale. Don't edit files under `themes/`; override them by putting a file at the same path under `layouts/`.
- **Layout overrides** (`layouts/`) replace the theme's look:
  - `_default/baseof.html` replaces the theme's sidebar menu with a top `site-header` nav. That nav has a hardcoded `about` link plus the `menu.after` entries from `config.yaml` (external: movies) and page front matter (reading, games). It also loads `/custom.css` and holds the Google Analytics tag and the site-verification meta tag.
  - `index.html` is the landing page: content from `content/_index.md`, followed by a reverse-chronological list of every post.
  - `posts/list.html` and `posts/single.html` render posts; `_markup/render-link.html` makes external links open in a new tab.
  - `partials/docs/post-meta.html` and `html-head-title.html` override theme partials (the author name is hardcoded).
  - `partials/docs/html-head.html` is a copy of the theme's version with `resources.ToCSS` (removed in newer Hugo) replaced by `css.Sass`. When updating the theme, re-copy that file and apply the same change. It also emits its own Open Graph/Twitter tags in place of `_internal/opengraph.html`. Description: front matter `description`, else the summary truncated to 160 chars, else `params.description`. Image: front matter `image` (a static path, also shown at the top of posts by `post-meta.html`), else `params.ogImage`. Titles are `<page title> · <params.author>` (just the author on the home page), from `html-head-title.html`.
- **Games page** (`/games/`): the cover grid is rendered by `layouts/_default/games.html` from `data/games.yaml`, in file order, with source covers at `assets/images/games/` (300×450 JPEGs, never published directly). The layout resizes each to 150/200/300px WebP (q60) and serves them via `srcset`/`sizes`, so browsers download only the size they display. The page body, with the "uses" section, is in `content/games/index.md`. To add a game, add a `- title:` entry and run `make covers`. The build fails if a listed cover is missing. If the wrong cover is picked, set `steam_id` or `cover_url` on the entry. Optional fields: `rating` (0.5–5 in steps of 0.5, rendered as ★/½; an invalid value fails the build) `status` (`playing` or `stopped`; `stopped` requires a `note` saying where, which is shown under it), `favorite: true` (also listed in the "favorite games" row), and `note` (otherwise shown on hover). Invalid values fail the build.
- **Reading page** (`/reading/`, the nav's "reading" link): `layouts/_default/books.html` renders `data/books.yaml` as text rows (no covers): currently reading first, then read books grouped by the `year` field the sync script sets ("undated" for books with no finish date). The row star style reuses `.game-rating`.
- **Styling** lives entirely in `static/custom.css` (plain CSS, IBM Plex Mono, beige `#f3f0e8` background), loaded after the theme CSS. The theme's SCSS hooks (`assets/_custom.scss`) are not used.
- **Content:** posts are in `content/posts/*.md` with front matter `title`, `date`, `description` (for search/link previews), `categories` (only `"tech"` and/or `"life"`), and optional `image`. Their permalinks are `/posts/:filename/`. Taxonomy and term pages are disabled in `config.yaml`, so `categories` doesn't generate pages. Raw HTML in markdown is allowed (`goldmark.renderer.unsafe: true`).
