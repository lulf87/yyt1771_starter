"""Helpers for importing canonical AFAS postprocessing datasets."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from src.curve.afas_postprocessing_dataset import (
    AFAS_DATASET_SCHEMA_VERSION,
    DEFAULT_AFAS_ANALYSIS_PARAMETERS,
    DEFAULT_AFAS_PREPROCESSING_PARAMETERS,
)


def normalize_imported_afas_dataset(payload: Mapping[str, Any], *, session_id: str) -> dict[str, Any]:
    """Validate a canonical AFAS dataset payload and fill import-safe defaults."""

    schema_version = str(payload.get("schema_version") or AFAS_DATASET_SCHEMA_VERSION)
    if schema_version != AFAS_DATASET_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported AFAS dataset schema_version: {schema_version}. "
            f"Expected {AFAS_DATASET_SCHEMA_VERSION}."
        )

    raw_channel_map = payload.get("channel_map")
    if not isinstance(raw_channel_map, Mapping) or not raw_channel_map:
        raise ValueError("AFAS dataset must contain a non-empty channel_map.")

    channel_map: dict[str, dict[str, Any]] = {}
    available_channels = [str(name) for name in raw_channel_map.keys()]
    active_channel = str(payload.get("active_channel") or available_channels[0])
    if active_channel not in raw_channel_map:
        raise ValueError(f"active_channel '{active_channel}' is not present in channel_map.")

    top_level_timestamps = payload.get("timestamps_ms")
    top_level_temperatures = payload.get("temperature_series_celsius")

    for channel_name, channel_payload in raw_channel_map.items():
        if not isinstance(channel_payload, Mapping):
            raise ValueError(f"channel_map['{channel_name}'] must be an object.")

        resolved_temperatures = channel_payload.get("temperature_celsius")
        if resolved_temperatures is None and channel_name == active_channel:
            resolved_temperatures = top_level_temperatures
        temperatures = _coerce_float_list(
            resolved_temperatures,
            field_name=f"channel_map['{channel_name}'].temperature_celsius",
        )
        if not temperatures:
            raise ValueError(f"channel_map['{channel_name}'].temperature_celsius cannot be empty.")

        values = _coerce_float_list(
            channel_payload.get("values"),
            field_name=f"channel_map['{channel_name}'].values",
        )
        expected_length = len(temperatures)
        if len(values) != expected_length:
            raise ValueError(
                f"channel_map['{channel_name}'] length mismatch: "
                f"temperature_celsius has {expected_length} values but values has {len(values)}."
            )

        resolved_timestamps = channel_payload.get("timestamps_ms")
        if resolved_timestamps is None and channel_name == active_channel:
            resolved_timestamps = top_level_timestamps
        timestamps_ms = _coerce_int_series(
            resolved_timestamps,
            field_name=f"channel_map['{channel_name}'].timestamps_ms",
            expected_length=expected_length,
            default_factory=lambda: [index * 1000 for index in range(expected_length)],
        )

        metric_norm = _coerce_optional_float_series(
            channel_payload.get("metric_norm"),
            field_name=f"channel_map['{channel_name}'].metric_norm",
            expected_length=expected_length,
        )
        quality = _coerce_float_series(
            channel_payload.get("quality"),
            field_name=f"channel_map['{channel_name}'].quality",
            expected_length=expected_length,
            default_factory=lambda: [1.0] * expected_length,
        )
        point_a_px = _coerce_optional_point_series(
            channel_payload.get("point_a_px"),
            field_name=f"channel_map['{channel_name}'].point_a_px",
            expected_length=expected_length,
        )
        point_b_px = _coerce_optional_point_series(
            channel_payload.get("point_b_px"),
            field_name=f"channel_map['{channel_name}'].point_b_px",
            expected_length=expected_length,
        )

        channel_map[str(channel_name)] = {
            "channel_name": str(channel_payload.get("channel_name") or channel_name),
            "metric_name": str(channel_payload.get("metric_name") or "metric_raw"),
            "timestamps_ms": timestamps_ms,
            "temperature_celsius": temperatures,
            "values": values,
            "metric_norm": metric_norm,
            "quality": quality,
            "point_a_px": point_a_px,
            "point_b_px": point_b_px,
        }

    active_channel_payload = channel_map[active_channel]
    return {
        "schema_version": AFAS_DATASET_SCHEMA_VERSION,
        "session_id": session_id,
        "source": str(payload.get("source") or "imported_afas_dataset"),
        "analysis_engine": str(payload.get("analysis_engine") or "afas"),
        "capture_mode": str(payload.get("capture_mode") or "post_run_review"),
        "artifact_provenance": dict(payload.get("artifact_provenance") or {}),
        "active_channel": active_channel,
        "channel_map": channel_map,
        "temperature_series_celsius": list(active_channel_payload["temperature_celsius"]),
        "timestamps_ms": list(active_channel_payload["timestamps_ms"]),
        "definition": dict(payload.get("definition") or {}),
        "preprocessing_defaults": _merge_parameter_defaults(
            DEFAULT_AFAS_PREPROCESSING_PARAMETERS,
            payload.get("preprocessing_defaults"),
        ),
        "analysis_defaults": _merge_parameter_defaults(
            DEFAULT_AFAS_ANALYSIS_PARAMETERS,
            payload.get("analysis_defaults"),
        ),
        "rates": dict(payload.get("rates") or {}),
        "measurement_profile": dict(payload.get("measurement_profile") or {}),
        "warnings": [str(item) for item in payload.get("warnings", [])],
        "live_result_snapshot": dict(payload.get("live_result_snapshot") or {}),
    }


def build_imported_session_detail(dataset: Mapping[str, Any]) -> dict[str, Any]:
    """Build a replay-style detail payload from an imported AFAS dataset."""

    active_channel = str(dataset["active_channel"])
    channel_payload = dict(dataset["channel_map"][active_channel])
    temperatures = _coerce_float_list(
        channel_payload.get("temperature_celsius"),
        field_name=f"channel_map['{active_channel}'].temperature_celsius",
    )
    values = _coerce_float_list(
        channel_payload.get("values"),
        field_name=f"channel_map['{active_channel}'].values",
    )
    timestamps_ms = _coerce_int_series(
        channel_payload.get("timestamps_ms"),
        field_name=f"channel_map['{active_channel}'].timestamps_ms",
        expected_length=len(temperatures),
        default_factory=lambda: [index * 1000 for index in range(len(temperatures))],
    )
    metric_norm = _coerce_optional_float_series(
        channel_payload.get("metric_norm"),
        field_name=f"channel_map['{active_channel}'].metric_norm",
        expected_length=len(temperatures),
    )
    quality = _coerce_float_series(
        channel_payload.get("quality"),
        field_name=f"channel_map['{active_channel}'].quality",
        expected_length=len(temperatures),
        default_factory=lambda: [1.0] * len(temperatures),
    )

    points = [
        {
            "timestamp_ms": timestamps_ms[index],
            "celsius": temperatures[index],
            "metric_raw": values[index],
            "metric_norm": metric_norm[index],
            "quality": quality[index],
        }
        for index in range(len(temperatures))
    ]
    live_result_snapshot = dict(dataset.get("live_result_snapshot") or {})
    return {
        "session_id": str(dataset["session_id"]),
        "source": str(dataset.get("source") or "imported_afas_dataset"),
        "af95": _coerce_optional_float(live_result_snapshot.get("af95")),
        "point_count": len(points),
        "points": points,
        "key_frames": [],
    }


def build_imported_session_result(
    dataset: Mapping[str, Any],
    *,
    analysis: Mapping[str, Any],
    point_count: int,
) -> dict[str, Any]:
    """Create a lightweight result payload for imported datasets."""

    result_payload = dict(analysis.get("result") or {})
    return {
        "session_id": str(dataset["session_id"]),
        "state": "completed",
        "analysis_engine": str(dataset.get("analysis_engine") or "afas"),
        "channel_name": str(dataset["active_channel"]),
        "result_status": str(analysis.get("result_status") or "ok"),
        "result_reason": analysis.get("reason"),
        "result_detail": str(analysis.get("detail") or "Imported AFAS dataset is ready for Analysis Studio."),
        "af95": _coerce_optional_float(dict(dataset.get("live_result_snapshot") or {}).get("af95")),
        "as_value": _coerce_optional_float(result_payload.get("As")),
        "af_value": _coerce_optional_float(result_payload.get("Af_tan")),
        "point_count": int(point_count),
        "capture_mode": str(dataset.get("capture_mode") or "post_run_review"),
        "rates": dict(dataset.get("rates") or {}),
        "measurement_profile": dict(dataset.get("measurement_profile") or {}),
        "warnings": [str(item) for item in analysis.get("warnings", [])],
        "artifacts": {
            "definition": None,
            "telemetry": None,
            "events": None,
            "detail": "detail.json",
            "result": "result.json",
            "afas_dataset": "afas_dataset.json",
            "afas_analysis": "afas_analysis.json",
            "afas_plot": None,
            "afas_report": None,
            "keyframes": [],
        },
    }


def _merge_parameter_defaults(defaults: Mapping[str, Any], overrides: Any) -> dict[str, Any]:
    merged = dict(defaults)
    if isinstance(overrides, Mapping):
        merged.update(dict(overrides))
    return merged


def _coerce_float_list(values: Any, *, field_name: str) -> list[float]:
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes, bytearray)):
        raise ValueError(f"{field_name} must be an array of numbers.")
    return [float(value) for value in values]


def _coerce_float_series(
    values: Any,
    *,
    field_name: str,
    expected_length: int,
    default_factory: Callable[[], list[float]],
) -> list[float]:
    if values is None:
        return default_factory()
    coerced = _coerce_float_list(values, field_name=field_name)
    if len(coerced) != expected_length:
        raise ValueError(f"{field_name} must contain {expected_length} items, got {len(coerced)}.")
    return coerced


def _coerce_optional_float_series(
    values: Any,
    *,
    field_name: str,
    expected_length: int,
) -> list[float | None]:
    if values is None:
        return [None] * expected_length
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes, bytearray)):
        raise ValueError(f"{field_name} must be an array of numbers or nulls.")
    if len(values) != expected_length:
        raise ValueError(f"{field_name} must contain {expected_length} items, got {len(values)}.")
    return [_coerce_optional_float(value) for value in values]


def _coerce_optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _coerce_int_series(
    values: Any,
    *,
    field_name: str,
    expected_length: int,
    default_factory: Callable[[], list[int]],
) -> list[int]:
    if values is None:
        return default_factory()
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes, bytearray)):
        raise ValueError(f"{field_name} must be an array of integers.")
    coerced = [int(value) for value in values]
    if len(coerced) != expected_length:
        raise ValueError(f"{field_name} must contain {expected_length} items, got {len(coerced)}.")
    return coerced


def _coerce_optional_point_series(
    values: Any,
    *,
    field_name: str,
    expected_length: int,
) -> list[list[int] | None]:
    if values is None:
        return [None] * expected_length
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes, bytearray)):
        raise ValueError(f"{field_name} must be an array of [x, y] points or nulls.")
    if len(values) != expected_length:
        raise ValueError(f"{field_name} must contain {expected_length} items, got {len(values)}.")

    normalized: list[list[int] | None] = []
    for index, item in enumerate(values):
        if item is None:
            normalized.append(None)
            continue
        if not isinstance(item, Sequence) or isinstance(item, (str, bytes, bytearray)) or len(item) != 2:
            raise ValueError(f"{field_name}[{index}] must be a [x, y] point or null.")
        normalized.append([int(item[0]), int(item[1])])
    return normalized
