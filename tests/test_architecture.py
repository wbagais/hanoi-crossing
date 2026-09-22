"""The blueprint in CLAUDE.md: each module imports only what this table allows."""

import ast
import pathlib

import pytest

PACKAGE = pathlib.Path(__file__).resolve().parent.parent / "src" / "hanoi_crossing"

ALLOWED = {
    "engine": set(),
    "agents": {"engine"},
    "runner": {"engine", "agents"},
    "recording": {"engine", "agents", "runner"},
    "render": {"engine", "runner"},
    "human": {"engine", "agents", "runner", "render"},
    "cli": {"engine", "agents", "runner", "recording", "render", "human"},
}


def _local_imports(module: str) -> set[str]:
    tree = ast.parse((PACKAGE / f"{module}.py").read_text(encoding="utf-8"))
    return {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.level == 1 and node.module
    }


def test_every_module_is_in_the_table() -> None:
    assert {p.stem for p in PACKAGE.glob("*.py")} - {"__init__"} == set(ALLOWED)


@pytest.mark.parametrize("module", sorted(ALLOWED))
def test_module_imports_only_what_the_blueprint_allows(module: str) -> None:
    extra = _local_imports(module) - ALLOWED[module]
    assert not extra, f"{module} must not import {sorted(extra)}"
