"""Locations of every input and output of the pipeline.

All paths derive from the documentation root (the folder holding docmodel/, editorial/,
content/ ...). Two environment variables allow running on another checkout:
  CGP_DOC_ROOT    documentation root    (default: found from this file)
  CGP_SOURCE_DIR  CGP library sources   (default: <root>/../cgp-2027/cgp)
  CGP_BUILD_DIR   generated outputs     (default: <root>/build; the tests use a temporary one)
"""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Paths:
    root: Path

    @property
    def source(self) -> Path:
        env = os.environ.get("CGP_SOURCE_DIR")
        return Path(env).resolve() if env else (self.root.parent / "cgp-2027" / "cgp").resolve()

    # --- inputs
    @property
    def doxyfile_template(self) -> Path:
        return self.root / "docmodel" / "Doxyfile.in"

    @property
    def schema(self) -> Path:
        return self.root / "docmodel" / "schema" / "api.schema.json"

    @property
    def editorial(self) -> Path:
        return self.root / "editorial"

    @property
    def types(self) -> Path:
        return self.editorial / "types.yaml"

    @property
    def descriptions(self) -> Path:
        return self.editorial / "descriptions.yaml"

    @property
    def annotations(self) -> Path:
        return self.editorial / "annotations.yaml"

    @property
    def function_groups(self) -> Path:
        return self.editorial / "function_groups.yaml"

    @property
    def members(self) -> Path:
        return self.editorial / "members.yaml"

    @property
    def content_check(self) -> Path:
        return self.editorial / "content_check.yaml"

    @property
    def content(self) -> Path:
        return self.root / "content"

    @property
    def golden_dir(self) -> Path:
        return self.root / "docmodel" / "tests" / "golden"

    # --- outputs (generated, never edited by hand)
    @property
    def build(self) -> Path:
        env = os.environ.get("CGP_BUILD_DIR")
        return Path(env).resolve() if env else self.root / "build"

    @property
    def doxygen_xml(self) -> Path:
        return self.build / "doxygen" / "xml"

    @property
    def api_json(self) -> Path:
        return self.build / "api.json"

    @property
    def content_index(self) -> Path:
        return self.build / "content_index.json"

    @property
    def reports(self) -> Path:
        return self.build / "reports"


def default_paths() -> Paths:
    env = os.environ.get("CGP_DOC_ROOT")
    if env:
        return Paths(Path(env).resolve())
    # docmodel/src/cgp_docmodel/paths.py -> root is 4 levels up
    return Paths(Path(__file__).resolve().parents[3])
