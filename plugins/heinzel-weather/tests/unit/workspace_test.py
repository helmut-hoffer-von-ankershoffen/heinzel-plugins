"""The owning type gate must include its real source directory without requiring sibling projects."""

import tomllib
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit
ROOT = Path(__file__).resolve().parents[2]


def test_pyright_includes_the_owning_source_as_a_real_directory():
    settings = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    includes = {ROOT / directory for directory in settings["tool"]["pyright"]["include"]}
    assert includes == {ROOT / "src"}
    assert all(path.is_dir() for path in includes)
