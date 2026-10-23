POSTS_DIR := content/posts

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

.PHONY: post check install-hugo serve build

post:
	@if [ -z "$(strip $(title))" ]; then echo 'usage: make post <title>'; exit 1; fi
	@file="$(POSTS_DIR)/$(slug).md"; \
	if [ -e "$$file" ]; then echo "$$file already exists"; exit 1; fi; \
	printf -- '---\ntitle: "%s"\ndate: %s\ncategories: []\ndraft: true\n---\n' \
		'$(yaml_title)' "$$(date +%Y-%m-%d)" > "$$file"; \
	echo "created $$file"

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

build: check
	hugo --minify

# Title words passed to `make post` become goals; let them do nothing.
ifeq (post,$(firstword $(MAKECMDGOALS)))
%:
	@:
endif
