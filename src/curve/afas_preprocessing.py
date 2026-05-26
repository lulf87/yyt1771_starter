"""AFAS full-postprocessing preprocessing stage."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import numpy as np
from scipy.signal import savgol_filter


AFAS_PREPROCESSING_SCHEMA_VERSION = "afas_preprocessing_result.v1"
MAX_SAVGOL_WINDOW_DATA_FRACTION = 0.55


@dataclass(slots=True)
class AfasPreprocessingParameters:
    """Canonical preprocessing parameters shared by post-run AFAS analysis."""

    group_by_temperature: bool = True
    outlier_window: int = 11
    outlier_threshold: float = 5.0
    outlier_max_iterations: int = 3
    savgol_window_length: int = 51
    savgol_polyorder: int = 3

    @classmethod
    def from_mapping(
        cls,
        defaults: Mapping[str, Any] | None,
        overrides: Mapping[str, Any] | None = None,
    ) -> AfasPreprocessingParameters:
        merged: dict[str, Any] = {}
        if defaults is not None:
            merged.update(dict(defaults))
        if overrides is not None:
            merged.update(dict(overrides))
        return cls(
            group_by_temperature=bool(merged.get("group_by_temperature", True)),
            outlier_window=int(merged.get("outlier_window", 11)),
            outlier_threshold=float(merged.get("outlier_threshold", 5.0)),
            outlier_max_iterations=int(merged.get("outlier_max_iterations", 3)),
            savgol_window_length=int(merged.get("savgol_window_length", 51)),
            savgol_polyorder=int(merged.get("savgol_polyorder", 3)),
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "group_by_temperature": self.group_by_temperature,
            "outlier_window": self.outlier_window,
            "outlier_threshold": self.outlier_threshold,
            "outlier_max_iterations": self.outlier_max_iterations,
            "savgol_window_length": self.savgol_window_length,
            "savgol_polyorder": self.savgol_polyorder,
        }


def group_by_temperature(
    temps: Sequence[float],
    values: Sequence[float],
) -> tuple[np.ndarray, np.ndarray]:
    """Aggregate repeated temperatures into a single mean value per temperature."""

    temperatures = np.asarray(temps, dtype=float)
    channel_values = np.asarray(values, dtype=float)

    if len(temperatures) != len(channel_values):
        raise ValueError(f"Length mismatch: temps ({len(temperatures)}) != values ({len(channel_values)})")

    if len(temperatures) == 0:
        return np.array([], dtype=float), np.array([], dtype=float)

    valid_mask = ~np.isnan(channel_values)
    temperatures = temperatures[valid_mask]
    channel_values = channel_values[valid_mask]
    if len(temperatures) == 0:
        return np.array([], dtype=float), np.array([], dtype=float)

    order = np.argsort(temperatures, kind="mergesort")
    sorted_temperatures = temperatures[order]
    sorted_values = channel_values[order]
    unique_temperatures, inverse_indexes, counts = np.unique(
        sorted_temperatures,
        return_inverse=True,
        return_counts=True,
    )
    sums = np.zeros(len(unique_temperatures), dtype=float)
    np.add.at(sums, inverse_indexes, sorted_values)
    means = sums / counts
    return unique_temperatures, means


def remove_outliers(
    temps: Sequence[float],
    values: Sequence[float],
    window: int = 11,
    threshold: float = 5.0,
    max_iterations: int = 3,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Iteratively repair spikes with rolling-median plus MAD thresholding."""

    temperatures = np.asarray(temps, dtype=float)
    channel_values = np.asarray(values, dtype=float)

    if len(temperatures) != len(channel_values):
        raise ValueError(f"Length mismatch: temps ({len(temperatures)}) != values ({len(channel_values)})")

    sample_count = len(channel_values)
    if sample_count < window + 2:
        return temperatures.copy(), channel_values.copy(), np.zeros(sample_count, dtype=bool)

    window = max(int(window), 11)
    if window % 2 == 0:
        window += 1

    combined_mask = np.zeros(sample_count, dtype=bool)
    working_values = channel_values.copy()
    min_periods = window // 2 + 1

    for _ in range(max_iterations):
        rolling_med = _rolling_median(working_values, window=window, min_periods=min_periods)
        deviations = np.abs(working_values - rolling_med)
        boundary = max(window // 2, 3)
        inner_mask = np.ones(sample_count, dtype=bool)
        inner_mask[:boundary] = False
        inner_mask[-boundary:] = False
        inner_mask[combined_mask] = False
        valid_devs = deviations[inner_mask & ~np.isnan(deviations)]

        if len(valid_devs) == 0:
            break

        mad = float(np.median(valid_devs))
        if np.isnan(mad):
            mad = 0.0
        data_range = float(np.nanmax(working_values) - np.nanmin(working_values))
        mad = max(mad, data_range * 0.01, 1.0)

        outlier_threshold = float(threshold) * mad
        new_mask = deviations > outlier_threshold
        new_mask[:boundary] = False
        new_mask[-boundary:] = False
        new_mask[combined_mask] = False
        if not np.any(new_mask):
            break

        combined_mask |= new_mask
        normal_indexes = np.where(~combined_mask)[0]
        outlier_indexes = np.where(combined_mask)[0]
        if len(normal_indexes) >= 2:
            working_values[outlier_indexes] = np.interp(
                outlier_indexes,
                normal_indexes,
                channel_values[~combined_mask],
            )

    return temperatures, working_values, combined_mask


def smooth_data(
    temps: Sequence[float],
    values: Sequence[float],
    window_length: int = 51,
    polyorder: int = 3,
) -> tuple[np.ndarray, np.ndarray]:
    """Apply Savitzky-Golay smoothing while keeping temperature positions intact."""

    temperatures = np.asarray(temps, dtype=float)
    channel_values = np.asarray(values, dtype=float)

    if len(temperatures) != len(channel_values):
        raise ValueError(f"Length mismatch: temps ({len(temperatures)}) != values ({len(channel_values)})")
    if len(temperatures) == 0:
        return np.array([], dtype=float), np.array([], dtype=float)

    corrected_window = int(window_length)
    if corrected_window % 2 == 0:
        corrected_window += 1
    if corrected_window <= int(polyorder):
        raise ValueError(
            f"window_length ({corrected_window}) must be greater than polyorder ({int(polyorder)})"
        )
    if corrected_window > len(channel_values):
        raise ValueError(
            f"window_length ({corrected_window}) cannot be larger than data length ({len(channel_values)})"
        )

    return temperatures, savgol_filter(channel_values, corrected_window, int(polyorder))


def preprocess_afas_channel(
    dataset: Mapping[str, Any],
    *,
    channel_name: str | None = None,
    parameter_overrides: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a canonical preprocessing result for one AFAS dataset channel."""

    resolved_channel = channel_name or str(dataset["active_channel"])
    channel_payload = dict(dataset["channel_map"][resolved_channel])
    parameters = AfasPreprocessingParameters.from_mapping(
        dataset.get("preprocessing_defaults"),
        parameter_overrides,
    )

    raw_temperatures = np.asarray(channel_payload["temperature_celsius"], dtype=float)
    raw_values = np.asarray(channel_payload["values"], dtype=float)
    raw_timestamps = [int(value) for value in channel_payload.get("timestamps_ms", [])]

    grouped_temperatures = raw_temperatures
    grouped_values = raw_values
    if parameters.group_by_temperature:
        grouped_temperatures, grouped_values = group_by_temperature(raw_temperatures, raw_values)

    repaired_temperatures, repaired_values, outlier_mask = remove_outliers(
        grouped_temperatures,
        grouped_values,
        window=parameters.outlier_window,
        threshold=parameters.outlier_threshold,
        max_iterations=parameters.outlier_max_iterations,
    )

    warnings: list[str] = []
    smoothing_applied = True
    effective_savgol_window_length: int | None = int(parameters.savgol_window_length)
    smoothing_warning: str | None = _full_length_savgol_window_warning(
        len(repaired_values),
        window_length=parameters.savgol_window_length,
    )
    if smoothing_warning is not None:
        smoothing_applied = False
        effective_savgol_window_length = None
        smoothed_temperatures = repaired_temperatures.copy()
        smoothed_values = repaired_values.copy()
    else:
        effective_savgol_window_length, edge_window_warning = _edge_safe_savgol_window_length(
            len(repaired_values),
            window_length=parameters.savgol_window_length,
            polyorder=parameters.savgol_polyorder,
        )
        if edge_window_warning is not None:
            warnings.append(edge_window_warning)
        try:
            smoothed_temperatures, smoothed_values = smooth_data(
                repaired_temperatures,
                repaired_values,
                window_length=effective_savgol_window_length,
                polyorder=parameters.savgol_polyorder,
            )
        except ValueError as exc:
            smoothing_applied = False
            effective_savgol_window_length = None
            smoothing_warning = str(exc)
            smoothed_temperatures = repaired_temperatures.copy()
            smoothed_values = repaired_values.copy()

    if smoothing_warning is not None:
        warnings.append(smoothing_warning)

    return {
        "schema_version": AFAS_PREPROCESSING_SCHEMA_VERSION,
        "dataset_schema_version": dataset.get("schema_version"),
        "session_id": dataset.get("session_id"),
        "channel_name": resolved_channel,
        "parameters": parameters.to_payload(),
        "analysis_defaults": dict(dataset.get("analysis_defaults", {})),
        "raw": {
            "temperature_celsius": raw_temperatures.tolist(),
            "values": raw_values.tolist(),
            "timestamps_ms": raw_timestamps,
        },
        "grouped": {
            "temperature_celsius": grouped_temperatures.tolist(),
            "values": grouped_values.tolist(),
            "applied": parameters.group_by_temperature,
        },
        "outlier_repair": {
            "temperature_celsius": repaired_temperatures.tolist(),
            "values": repaired_values.tolist(),
            "outlier_mask": outlier_mask.astype(bool).tolist(),
            "outlier_count": int(np.count_nonzero(outlier_mask)),
        },
        "smoothed": {
            "temperature_celsius": smoothed_temperatures.tolist(),
            "values": smoothed_values.tolist(),
            "applied": smoothing_applied,
            "effective_savgol_window_length": effective_savgol_window_length,
        },
        "warnings": warnings,
    }


def _full_length_savgol_window_warning(data_length: int, *, window_length: int) -> str | None:
    if int(data_length) <= 0:
        return None
    corrected_window = int(window_length)
    if corrected_window % 2 == 0:
        corrected_window += 1
    if corrected_window != int(data_length):
        return None
    return (
        f"window_length ({corrected_window}) covers the full data length ({int(data_length)}); "
        "smoothing skipped to avoid global Savitzky-Golay edge distortion"
    )


def _edge_safe_savgol_window_length(
    data_length: int,
    *,
    window_length: int,
    polyorder: int,
) -> tuple[int, str | None]:
    corrected_window = int(window_length)
    if corrected_window % 2 == 0:
        corrected_window += 1
    if int(data_length) <= 0 or corrected_window > int(data_length):
        return corrected_window, None

    max_fractional_window = int(int(data_length) * MAX_SAVGOL_WINDOW_DATA_FRACTION)
    if max_fractional_window % 2 == 0:
        max_fractional_window -= 1
    min_valid_window = int(polyorder) + 2
    if min_valid_window % 2 == 0:
        min_valid_window += 1
    max_fractional_window = max(max_fractional_window, min_valid_window)
    max_fractional_window = min(max_fractional_window, int(data_length))
    if max_fractional_window % 2 == 0:
        max_fractional_window -= 1

    if corrected_window <= max_fractional_window:
        return corrected_window, None
    return (
        max_fractional_window,
        (
            f"window_length ({corrected_window}) reduced to {max_fractional_window} "
            "to avoid Savitzky-Golay edge distortion"
        ),
    )


def _rolling_median(values: np.ndarray, *, window: int, min_periods: int) -> np.ndarray:
    """Compute a centered rolling median without depending on pandas."""

    sample_count = len(values)
    half_window = window // 2
    medians = np.full(sample_count, np.nan, dtype=float)
    for index in range(sample_count):
        start = max(0, index - half_window)
        stop = min(sample_count, index + half_window + 1)
        window_values = values[start:stop]
        if len(window_values) < min_periods:
            continue
        medians[index] = float(np.median(window_values))
    return medians
