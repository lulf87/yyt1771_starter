"""Operator-facing camera error normalization."""

from __future__ import annotations


def normalize_camera_runtime_error(exc: BaseException) -> str:
    """Return a stable, actionable message for camera runtime failures."""
    raw_detail = _exception_chain_detail(exc)
    detail = raw_detail.lower()
    if "open device" in detail and "0x80000203" in detail:
        return (
            "Hik MVS camera access denied while opening device (ret=0x80000203). "
            "The camera may be not connected to this runtime, or another camera client / MVS process "
            "may still hold exclusive access. Stop other camera clients, reconnect or power-cycle the camera, "
            f"then retry. Raw SDK detail: {raw_detail}"
        )
    if "not importable on this machine" in detail or "native library could not be loaded" in detail:
        return (
            "Hik MVS SDK is not available in the current runtime. "
            "No live camera access was attempted. Check the selected Python runtime and Hik MVS SDK path. "
            f"Raw SDK detail: {raw_detail}"
        )
    if "no hik cameras were discovered" in detail:
        return (
            "No Hik cameras were discovered by the MVS SDK. "
            "Check camera power, network connection, IP/subnet, and driver visibility. "
            f"Raw SDK detail: {raw_detail}"
        )
    if "create handle" in detail and ("0x80000004" in detail or "hik mvs sdk" in detail):
        return (
            "Hik MVS camera handle creation failed. "
            "This is usually an SDK/runtime initialization problem or a stale camera process. "
            f"Raw SDK detail: {raw_detail}"
        )
    if "failed to open hik gige / mvs camera" in detail:
        return (
            "Hik MVS camera did not reach an opened state. "
            "Check camera power, network/IP visibility, SDK driver state, and whether another camera client "
            f"still holds exclusive access. Raw SDK detail: {raw_detail}"
        )
    return raw_detail


def _exception_chain_detail(exc: BaseException) -> str:
    parts: list[str] = []
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        part = str(current).strip() or current.__class__.__name__
        parts.append(part)
        current = current.__cause__ or current.__context__
    return " | caused by: ".join(parts)


__all__ = ["normalize_camera_runtime_error"]
