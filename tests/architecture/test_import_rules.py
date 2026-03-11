"""Guardrails for the frozen module layout."""

from __future__ import annotations

import ast
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"

ALLOWED_DEPENDENCIES = {
    "core": set(),
    "camera": {"core"},
    "temp": {"core"},
    "plc": {"core"},
    "vision": {"core"},
    "sync": {"core"},
    "curve": {"core"},
    "storage": {"core"},
    "report": {"core"},
    "workflow": {"core", "camera", "temp", "plc", "vision", "sync", "curve", "storage", "report"},
    "webapp": {"core", "workflow", "storage", "report"},
}


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module.startswith("src."):
                imported.add(node.module.split(".")[1])
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("src."):
                    imported.add(alias.name.split(".")[1])
    return imported


def test_no_unapproved_cross_module_imports() -> None:
    for module_dir in sorted(
        path for path in SRC_ROOT.iterdir() if path.is_dir() and path.name in ALLOWED_DEPENDENCIES
    ):
        module_name = module_dir.name
        allowed = ALLOWED_DEPENDENCIES[module_name]
        for path in module_dir.rglob("*.py"):
            imported_modules = _imported_modules(path)
            disallowed = sorted(
                name for name in imported_modules if name != module_name and name not in allowed
            )
            assert not disallowed, f"{path.relative_to(PROJECT_ROOT)} imports forbidden modules: {disallowed}"
