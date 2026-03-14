"""Repository layout guardrails for the frozen project baseline."""

from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
TESTS_ROOT = PROJECT_ROOT / "tests"

ALLOWED_TOP_LEVEL_DIRS = {"configs", "docs", "examples", "src", "tests"}
IGNORED_TOP_LEVEL_DIRS = {".git", ".pytest_cache", "__pycache__"}
DISALLOWED_TOP_LEVEL_DIRS = {"scripts", "utils", "common", "shared", "misc", "temp_files", "frontend"}
ALLOWED_SRC_MODULES = {
    "core",
    "camera",
    "temp",
    "plc",
    "vision",
    "sync",
    "curve",
    "workflow",
    "storage",
    "report",
    "webapp",
}
ALLOWED_TEST_DIRS = {
    "architecture",
    "camera",
    "core",
    "curve",
    "plc",
    "report",
    "storage",
    "sync",
    "temp",
    "vision",
    "webapp",
    "workflow",
}
ALLOWED_ROOT_FILES = {"README.md", "pyproject.toml", ".gitignore"}
ALLOWED_TOOL_CONFIG_SUFFIXES = {".toml", ".ini", ".cfg"}


def test_top_level_directories_match_frozen_layout() -> None:
    top_level_dirs = {
        path.name
        for path in PROJECT_ROOT.iterdir()
        if path.is_dir() and not _is_ignored_top_level_dir(path)
    }

    assert DISALLOWED_TOP_LEVEL_DIRS.isdisjoint(top_level_dirs), (
        f"Disallowed top-level directories present: {sorted(DISALLOWED_TOP_LEVEL_DIRS & top_level_dirs)}"
    )
    assert top_level_dirs == ALLOWED_TOP_LEVEL_DIRS, (
        f"Unexpected top-level directories: {sorted(top_level_dirs - ALLOWED_TOP_LEVEL_DIRS)}; "
        f"missing: {sorted(ALLOWED_TOP_LEVEL_DIRS - top_level_dirs)}"
    )


def test_top_level_files_stay_within_readme_and_tooling_scope() -> None:
    unexpected_files = sorted(
        path.name
        for path in PROJECT_ROOT.iterdir()
        if path.is_file() and not _is_allowed_root_file(path)
    )
    assert not unexpected_files, f"Unexpected top-level files: {unexpected_files}"


def test_src_first_level_modules_are_frozen() -> None:
    src_modules = {
        path.name
        for path in SRC_ROOT.iterdir()
        if path.is_dir() and path.name != "__pycache__" and not path.name.startswith(".")
    }
    assert src_modules == ALLOWED_SRC_MODULES, (
        f"Unexpected src/一级模块: {sorted(src_modules - ALLOWED_SRC_MODULES)}; "
        f"missing: {sorted(ALLOWED_SRC_MODULES - src_modules)}"
    )


def test_tests_root_is_not_flattened_with_test_files() -> None:
    flat_test_files = sorted(
        path.name for path in TESTS_ROOT.iterdir() if path.is_file() and path.name.startswith("test_")
    )
    assert not flat_test_files, f"tests/ 根目录不应平铺 test_*.py: {flat_test_files}"


def test_tests_root_directories_match_supported_mirror_layout() -> None:
    test_dirs = {
        path.name
        for path in TESTS_ROOT.iterdir()
        if path.is_dir() and path.name != "__pycache__" and not path.name.startswith(".")
    }
    assert test_dirs.issubset(ALLOWED_TEST_DIRS), (
        f"Unexpected tests/子目录: {sorted(test_dirs - ALLOWED_TEST_DIRS)}"
    )


def _is_allowed_root_file(path: Path) -> bool:
    if path.name in ALLOWED_ROOT_FILES:
        return True
    if path.name.startswith("."):
        return True
    return path.suffix in ALLOWED_TOOL_CONFIG_SUFFIXES


def _is_ignored_top_level_dir(path: Path) -> bool:
    if path.name in IGNORED_TOP_LEVEL_DIRS:
        return True
    if path.name.startswith("."):
        return True
    return path.name.endswith(".egg-info")
