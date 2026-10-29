# cgp-docmodel

Builds `build/api.json`, a platform-independent model of the CGP API, from the Doxygen XML
of `../cgp-2027/cgp`. It never modifies the C++ sources.

## Design goals

- **Auditable**: every value says where it comes from (`description_source`,
  `category_source`, `category_rule`, `params_source`, `source_url` pinned to the extracted
  commit). Builds are deterministic, and the model is kept in plain-text snapshots
  (`tests/golden/*.txt`) whose diff shows the exact effect of any change. Functions left
  out are listed with the reason (`excluded`), never dropped silently; a key collision
  fails the build.
- **Controllable**: what is documented and how it is classified lives in `../editorial/*.yaml`,
  not in code. Stale or invalid entries make `check` fail.
- **Readable**: one module per stage, pure functions where possible, no hidden state.

## Modules (`src/cgp_docmodel/`)

| Module | Role | Tests |
|---|---|---|
| `paths.py` | every input and output location (env: `CGP_DOC_ROOT`, `CGP_SOURCE_DIR`, `CGP_BUILD_DIR`) | |
| `doxygen.py` | runs Doxygen, reads its XML into plain records (the only module that reads XML): header-declared functions only, specializations (vec3 = `numarray_stack<T,3>`, mat4), base classes | `unit/test_doxygen_fixture.py`, integration |
| `header.py` | reads declarations in the .hpp: parameter names and default values that Doxygen loses when the definition is in a .cpp | `unit/test_header.py` |
| `cpptypes.py` | type strings: normalization, alias resolution, `exact` / `generic` matching | `unit/test_cpptypes.py` |
| `categories.py` | ordered heuristic rules; each function records the rule that fired | `unit/test_categories.py` |
| `relations.py` | merges const / non-const variants, builds takes / returns / operators per type (also through base classes: `via`) | `unit/test_relations.py` |
| `editorial.py` | loads and validates `editorial/*.yaml`, finds stale keys | `unit/test_editorial.py` |
| `content.py` | resolves the inline code of `content/*.md` against the model | `unit/test_content.py` |
| `crossrefs.py` | from that resolution: `guides` of each type and `content_links` (inline code -> reference target) | `unit/test_crossrefs.py`, integration |
| `model.py` | assembles `api.json` (deterministic, with provenance) | integration |
| `checks.py` | JSON schema validation and structural invariants | integration |
| `report.py` | coverage report and the four golden snapshots | integration |
| `cli.py` | `cgp-docmodel build / check / report / snapshot` | integration |

## Commands and exit codes

```sh
cgp-docmodel build              # Doxygen + build/api.json + build/content_index.json
cgp-docmodel check [--strict]   # schema, invariants, editorial, content references
cgp-docmodel report             # build/reports/coverage.md
cgp-docmodel snapshot [--update]
```

Exit codes: `0` success, `1` check failed or snapshot differs, `2` environment problem
(Doxygen missing, sources not found, invalid YAML).

## The model (`build/api.json`, schema `schema/api.schema.json`)

- `functions[]`: free functions of `cgp` and `cgp::loader` declared in a header. Fields: `id`
  (stable, derived from the key), `key` (name, template parameters and parameter types, e.g.
  `norm<T,N>(numarray_stack<T,N> const&)`; used by the editorial files), `name`,
  `params_source` (header | doxygen),
  `signature`, `template`, `params`, `ret`, `module`, `file`, `line`, `source_url`,
  `description` + `description_source`, `category` + `category_source` + `category_rule`,
  `primary` / `variants` / `variant_of` (const variants), `home` (schema 1.5: the page that
  documents a primary function in full, `{type, group, rel}`: factories on the type they return,
  the others on the type of their first parameter, see `relations.choose_home`; null for a variant).
- `types{}`: documented types (from `editorial/types.yaml`): `canonical`, `group`, `short`,
  `struct` (fields and methods, variants merged), and the relations `takes`, `returns`,
  `operators`: lists of `{id, generic, via}`. `generic` means the function is a template applying
  to the type (e.g. `norm(numarray_stack<T,N>)` for `vec3`); `via` names the base class through
  which it applies (`quaternion` derives from `numarray_stack<float,4>`), or null.
  Fields have an `id` (`field-<name>`); methods and fields use their `id` as anchor on both sites.
  `guides` (schema 1.5): content pages citing the type, one of its members or a function whose
  `home` is the type, `{path, title, section}` ordered by section then `order:`.
- `content_links{}` (schema 1.5): exact text of an inline code span of `content/*.md` -> its
  target `{kind: type|function|method|field, type, group, rel, id}`. Only spans with a single
  unambiguous target; names of `no_link` in `editorial/content_check.yaml` are never linked.
  Renderers turn the span into a link without resolving anything themselves.
- Families (`family_of` non-null, e.g. `vecN` = `numarray_stack<T,N>` for vec2/3/4): their relations
  are the functions generic over ALL template arguments. On member pages these entries carry
  `shared` = the family name, so renderers list them once, on the family page.
- `excluded[]`: functions left out of the model, with the reason.
- `aliases{}`: typedefs of the namespace (`vec3 -> numarray_stack3<float>`...).

Changing a field name or its meaning is a breaking change: bump `schema_version` in
`model.py` and in the schema, and update the renderers.

## Tests

```sh
../.venv/bin/python -m pytest docmodel/tests/unit -q   # pure logic, < 1 s
../.venv/bin/python -m pytest docmodel -q              # + integration on the real sources, ~2 s
```

Integration tests build the model into a temporary directory and check: schema,
invariants, known facts about CGP (`cross` only on vec3, `mesh_primitive_*` return a mesh,
vec3 has x/y/z, `draw` keeps its default values...), determinism (two builds are
byte-identical) and the four golden snapshots (`tests/golden/`: functions, relations,
structs, excluded).

The suite was checked by mutation: re-introducing each bug found by the audit of
2026-10-28 (header defaults ignored, specializations ignored, base classes ignored,
silent drop of collisions, .cpp-only functions kept) makes at least one test fail.
