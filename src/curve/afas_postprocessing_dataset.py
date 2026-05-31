"""Canonical AFAS postprocessing dataset contract builder."""

from __future__ import annotations

from typing import Any

from src.core.models import MeasurementDefinition, SyncPoint, resolve_width_extreme_mode
from src.curve.af95 import normalize_sync_points

AFAS_DATASET_SCHEMA_VERSION = "afas_postprocessing_dataset.v1"
AFAS_DATASET_ARTIFACT_NAME = "afas_dataset.json"
DEFAULT_AFAS_PREPROCESSING_PARAMETERS = {
    "group_by_temperature": True,
    "outlier_window": 11,
    "outlier_threshold": 5.0,
    "outlier_max_iterations": 3,
    "savgol_window_length": 51,
    "savgol_polyorder": 3,
}
DEFAULT_AFAS_ANALYSIS_PARAMETERS = {
    "low_range_celsius": None,
    "high_range_celsius": None,
    "tangent_offset": 0,
}


def build_afas_postprocessing_dataset(
    *,
    session_id: str,
    definition: MeasurementDefinition,
    sync_points: list[SyncPoint],
    channel_name: str,
    analysis_engine: str,
    capture_mode: str,
    rates: dict[str, Any],
    measurement_profile: dict[str, Any],
    warnings: list[str],
    live_result_snapshot: dict[str, Any],
) -> dict[str, Any]:
    normalized_points = normalize_sync_points(sync_points)
    normalized_by_timestamp = {point.timestamp_ms: point for point in normalized_points}

    timestamps_ms: list[int] = []
    temperatures_celsius: list[float] = []
    channel_values: list[float] = []
    metric_norm: list[float | None] = []
    quality_values: list[float] = []
    point_a_series: list[list[int] | None] = []
    point_b_series: list[list[int] | None] = []

    for sync_point in sync_points:
        if sync_point.temp is None or sync_point.metric is None or sync_point.metric.metric_raw is None:
            continue
        timestamps_ms.append(int(sync_point.timestamp_ms))
        temperatures_celsius.append(float(sync_point.temp.celsius))
        channel_values.append(float(sync_point.metric.metric_raw))
        normalized = normalized_by_timestamp.get(sync_point.timestamp_ms)
        metric_norm.append(None if normalized is None else float(normalized.metric_norm))
        quality_values.append(float(sync_point.metric.quality))
        point_a_series.append(
            None
            if sync_point.metric.point_a_px is None
            else [int(sync_point.metric.point_a_px[0]), int(sync_point.metric.point_a_px[1])]
        )
        point_b_series.append(
            None
            if sync_point.metric.point_b_px is None
            else [int(sync_point.metric.point_b_px[0]), int(sync_point.metric.point_b_px[1])]
        )

    return {
        "schema_version": AFAS_DATASET_SCHEMA_VERSION,
        "session_id": session_id,
        "source": "live_run",
        "analysis_engine": analysis_engine,
        "capture_mode": capture_mode,
        "artifact_provenance": {
            "definition": "definition.json",
            "telemetry": "telemetry.csv",
            "events": "events.jsonl",
            "detail": "detail.json",
            "result": "result.json",
        },
        "active_channel": channel_name,
        "channel_map": {
            channel_name: {
                "channel_name": channel_name,
                "metric_name": "metric_raw",
                "timestamps_ms": timestamps_ms,
                "temperature_celsius": temperatures_celsius,
                "values": channel_values,
                "metric_norm": metric_norm,
                "quality": quality_values,
                "point_a_px": point_a_series,
                "point_b_px": point_b_series,
            }
        },
        "temperature_series_celsius": temperatures_celsius,
        "timestamps_ms": timestamps_ms,
        "definition": _definition_payload(definition),
        "preprocessing_defaults": dict(DEFAULT_AFAS_PREPROCESSING_PARAMETERS),
        "analysis_defaults": dict(DEFAULT_AFAS_ANALYSIS_PARAMETERS),
        "rates": dict(rates),
        "measurement_profile": dict(measurement_profile),
        "warnings": list(warnings),
        "live_result_snapshot": dict(live_result_snapshot),
    }


def _definition_payload(definition: MeasurementDefinition) -> dict[str, Any]:
    return {
        "analysis_roi": {
            "x": definition.analysis_roi.x,
            "y": definition.analysis_roi.y,
            "width": definition.analysis_roi.width,
            "height": definition.analysis_roi.height,
        },
        "metric_box": {
            "center_x": definition.metric_box.center_x,
            "center_y": definition.metric_box.center_y,
            "width": definition.metric_box.width,
            "height": definition.metric_box.height,
            "angle_deg": definition.metric_box.angle_deg,
        },
        "point_a_px": {
            "x": definition.point_a_px.x,
            "y": definition.point_a_px.y,
        },
        "point_b_px": {
            "x": definition.point_b_px.x,
            "y": definition.point_b_px.y,
        },
        "observation_axis": definition.observation_axis.value,
        "foreground_polarity": definition.foreground_polarity,
        "threshold_mode": definition.threshold_mode,
        "ignore_internal_texture": definition.ignore_internal_texture,
        "min_target_area_px": definition.min_target_area_px,
        "sensitivity": definition.sensitivity,
        "direction_angle_deg": definition.direction_angle_deg,
        "direction_projection_mode": definition.direction_projection_mode,
        "width_extreme_mode": resolve_width_extreme_mode(definition),
        "target_geometry_mode": definition.target_geometry_mode,
        "side_guard_ratio": definition.side_guard_ratio,
        "envelope_min_support_px": definition.envelope_min_support_px,
        "envelope_quantile": definition.envelope_quantile,
        "envelope_normal_bin_width_px": definition.envelope_normal_bin_width_px,
        "envelope_lateral_window_bins": definition.envelope_lateral_window_bins,
        "envelope_endpoint_support_radius_px": definition.envelope_endpoint_support_radius_px,
        "envelope_endpoint_min_support_px": definition.envelope_endpoint_min_support_px,
        "envelope_relocate_confirm_frames": definition.envelope_relocate_confirm_frames,
        "envelope_near_tie_span_ratio": definition.envelope_near_tie_span_ratio,
        "envelope_immediate_span_gain_ratio": definition.envelope_immediate_span_gain_ratio,
    }
