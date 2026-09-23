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


PURE = {"random", "time", "os", "sys", "pathlib", "datetime", "io", "queue", "threading"}


def _imports(module: str) -> tuple[set[str], set[str]]:
    """The package modules and the outside modules ``module`` imports, however written."""
    tree = ast.parse((PACKAGE / f"{module}.py").read_text(encoding="utf-8"))
    package, outside = set(), set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.level == 1 and node.module:
            package.add(node.module)  # from .engine import ...
        elif isinstance(node, ast.ImportFrom) and node.module:
            name = node.module  # from hanoi_crossing.engine import ... / from json import ...
            (package if name.startswith("hanoi_crossing") else outside).add(name.split(".")[-1])
        elif isinstance(node, ast.Import):
            for alias in node.names:  # import json / import hanoi_crossing.engine
                target = package if alias.name.startswith("hanoi_crossing") else outside
                target.add(alias.name.split(".")[-1])
    return package - {"hanoi_crossing"}, outside


@pytest.mark.parametrize("module", sorted(ALLOWED))
def test_module_imports_only_what_the_blueprint_allows(module: str) -> None:
    extra = _imports(module)[0] - ALLOWED[module]
    assert not extra, f"{module} must not import {sorted(extra)}"


def test_the_engine_stays_pure() -> None:
    """CLAUDE.md ring 1: no I/O, no clock, no randomness."""
    impure = _imports("engine")[1] & PURE
    assert not impure, f"engine must not import {sorted(impure)}"


def test_every_module_is_in_the_table() -> None:
    assert {p.stem for p in PACKAGE.glob("*.py")} - {"__init__"} == set(ALLOWED)
