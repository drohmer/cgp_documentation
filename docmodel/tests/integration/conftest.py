"""Build the real model once per test session, into a temporary build directory."""

import json
import shutil

import pytest

from cgp_docmodel import cli
from cgp_docmodel.paths import default_paths


def _build(build_dir, monkeypatch):
    monkeypatch.setenv("CGP_BUILD_DIR", str(build_dir))
    assert cli.main(["build"]) == 0
    return default_paths()


@pytest.fixture(scope="session")
def built(tmp_path_factory):
    if shutil.which("doxygen") is None:
        pytest.skip("doxygen not installed")
    if not default_paths().source.is_dir():
        pytest.skip("CGP sources not found (set CGP_SOURCE_DIR)")
    mp = pytest.MonkeyPatch()
    paths = _build(tmp_path_factory.mktemp("build"), mp)
    model = json.loads(paths.api_json.read_text(encoding="utf-8"))
    yield paths, model
    mp.undo()


@pytest.fixture(scope="session")
def model(built):
    return built[1]


@pytest.fixture(scope="session")
def fns(model):
    return {f["id"]: f for f in model["functions"]}
