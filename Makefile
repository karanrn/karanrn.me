POSTS_DIR := content/posts

GOODREADS_USER := 37190680

# Keep in sync with hugo-version in .github/workflows/gh-pages.yaml.
HUGO_VERSION := 0.168.0
# Oldest Hugo with css.Sass, which layouts/partials/docs/html-head.html needs.
HUGO_MIN_VERSION := 0.128.0

# Everything after `post` on the command line is the title: `make post My New Post`.
# `make post title="My New Post"` also works.
ifeq (post,$(firstword $(MAKECMDGOALS)))
  title ?= $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
endif

# Shell-safe (single-quoted) title, and the same with `"` escaped for YAML.
sq_title = $(subst ','\'',$(title))
yaml_title = $(subst ",\",$(sq_title))

slug = $(shell echo '$(sq_title)' | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+|-+$$//g')

.PHONY: post covers books check install-hugo serve build

post:
	@if [ -z "$(strip $(title))" ]; then echo 'usage: make post <title>'; exit 1; fi
	@file="$(POSTS_DIR)/$(slug).md"; \
	if [ -e "$$file" ]; then echo "$$file already exists"; exit 1; fi; \
	printf -- '---\ntitle: "%s"\ndate: %s\ncategories: []\ndraft: true\n---\n' \
		'$(yaml_title)' "$$(date +%Y-%m-%d)" > "$$file"; \
	echo "created $$file"

# Fetch covers for games in data/games.yaml that don't have one yet.
covers:
	@command -v python3 >/dev/null || { echo 'python3 not found'; exit 1; }
	@python3 -c 'import yaml, PIL' 2>/dev/null || { echo 'missing python packages: pip install pyyaml pillow (or apt install python3-yaml python3-pil)'; exit 1; }
	python3 scripts/fetch-game-covers.py

# Rewrite data/books.yaml from the Goodreads read and currently-reading shelves.
books:
	@command -v python3 >/dev/null || { echo 'python3 not found'; exit 1; }
	@python3 -c 'import yaml' 2>/dev/null || { echo 'missing python package: pip install pyyaml (or apt install python3-yaml)'; exit 1; }
	python3 scripts/fetch-books.py $(GOODREADS_USER)

check:
	@command -v go >/dev/null || { echo 'go not found: install it from https://go.dev/dl/'; exit 1; }
	@command -v hugo >/dev/null || { echo 'hugo not found: run `make install-hugo`'; exit 1; }
	@hugo version | grep -q '+extended' || { echo "hugo is not the extended build (needed for SCSS): $$(hugo version)"; echo 'run `make install-hugo`'; exit 1; }
	@v=$$(hugo version | sed -E 's/^hugo v([0-9.]+).*/\1/'); \
	if [ "$$(printf '%s\n' $(HUGO_MIN_VERSION) $$v | sort -V | head -1)" != $(HUGO_MIN_VERSION) ]; then \
		echo "hugo $$v is too old, need >= $(HUGO_MIN_VERSION): run \`make install-hugo\`"; exit 1; \
	fi; \
	echo "ok: $$(go version | cut -d' ' -f3), hugo $$v extended"

# Extended build needs cgo, hence a C compiler.
install-hugo:
	@command -v go >/dev/null || { echo 'go not found: install it from https://go.dev/dl/'; exit 1; }
	@command -v gcc >/dev/null || { echo 'gcc not found: needed to build hugo extended'; exit 1; }
	CGO_ENABLED=1 go install -tags extended github.com/gohugoio/hugo@v$(HUGO_VERSION)

serve: check
	hugo server -D

# Syncs the reading page first; if Goodreads is unreachable it builds with the committed data.
build: check
	@$(MAKE) --no-print-directory books || echo 'warning: Goodreads sync failed, using existing data/books.yaml'
	hugo --minify

# Title words passed to `make post` become goals; let them do nothing.
ifeq (post,$(firstword $(MAKECMDGOALS)))
%:
	@:
endif
