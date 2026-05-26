"""Runtime guard for real/offline pixel, contour, and A/B alignment."""

from __future__ import annotations

from typing import Any

from src.application.runtime_config import RuntimeConfig
from src.core.models import MeasurementDefinition
from src.workflow.precheck import build_real_offline_alignment_item


class RealOfflineAlignmentGuardError(RuntimeError):
    """Raised when a locked profile no longer matches the offline truth contract."""


def is_real_offline_alignment_locked_profile(runtime_config: RuntimeConfig) -> bool:
    return (
        build_real_offline_alignment_item(
            runtime_config.profile,
            runtime_config.camera,
            runtime_config.live.run,
            runtime_config.live.vision,
        )
        is not None
    )


def assert_real_offline_alignment_ready(
    runtime_config: RuntimeConfig,
    *,
    context: str,
) -> dict[str, str] | None:
    """Block locked real/offline profiles when their source/algorithm contract drifts."""

    item = build_real_offline_alignment_item(
        runtime_config.profile,
        runtime_config.camera,
        runtime_config.live.run,
        runtime_config.live.vision,
    )
    if item is None:
        return None
    if item.get("status") == "ok":
        return item
    detail = str(item.get("detail", "real/offline alignment contract failed"))
    raise RealOfflineAlignmentGuardError(f"{context} blocked by real/offline alignment guard: {detail}")


def assert_real_offline_contour_request_ready(
    runtime_config: RuntimeConfig,
    request: Any,
    *,
    context: str,
) -> None:
    """Block locked profiles when operator/request contour or A/B parameters drift."""

    if not is_real_offline_alignment_locked_profile(runtime_config):
        return
    expected = {
        "foreground_polarity": str(runtime_config.live.vision.foreground_polarity),
        "threshold_mode": str(runtime_config.live.vision.threshold_mode),
        "ignore_internal_texture": bool(runtime_config.live.vision.ignore_internal_texture),
        "min_target_area_px": int(runtime_config.live.vision.min_target_area_px),
    }
    actual = {
        "foreground_polarity": str(_read_field(request, "foreground_polarity")),
        "threshold_mode": str(_read_field(request, "threshold_mode")),
        "ignore_internal_texture": bool(_read_field(request, "ignore_internal_texture")),
        "min_target_area_px": int(_read_field(request, "min_target_area_px")),
    }
    if actual == expected:
        _assert_formal_ab_request_ready(request, context=context)
        return
    raise RealOfflineAlignmentGuardError(
        f"{context} blocked by real/offline alignment guard: request contour settings {actual} "
        f"must match offline truth contour settings {expected}"
    )


def assert_real_offline_definition_ready(
    runtime_config: RuntimeConfig,
    definition: MeasurementDefinition,
    *,
    context: str,
) -> None:
    assert_real_offline_contour_request_ready(runtime_config, definition, context=context)


def _read_field(payload: Any, name: str) -> Any:
    if isinstance(payload, dict):
        return payload.get(name)
    return getattr(payload, name)


def _assert_formal_ab_request_ready(request: Any, *, context: str) -> None:
    expected_mode = "max_chord"
    actual_mode = str(_read_field(request, "direction_projection_mode") or "auto")
    if actual_mode == expected_mode:
        return
    raise RealOfflineAlignmentGuardError(
        f"{context} blocked by real/offline alignment guard: request A/B selection mode {actual_mode!r} "
        f"must match offline truth formal contour-boundary mode {expected_mode!r}"
    )
