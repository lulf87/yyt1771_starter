"""Parameterized AFAS tangent analysis for the full postprocessing pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import numpy as np
from scipy.stats import linregress


AFAS_ANALYSIS_SCHEMA_VERSION = "afas_postprocessing_analysis.v1"


@dataclass(slots=True)
class AfasAnalysisParameters:
    """Canonical tangent-analysis parameters for post-run AFAS review."""

    low_range_celsius: tuple[float, float] | None = None
    high_range_celsius: tuple[float, float] | None = None
    tangent_offset: int = 0

    @classmethod
    def from_mapping(
        cls,
        defaults: Mapping[str, Any] | None,
        overrides: Mapping[str, Any] | None = None,
    ) -> AfasAnalysisParameters:
        merged: dict[str, Any] = {}
        if defaults is not None:
            merged.update(dict(defaults))
        if overrides is not None:
            merged.update(dict(overrides))
        return cls(
            low_range_celsius=_normalize_range(merged.get("low_range_celsius")),
            high_range_celsius=_normalize_range(merged.get("high_range_celsius")),
            tangent_offset=int(merged.get("tangent_offset", 0)),
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "low_range_celsius": None
            if self.low_range_celsius is None
            else [float(self.low_range_celsius[0]), float(self.low_range_celsius[1])],
            "high_range_celsius": None
            if self.high_range_celsius is None
            else [float(self.high_range_celsius[0]), float(self.high_range_celsius[1])],
            "tangent_offset": self.tangent_offset,
        }


def compute_derivative(
    temps: Sequence[float],
    values: Sequence[float],
) -> np.ndarray:
    """Compute dValue / dTemperature using numpy.gradient."""

    temperatures = np.asarray(temps, dtype=float)
    channel_values = np.asarray(values, dtype=float)
    if len(temperatures) != len(channel_values):
        raise ValueError(f"Length mismatch: temps ({len(temperatures)}) != values ({len(channel_values)})")
    if len(temperatures) < 2:
        raise ValueError(f"Need at least 2 points to compute derivative, got {len(temperatures)}")
    return np.gradient(channel_values, temperatures)


def find_max_slope_index(derivatives: Sequence[float], offset: int = 0) -> int:
    """Find the index of the maximum absolute slope, with optional offset."""

    derivative_values = np.asarray(derivatives, dtype=float)
    if len(derivative_values) == 0:
        raise ValueError("derivatives array cannot be empty")
    max_abs_index = int(np.argmax(np.abs(derivative_values)))
    adjusted_index = max_abs_index + int(offset)
    return max(0, min(adjusted_index, len(derivative_values) - 1))


def fit_baseline(
    temps: Sequence[float],
    values: Sequence[float],
    t_start: float,
    t_end: float,
) -> tuple[float, float]:
    """Fit a baseline line on the specified temperature interval."""

    temperatures = np.asarray(temps, dtype=float)
    channel_values = np.asarray(values, dtype=float)
    mask = (temperatures >= float(t_start)) & (temperatures <= float(t_end))
    range_temperatures = temperatures[mask]
    range_values = channel_values[mask]
    if len(range_temperatures) == 0:
        raise ValueError(f"No data points in temperature range [{t_start}, {t_end}]")
    if len(range_temperatures) < 2:
        raise ValueError(f"Need at least 2 points for baseline fitting, got {len(range_temperatures)}")
    result = linregress(range_temperatures, range_values)
    return float(result.slope), float(result.intercept)


def compute_tangent_at_point(
    temps: Sequence[float],
    values: Sequence[float],
    derivatives: Sequence[float],
    index: int,
) -> tuple[float, float]:
    """Build the tangent line at the chosen max-slope point."""

    temperatures = np.asarray(temps, dtype=float)
    channel_values = np.asarray(values, dtype=float)
    derivative_values = np.asarray(derivatives, dtype=float)
    if len(temperatures) != len(channel_values) or len(temperatures) != len(derivative_values):
        raise ValueError("temps, values, and derivatives must have the same length")
    if not 0 <= int(index) < len(temperatures):
        raise ValueError(f"Index {index} out of bounds [0, {len(temperatures) - 1}]")

    slope = float(derivative_values[int(index)])
    x0 = float(temperatures[int(index)])
    y0 = float(channel_values[int(index)])
    return slope, float(y0 - slope * x0)


def find_intersection(
    slope1: float,
    intercept1: float,
    slope2: float,
    intercept2: float,
) -> float | None:
    """Return the x-coordinate where two lines intersect."""

    if np.isclose(float(slope1), float(slope2)):
        return None
    return float((float(intercept2) - float(intercept1)) / (float(slope1) - float(slope2)))


def analyze_preprocessed_afas_channel(
    preprocessing_result: Mapping[str, Any],
    *,
    parameter_overrides: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Run parameterized tangent analysis on a preprocessing result payload."""

    smoothed = dict(preprocessing_result["smoothed"])
    temperatures = np.asarray(smoothed["temperature_celsius"], dtype=float)
    channel_values = np.asarray(smoothed["values"], dtype=float)
    outlier_count = int(preprocessing_result["outlier_repair"]["outlier_count"])
    parameters = AfasAnalysisParameters.from_mapping(
        preprocessing_result.get("analysis_defaults"),
        parameter_overrides,
    )

    warnings: list[str] = list(preprocessing_result.get("warnings", []))
    if len(temperatures) < 10:
        return {
            "schema_version": AFAS_ANALYSIS_SCHEMA_VERSION,
            "preprocessing_schema_version": preprocessing_result.get("schema_version"),
            "session_id": preprocessing_result.get("session_id"),
            "channel_name": preprocessing_result.get("channel_name"),
            "parameters": parameters.to_payload(),
            "result_status": "unavailable",
            "reason": "insufficient_points",
            "detail": f"Need at least 10 points for postprocessing tangent analysis, got {len(temperatures)}.",
            "warnings": warnings,
            "outlier_count": outlier_count,
            "series": {
                "temperature_celsius": temperatures.tolist(),
                "values": channel_values.tolist(),
                "derivative": [],
            },
            "fit": {},
        }

    low_range, high_range, auto_range_messages = _resolve_ranges(temperatures, parameters)
    warnings.extend(auto_range_messages)

    derivatives = compute_derivative(temperatures, channel_values)
    max_slope_index = find_max_slope_index(derivatives, offset=parameters.tangent_offset)
    max_slope_temp = float(temperatures[max_slope_index])
    max_slope_value = float(channel_values[max_slope_index])
    tangent_slope, tangent_intercept = compute_tangent_at_point(
        temperatures,
        channel_values,
        derivatives,
        max_slope_index,
    )
    low_slope, low_intercept = fit_baseline(temperatures, channel_values, *low_range)
    high_slope, high_intercept = fit_baseline(temperatures, channel_values, *high_range)
    as_value = find_intersection(tangent_slope, tangent_intercept, low_slope, low_intercept)
    af_tan = find_intersection(tangent_slope, tangent_intercept, high_slope, high_intercept)

    result_status = "ok"
    reason = None
    detail = "Parameterized tangent analysis completed."
    if as_value is None or af_tan is None:
        result_status = "unavailable"
        reason = "parallel_lines"
        detail = "Tangent and baseline fitting produced parallel lines; intersections are unavailable."
    elif af_tan <= as_value:
        result_status = "unavailable"
        reason = "invalid_result"
        detail = f"Non-increasing intersections were produced: As={as_value:.3f}, Af-tan={af_tan:.3f}."

    return {
        "schema_version": AFAS_ANALYSIS_SCHEMA_VERSION,
        "preprocessing_schema_version": preprocessing_result.get("schema_version"),
        "session_id": preprocessing_result.get("session_id"),
        "channel_name": preprocessing_result.get("channel_name"),
        "parameters": {
            **parameters.to_payload(),
            "resolved_low_range_celsius": [float(low_range[0]), float(low_range[1])],
            "resolved_high_range_celsius": [float(high_range[0]), float(high_range[1])],
        },
        "result_status": result_status,
        "reason": reason,
        "detail": detail,
        "warnings": warnings,
        "outlier_count": outlier_count,
        "series": {
            "temperature_celsius": temperatures.tolist(),
            "values": channel_values.tolist(),
            "derivative": derivatives.tolist(),
        },
        "fit": {
            "max_slope_index": int(max_slope_index),
            "max_slope_temperature_celsius": max_slope_temp,
            "max_slope_value": max_slope_value,
            "low_baseline": {
                "range_celsius": [float(low_range[0]), float(low_range[1])],
                "slope": low_slope,
                "intercept": low_intercept,
            },
            "high_baseline": {
                "range_celsius": [float(high_range[0]), float(high_range[1])],
                "slope": high_slope,
                "intercept": high_intercept,
            },
            "tangent": {
                "slope": tangent_slope,
                "intercept": tangent_intercept,
            },
        },
        "result": {
            "As": as_value,
            "Af_tan": af_tan,
            "max_slope_temp": max_slope_temp,
        },
    }


