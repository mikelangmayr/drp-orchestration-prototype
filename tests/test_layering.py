"""Guardrail: the ``core`` layer must stay free of orchestration.

If a primitive ever imports ``prefect``, it ceases to be usable from a notebook
or a bare test, and the architecture argument collapses (docs/architecture.md
§"Why the strict separation matters"). This test enforces that invariant
statically — parsing imports rather than grepping text, so docstrings that
merely mention prefect are not false positives — so a violation fails CI rather
than review.
"""
from __future__ import annotations

import ast
from pathlib import Path

CORE_DIR = Path(__file__).resolve().parents[1] / "src" / "spie_prototype" / "core"


def _imports_prefect(source: str) -> bool:
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(alias.name.split(".")[0] == "prefect" for alias in node.names):
                return True
        elif isinstance(node, ast.ImportFrom):
            if (node.module or "").split(".")[0] == "prefect":
                return True
    return False


def test_core_does_not_import_prefect() -> None:
    offenders = [path.name for path in CORE_DIR.glob("*.py") if _imports_prefect(path.read_text())]
    assert not offenders, f"core/ modules must not import prefect: {offenders}"
