# Instructions for autonomous agents

Read `README.md` first (pipeline and layout). This file lists the rules for working here
without supervision.

## Before handing back any work

```sh
make verify     # docmodel unit + integration tests, check, snapshot (about 5 s)
make e2e        # only if you touched content/, renderers/ or the model fields (about 30 s)
make recipes    # only if you touched the C++ code of a how-to page (about 30 s)
```

Report the outcome as printed. A failing command is never "probably fine": either fix it
or report it as failing, with its output.

## Rules

1. **Never modify** `../cgp-2027` (the C++ sources) or anything under `build/`
   (generated; `make clean` removes it).
2. **Prefer data over code.** Descriptions, categories, documented types and content-check
   exceptions go in `editorial/*.yaml`. Change `docmodel/src/` only when the logic is wrong
   for a whole class of cases.
3. **Snapshot changes must be explained.** The golden files `docmodel/tests/golden/*.txt`
   (functions, relations, structs, excluded) are the reviewed state of the model.
   If `cgp-docmodel snapshot` reports a diff:
   - after a change of the C++ sources or of `editorial/types.yaml`: check that the diff is
     what the change implies, then `cgp-docmodel snapshot --update`;
   - after a change of `docmodel/src/`: list in your report which relations appeared or
     disappeared and why; update the golden file only if every line of the diff is intended.
4. **One rule, one test.** A new category rule in `categories.py` needs a case in
   `tests/unit/test_categories.py` (`test_every_rule_has_a_case` enforces it). A bug fixed
   in `docmodel/src/` gets a test that failed before the fix: re-introduce the bug, run the
   tests, check that they fail, restore the fix.
5. **The schema is a contract.** Renaming or removing a field of `api.json` is a breaking
   change: bump `schema_version` (in `model.py` and `schema/api.schema.json`) and update
   both renderers in the same change.
6. **Descriptions** (`editorial/descriptions.yaml`): one sentence, present tense, starting
   with a verb or a noun phrase ("Euclidean length of the vector."), plain ASCII. A
   description you drafted without checking the C++ body must be marked by ending it with
   ` [draft]` so that a human reviews it.
7. **Content pages** (`content/*.md`): every inline code name must resolve
   (`cgp-docmodel check` warns otherwise). Fix the page, or add the name to
   `editorial/content_check.yaml` only if it is not a CGP name (OpenGL, GLSL, scene template).
8. Plain ASCII in files (accents allowed in French text). No emoji.

## Useful facts

- `vec2/3/4` are aliases of `numarray_stack<float,N>`, `mat2/3/4` of `matrix_stack<float,N,N>`:
  most functions on vec3 are templates and are flagged `generic`.
- Function keys look like `norm(numarray_stack<T,N> const&)`; find them in `build/api.json`
  (`key` field) or in `docmodel/tests/golden/relations.txt`.
- The documentation is public: cite and link only public sources. Public code using CGP:
  `github.com/drohmer/csc43043ep-lab-code` (CSC_43043 labs, without the solutions) and
  `github.com/drohmer/epita_ani3d_lab_code-2027` (`examples/`: the CGP examples; `scenes_ani3d/`:
  labs). Never publish the solution of a lab, and never cite private material.