def _normalize_range(value: Any) -> tuple[float, float] | None:
    if value is None:
        return None
    if isinstance(value, (list, tuple)) and len(value) == 2:
        return float(value[0]), float(value[1])
    raise ValueError("analysis range values must be [start, end] pairs")


def _resolve_ranges(
    temperatures: np.ndarray,
    parameters: AfasAnalysisParameters,
) -> tuple[tuple[float, float], tuple[float, float], list[str]]:
    warnings: list[str] = []
    if parameters.low_range_celsius is not None and parameters.high_range_celsius is not None:
        return parameters.low_range_celsius, parameters.high_range_celsius, warnings

    temp_min = float(np.min(temperatures))
    temp_max = float(np.max(temperatures))
    span = temp_max - temp_min
    if span <= 0:
        raise ValueError("temperature span must be positive for tangent analysis")

    auto_band = span * 0.2
    low_range = parameters.low_range_celsius or (temp_min, temp_min + auto_band)
    high_range = parameters.high_range_celsius or (temp_max - auto_band, temp_max)
    if parameters.low_range_celsius is None:
        warnings.append("low_range_celsius was not provided; using the first 20% of the temperature span.")
    if parameters.high_range_celsius is None:
        warnings.append("high_range_celsius was not provided; using the last 20% of the temperature span.")
    return low_range, high_range, warnings
