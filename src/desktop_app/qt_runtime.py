"""Shared desktop runtime bootstrap helpers."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import sys

from src.camera.hik_gige_mvs import HIK_MVS_LIBRARY_PATH_ENV, HIK_MVS_PYTHON_PATH_ENV

HIK_MVS_SIDE_CAR_STAGING_DIR = Path("/tmp/mvs")
HIK_MVS_SIDE_CAR_LIBRARIES = (
    "libMVGigEVisionSDK.dylib",
    "libMVU3VisionSDK.dylib",
    "libMediaProcess.dylib",
)


def bootstrap_desktop_runtime() -> None:
    """Prepare sys.path and Qt plugin paths for the desktop shell."""
    _bootstrap_local_hik_mvs_runtime()
    _prepend_extra_sys_path()
    _configure_qt_plugin_paths()


def _prepend_extra_sys_path() -> None:
    extra_sys_path = os.environ.get("YYT1771_DESKTOP_EXTRA_SYS_PATH", "").strip()
    if not extra_sys_path:
        return
    for raw_entry in reversed(extra_sys_path.split(os.pathsep)):
        entry = raw_entry.strip()
        if not entry:
            continue
        resolved = str(Path(entry).expanduser())
        if resolved not in sys.path:
            sys.path.insert(0, resolved)


def find_pyside6_qt_root() -> Path | None:
    spec = importlib.util.find_spec("PySide6")
    if spec is None or spec.origin is None:
        return None
    package_dir = Path(spec.origin).resolve().parent
    qt_root = package_dir / "Qt"
    if not qt_root.exists():
        return None
    return qt_root


def _configure_qt_plugin_paths() -> None:
    qt_root = find_pyside6_qt_root()
    if qt_root is None:
        return
    plugin_root = qt_root / "plugins"
    platform_root = plugin_root / "platforms"
    if plugin_root.is_dir():
        _prepend_env_path("QT_PLUGIN_PATH", plugin_root)
    if platform_root.is_dir():
        os.environ.setdefault("QT_QPA_PLATFORM_PLUGIN_PATH", str(platform_root))


def _prepend_env_path(name: str, path: Path) -> None:
    resolved = str(path)
    existing = [entry for entry in os.environ.get(name, "").split(os.pathsep) if entry]
    if resolved in existing:
        existing.remove(resolved)
    existing.insert(0, resolved)
    os.environ[name] = os.pathsep.join(existing)


def _bootstrap_local_hik_mvs_runtime() -> None:
    python_path = _find_local_hik_mvs_python_path()
    if python_path is not None:
        resolved = str(python_path)
        os.environ.setdefault(HIK_MVS_PYTHON_PATH_ENV, resolved)
        if resolved not in sys.path:
            sys.path.insert(0, resolved)

    library_path = _find_local_hik_mvs_library_path()
    if library_path is not None:
        os.environ.setdefault(HIK_MVS_LIBRARY_PATH_ENV, str(library_path))
        _ensure_hik_runtime_sidecar_symlinks(library_path.parent)


def _ensure_hik_runtime_sidecar_symlinks(runtime_lib_dir: Path) -> None:
    if not runtime_lib_dir.is_dir():
        return
    sources = {
        library_name: runtime_lib_dir / library_name
        for library_name in HIK_MVS_SIDE_CAR_LIBRARIES
    }
    if not all(path.is_file() for path in sources.values()):
        return

    staging_dir = HIK_MVS_SIDE_CAR_STAGING_DIR
    staging_dir.mkdir(parents=True, exist_ok=True)
    for library_name, source in sources.items():
        target = staging_dir / library_name
        _ensure_symlink(target=target, source=source)


def _ensure_symlink(*, target: Path, source: Path) -> None:
    source_resolved = source.resolve()
    if target.is_symlink():
        try:
            if target.resolve() == source_resolved:
                return
        except OSError:
            pass
        target.unlink()
    elif target.exists():
        target.unlink()
    target.symlink_to(source_resolved)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _find_local_hik_mvs_python_path() -> Path | None:
    configured = os.environ.get(HIK_MVS_PYTHON_PATH_ENV, "").strip()
    if configured:
        resolved = Path(configured).expanduser()
        if (resolved / "MvCameraControl_class.py").is_file():
            return resolved

    hik_root = _project_root().parent / ".tmp_hik"
    if not hik_root.exists():
        return None

    candidates = sorted(
        (
            path.parent
            for path in hik_root.glob("**/Samples/Python/MvImport/MvCameraControl_class.py")
            if path.is_file()
        ),
        key=_path_sort_key,
        reverse=True,
    )
    return candidates[0] if candidates else None


def _find_local_hik_mvs_library_path() -> Path | None:
    configured = os.environ.get(HIK_MVS_LIBRARY_PATH_ENV, "").strip()
    if configured:
        resolved = Path(configured).expanduser()
        if resolved.is_file():
            return resolved

    hik_root = _project_root().parent / ".tmp_hik"
    if not hik_root.exists():
        return None

    preferred_patterns = [
        "patched_runtime_dlopen_*/lib/libMvCameraControl.dylib",
        "patched_runtime_loader/lib/libMvCameraControl.dylib",
        "patched_runtime/lib/libMvCameraControl.dylib",
        "**/lib/libMvCameraControl.dylib",
    ]
    for pattern in preferred_patterns:
        candidates = sorted(
            (path for path in hik_root.glob(pattern) if path.is_file()),
            key=_path_sort_key,
            reverse=True,
        )
        if candidates:
            return candidates[0]
    return None


def _path_sort_key(path: Path) -> tuple[float, str]:
    try:
        mtime = path.stat().st_mtime
    except OSError:
        mtime = 0.0
    return (mtime, str(path))
