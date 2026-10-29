# CGP documentation pipeline.
#   CGP sources -> Doxygen -> cgp-docmodel -> build/api.json -> renderers -> sites
#
# Every target is non-interactive and returns a non-zero status on failure,
# so that an agent or a CI job can chain them.

PY       := .venv/bin/python
DOCMODEL := .venv/bin/cgp-docmodel

.PHONY: help setup model check report snapshot test test-unit verify \
        site-lhtml site-starlight sites e2e demos e2e-demos recipes all clean deploy

help:            ## list targets
	@grep -E '^[a-z0-9-]+:.*## ' $(MAKEFILE_LIST) | sed 's/:.*## /\t/'

setup:           ## create .venv and install cgp-docmodel (editable) with test tools
	test -d .venv || python3 -m venv .venv
	.venv/bin/pip install -q -e "docmodel[test]" playwright "pagefind[extended]" \
		"lhtml-site[math] @ git+https://github.com/drohmer/lhtml-site"   # the docs theme: after 1.0.0
	.venv/bin/python -m playwright install --only-shell chromium
	npm --prefix renderers/starlight ci

# ---------------------------------------------------------------- model (stage 1)
model:           ## build/api.json + build/content_index.json from the CGP sources
	$(DOCMODEL) build

check: model     ## schema, invariants, editorial files, content references
	$(DOCMODEL) check

report: model    ## build/reports/coverage.md
	$(DOCMODEL) report

snapshot: model  ## diff of type relations vs the reviewed golden file
	$(DOCMODEL) snapshot

test-unit:       ## unit tests only (no doxygen needed, < 1 s)
	$(PY) -m pytest docmodel/tests/unit -q

test:            ## all docmodel tests (unit + integration on the real sources, ~2 s)
	$(PY) -m pytest docmodel -q

verify: test check snapshot  ## what must pass before handing back any work on docmodel

# ---------------------------------------------------------------- renderers (stage 2)
site-lhtml: model      ## renderers/lhtml/dist
	$(PY) renderers/lhtml/build.py

# ---------------------------------------------------------------- deployment
# graphicscomputing.fr/cgp/ (nginx, static files). The site is built with its base_url, the
# demos must have been compiled (make demos), archive-2024/ (the previous documentation) is kept.
DEPLOY_HOST ?= damien-scaleway
DEPLOY_DIR  ?= /var/www/graphicscomputing.fr/cgp/
DEPLOY_URL  ?= /cgp/
deploy: model    ## build the lhtml site for graphicscomputing.fr/cgp/ and upload it (rsync)
	@missing=$$(for d in content/assets/*-demo; do test -f $$d/project.wasm || echo $$d; done); \
	  if [ -n "$$missing" ]; then echo "demos not compiled (make demos): $$missing"; exit 1; fi
	CGP_BASE_URL=$(DEPLOY_URL) $(PY) renderers/lhtml/build.py
	rsync -az --delete --filter='P archive-2024/' renderers/lhtml/dist/ $(DEPLOY_HOST):$(DEPLOY_DIR)
	@echo "deployed: https://graphicscomputing.fr$(DEPLOY_URL)  (make site-lhtml to rebuild for local tests)"

site-starlight: model  ## renderers/starlight/dist
	npm --prefix renderers/starlight run build

sites: site-lhtml site-starlight  ## both sites

e2e: sites       ## Playwright tests on both sites (search, filter, links, screenshots)
	$(PY) tests/e2e/test_protos.py

# ---------------------------------------------------------------- WebGL demos (Emscripten)
demos:           ## compile demos/*/ to content/assets/NAME-demo/ + poster.png (first build ~15 s)
	$(PY) demos/build.py

e2e-demos: sites ## every demo of the pages loads and starts without JS error, both sites (~5 s each)
	$(PY) tests/e2e/test_demos.py

recipes:         ## apply the code of every how-to page to the cgp-2027 template and build it (~2 min)
	$(PY) tests/recipes/run_recipes.py

all: verify e2e  ## full pipeline and all tests

clean:           ## remove generated files (build/, sites)
	rm -rf build renderers/lhtml/dist renderers/lhtml/_build renderers/starlight/dist tests/e2e/out
