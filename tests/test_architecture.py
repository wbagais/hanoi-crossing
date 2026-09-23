"""The blueprint in CLAUDE.md: each module imports only what this table allows."""

import ast
import pathlib

import pytest

PACKAGE = pathlib.Path(__file__).resolve().parent.parent / "src" / "hanoi_crossing"

ALLOWED = {
    "engine": set(),
    "agents": {"engine"},
    "runner": {"engine"},
    "recording": {"engine", "agents", "runner"},
    "render": {"engine", "runner"},
    "human": {"engine", "runner", "render"},
    "cli": {"engine", "agents", "runner", "recording", "render", "human"},
}


@pytest.mark.parametrize("module", sorted(ALLOWED))
def test_module_imports_only_what_the_blueprint_allows(module: str) -> None:
    tree = ast.parse((PACKAGE / f"{module}.py").read_text(encoding="utf-8"))
    local = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.level == 1}
    extra = local - ALLOWED[module]
    assert not extra, f"{module} must not import {sorted(extra)}"


def test_every_module_is_in_the_table() -> None:
    assert {p.stem for p in PACKAGE.glob("*.py")} - {"__init__"} == set(ALLOWED)
