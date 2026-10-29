# CGP documentation

Sources of the documentation of [CGP](https://github.com/drohmer/cgp-2027) (Computer Graphics
Programming), a lightweight C++ library to learn and prototype interactive 3D graphics with
OpenGL. The documentation has four parts:

- **Get started**: install, compile and tour a first scene; troubleshooting.
- **Understand**: how a 3D scene is built and rendered (CPU to GPU, shaders, cameras,
  transforms, hierarchies, time, interaction).
- **How-to** and **Examples**: recipes and complete programs, each with a live WebGL demo.
- **Reference**: every type of CGP with the functions that apply to it, generated from the
  C++ sources.

The site is static: a generator turns the Markdown pages and a model of the API into HTML,
searchable offline (Pagefind).

## How it is built

```text
 ../cgp-2027/cgp (.hpp)                       editorial/*.yaml (hand-curated)
        |                                          |
        v                                          |
    Doxygen (XML, parser only)                     |
        |                                          |
        v                                          v
 +---------------------------------------------------------+
 | docmodel/  cgp-docmodel                                  |
 |  aliases, type -> functions, const variants, categories, |
 |  descriptions, checks of the pages in content/           |
 +---------------------------------------------------------+
        |
        v
 build/api.json (schema docmodel/schema/api.schema.json)   content/*.md (pages)
        |                                                    |
        +--------------------+-------------------------------+
                             v
          renderers/lhtml  or  renderers/starlight  ->  static site
```

Two renderers produce the same site from the same content: `renderers/lhtml`
([lhtml-site](https://github.com/drohmer/lhtml-site), Python, the main one) and
`renderers/starlight` ([Astro Starlight](https://starlight.astro.build), Node).

## Layout

| Folder | Role | Edited by hand? |
|---|---|---|
| `content/` | Pages in Markdown and their figures | yes (text) |
| `editorial/` | Types to document, descriptions, categories, pages of functions | yes (data) |
| `docmodel/` | Python package `cgp-docmodel`: extraction, model, checks, tests | yes (code) |
| `renderers/` | One site generator per folder; reads `build/api.json` and `content/` | yes (code) |
| `demos/` | WebGL demos: one CGP scene per folder, compiled with Emscripten (see `demos/README.md`) | yes (code) |
| `tools/figures/` | Generators of the SVG figures and their color palette | yes (code) |
| `tests/` | Playwright tests on the built sites, native build of the how-to code | yes (code) |
| `build/` | Everything generated: Doxygen XML, `api.json`, reports | **never** |

## Build the site

Requirements: Python 3.10 or more, [Doxygen](https://www.doxygen.nl), and the CGP sources next
to this folder (or set `CGP_SOURCE_DIR` to their `cgp/` folder):

```sh
git clone https://github.com/drohmer/cgp-2027.git
git clone https://github.com/drohmer/cgp_documentation.git
cd cgp_documentation
make setup        # once: .venv, cgp-docmodel, lhtml-site, Playwright, npm packages
make site-lhtml   # the site in renderers/lhtml/dist
.venv/bin/python -m http.server -d renderers/lhtml/dist 8001   # then open http://localhost:8001
```

`make setup` also installs the npm packages of the Starlight renderer (Node.js needed);
without Node, use the lhtml targets only. The WebGL demos need the
[Emscripten SDK](https://emscripten.org): `make demos` compiles them into `content/assets/`.

## Deploy

The site is published at [graphicscomputing.fr/cgp](https://graphicscomputing.fr/cgp/) (static
files served by nginx). `make deploy` builds the lhtml site with `base_url: '/cgp/'` (the
links of the 404 page start at the root of the server) and uploads it with rsync; the demos
must have been compiled before (`make demos`). The documentation of 2024 is kept in
`/cgp/archive-2024/`, and its old URLs redirect to the new site (nginx). `DEPLOY_HOST`,
`DEPLOY_DIR` and `DEPLOY_URL` set another target.

## Commands

```sh
make verify     # docmodel tests + check + snapshot: must pass after any change
make report     # build/reports/coverage.md (missing descriptions per module...)
make sites      # build both sites
make e2e        # Playwright tests on both sites
make demos      # compile the WebGL demos (Emscripten SDK) and their posters
make e2e-demos  # every demo of the pages starts without error, on both sites
make recipes    # compile the code of the how-to pages natively
make deploy     # build for graphicscomputing.fr/cgp/ and upload it
make help       # all targets
```

## Where to change what

| I want to... | Edit |
|---|---|
| write or fix a guide, a how-to or an example | `content/` |
| describe a function | `editorial/descriptions.yaml` (key = `key` field of `api.json`) |
| fix the category of a function | `editorial/annotations.yaml` |
| document a new type, its figures and common tasks | `editorial/types.yaml` |
| change how functions are attached to types | `docmodel/src/cgp_docmodel/`, then `make verify` |
| change the look of a site | `renderers/<name>/` |

`AGENTS.md` lists the rules of the project (also followed by coding agents), and
`docmodel/README.md` describes the internals of the model.

## License

MIT (see `LICENSE`), as the CGP library. The examples and the course labs cited by the pages
are in their own public repositories:
[epita_ani3d_lab_code-2027](https://github.com/drohmer/epita_ani3d_lab_code-2027) and
[csc43043ep-lab-code](https://github.com/drohmer/csc43043ep-lab-code).
