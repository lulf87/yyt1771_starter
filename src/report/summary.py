"""Result summary helpers."""

from __future__ import annotations

from typing import Any

from src.core.models import SessionRecord


def build_summary(record: SessionRecord, point_count: int) -> dict[str, str | int]:
    return {
        "session_id": record.session_id,
        "state": record.state.value,
        "point_count": point_count,
    }


def build_live_run_result(
    *,
    session_id: str,
    state: str,
    analysis_engine: str,
    channel_name: str,
    result_status: str,
    result_reason: str | None,
    result_detail: str,
    af95: float | None,
    as_value: float | None,
    af_value: float | None,
    point_count: int,
    keyframe_refs: list[str],
    capture_mode: str,
    rates: dict[str, Any],
    measurement_profile: dict[str, Any],
    warnings: list[str],
) -> dict[str, Any]:
    return {
        "session_id": session_id,
        "state": state,
        "analysis_engine": analysis_engine,
        "channel_name": channel_name,
        "result_status": result_status,
        "result_reason": result_reason,
        "result_detail": result_detail,
        "af95": af95,
        "as_value": as_value,
        "af_value": af_value,
        "point_count": point_count,
        "capture_mode": capture_mode,
        "rates": rates,
        "measurement_profile": measurement_profile,
        "warnings": list(warnings),
        "artifacts": {
            "definition": "definition.json",
            "telemetry": "telemetry.csv",
            "events": "events.jsonl",
            "detail": "detail.json",
            "result": "result.json",
            "afas_dataset": "afas_dataset.json",
            "afas_analysis": None,
            "afas_plot": None,
            "afas_report": None,
            "keyframes": keyframe_refs,
        },
    }
