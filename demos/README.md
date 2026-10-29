# WebGL demos

Each folder `demos/<name>/` is a CGP scene compiled with Emscripten into
`content/assets/<name>-demo/` (index.html, project.js/.wasm/.data) together with a
`poster.png` captured in headless Chromium. A page shows it with the marker

```markdown
<!-- demo: <name> -->
```

which both renderers turn into a click-to-load figure (the poster, then an iframe).

## Build

```sh
make demos                                   # every demo
.venv/bin/python demos/build.py NAME ...     # some demos (log: build/demos/build.log)
CGP_DEMO_BUILD_DIR=/tmp/x .venv/bin/python demos/build.py NAME   # parallel workers: one build dir each
```

The CGP library is compiled once per build directory (about 10 s), each demo links it
(a few seconds). The script exits with an error if a demo logs a JavaScript error or does not
start within 30 s. Look at the poster (`content/assets/<name>-demo/poster.png`): it is what the
reader sees first.

## Demos of the how-to pages: generated scenes

For a how-to page whose code blocks start with a location comment (`// scene.cpp - add at the
end of initialize()`, see `tests/recipes/apply_recipe.py`), `build.py` regenerates
`scene.hpp` and `scene.cpp` before the build: the cgp-2027 template with the code of the page
applied, exactly as a student would do. Do not edit these two files (their first line says
so): change the page. The demo folder keeps only its `assets/`, `shaders/` and `origin.txt`
(origin and license of the assets, copied as a comment at the top of `scene.cpp`).
`make recipes` builds the same projects natively, as a fast test of the pages.

## Content of a demo folder

The folder holds only what differs from the cgp-2027 template project (`../cgp-2027/src`,
`../cgp-2027/shaders`), staged over a copy of it:

| File | Role |
|---|---|
| `scene.hpp`, `scene.cpp` | required: the scene (same structure as the template) |
| other `.cpp` / `.hpp` | added to, or replacing, the files of `src/` |
| `shaders/` | added to the default shaders (`shaders/mesh/`, `shaders/single_color/`) |
| `assets/` | preloaded as `assets/` (textures, OBJ files): keep it small (< 3 MB) |
| `poster.png` | optional: a poster captured by hand, used instead of the automatic one (a scene that shows nothing before interaction, as sketching) |

Paths in the code: `project::path + "shaders/..."`, `project::path + "assets/..."`.

## Rules

- A demo of a How-to page runs **the code of the page**: same names, same values (generated,
  see above). For a hand-written demo, mark the page sections in comments (`// recipe: 2. Create the mesh`). If the code of the page does not
  compile or does not work, fix the page (and say why in your report), never only the demo.
- Keep the template GUI (ImGui window) and the orbit camera unless the page is about another
  camera: the reader must be able to interact.
- Frame the scene so that the poster (800 x 500) shows the result clearly.
- No modification of `../cgp-2027`. A bug of CGP is reported on its repository
  (github.com/drohmer/cgp-2027, issues).
- Assets: only files that may be redistributed, taken from the public repositories of the
  author (github.com/drohmer/csc43043ep-lab-code, github.com/drohmer/epita_ani3d_lab_code-2027,
  or ../cgp-2027). Note their public origin in `origin.txt` (or a comment at the top of
  `scene.cpp`): the documentation is public and cites only public sources.
