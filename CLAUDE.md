# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Personal blog (karanrn.me) built with Hugo, using the `hugo-book` theme with heavy local overrides.

## Commands

- `make post <title>` (or `make post title="..."`) — create `content/posts/<slugified-title>.md` with the standard front matter (`title`, `date`, `categories`, `draft: true`). Use this instead of `hugo new`, and remove `draft: true` to publish.
- `make serve` — local dev server at http://localhost:1313 with live reload (includes drafts)
- `make build` — production build (`hugo --minify`) into `public/`, the same command CI runs
- `make check` — checks for `go` and for Hugo **extended** at or above `HUGO_MIN_VERSION`. `serve` and `build` run it first.
- `make install-hugo` — `go install -tags extended` of `HUGO_VERSION` (needs cgo/gcc). A plain `go install` produces a non-extended Hugo that can't compile the theme's SCSS.

There are no tests or linters; verify changes by building and viewing the site.

CI (`.github/workflows/gh-pages.yaml`) pins Hugo extended to the same version as `HUGO_VERSION` in the Makefile, so keep the two in sync. Hugo before 0.128 won't work because the head partial uses `css.Sass`.

## Deployment

A push to `master` builds the site and publishes `public/` to the `gh-pages` branch via `peaceiris/actions-gh-pages`. PRs build but don't deploy. `static/CNAME` sets the custom domain. `public/` and `resources/_gen/` are generated and gitignored, so never edit them.

## Architecture

- **Theme is vendored, not a submodule.** `themes/hugo-book/` is committed directly. `.gitmodules` still lists an old `themes/devise` submodule that no longer exists, which is stale. Don't edit files under `themes/`; override them by putting a file at the same path under `layouts/`.
- **Layout overrides** (`layouts/`) replace the theme's look:
  - `_default/baseof.html` replaces the theme's sidebar menu with a top `site-header` nav. That nav has a hardcoded `about` link plus the external links from `menu.after` in `config.yaml`. It also loads `/custom.css` and holds the Google Analytics tag and the site-verification meta tag.
  - `index.html` is the landing page: content from `content/_index.md`, followed by a reverse-chronological list of every post.
  - `posts/list.html` and `posts/single.html` render posts; `_markup/render-link.html` makes external links open in a new tab.
  - `partials/docs/post-meta.html` and `html-head-title.html` override theme partials (the author name is hardcoded).
  - `partials/docs/html-head.html` is a copy of the theme's version with `resources.ToCSS` (removed in newer Hugo) replaced by `css.Sass`. When updating the theme, re-copy that file and apply the same change.
- **Styling** lives entirely in `static/custom.css` (plain CSS, IBM Plex Mono, beige `#f3f0e8` background), loaded after the theme CSS. The theme's SCSS hooks (`assets/_custom.scss`) are not used.
- **Content:** posts are in `content/posts/*.md` with front matter `title`, `date`, `categories`. Their permalinks are `/posts/:filename/`. Taxonomy and term pages are disabled in `config.yaml`, so `categories` doesn't generate pages. Raw HTML in markdown is allowed (`goldmark.renderer.unsafe: true`).
