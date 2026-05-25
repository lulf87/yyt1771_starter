"""Runtime guard for real/offline pixel, contour, and A/B alignment."""

from __future__ import annotations

from typing import Any

from src.application.runtime_config import RuntimeConfig
from src.workflow.precheck import build_real_offline_alignment_item


class RealOfflineAlignmentGuardError(RuntimeError):
    """Raised when a locked profile no longer matches the offline truth contract."""


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
