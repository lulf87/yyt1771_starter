"""JSON-backed storage for live-run artifacts, including AFAS datasets."""

from __future__ import annotations

import csv
from dataclasses import dataclass
import json
from pathlib import Path
import struct
from typing import Any
import zlib

from src.vision.metric_two_point_distance import downsample_grayscale_image, normalize_frame_image

_DETAIL_KEYFRAME_MAX_WIDTH = 160
_DETAIL_KEYFRAME_MAX_HEIGHT = 120
_ARTIFACT_KEYFRAME_MAX_WIDTH = 512
_ARTIFACT_KEYFRAME_MAX_HEIGHT = 512
_AFAS_ANALYSIS_ARTIFACT_NAME = "afas_analysis.json"
_AFAS_PLOT_ARTIFACT_NAME = "afas_plot.png"
_AFAS_REPORT_ARTIFACT_NAME = "afas_report.xlsx"
_DEFINITION_ORIGINAL_ARTIFACT_NAME = "definition_original.json"
_DEFINITION_EFFECTIVE_LOCAL_ARTIFACT_NAME = "definition_effective_local.json"
_MEASUREMENT_CAPTURE_PLAN_ARTIFACT_NAME = "measurement_capture_plan.json"


@dataclass(slots=True)
class _PreviewBitmap:
    width: int
    height: int
    pixels: bytes


class SessionArtifactStore:
    def __init__(self, artifact_dir: str | Path) -> None:
        self.artifact_dir = Path(artifact_dir)
        self.artifact_dir.mkdir(parents=True, exist_ok=True)

    def save_detail(self, session_id: str, payload: dict[str, Any]) -> Path:
        path = self._path_for(session_id)
        path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
        return path

    def get_detail(self, session_id: str) -> dict[str, Any] | None:
        live_path = self._session_dir(session_id) / "detail.json"
        if live_path.exists():
            return json.loads(live_path.read_text(encoding="utf-8"))
        replay_path = self._path_for(session_id)
        if replay_path.exists():
            return json.loads(replay_path.read_text(encoding="utf-8"))
        return None

    def save_live_bundle(
        self,
        session_id: str,
        *,
        definition: dict[str, Any],
        definition_original: dict[str, Any] | None = None,
        definition_effective_local: dict[str, Any] | None = None,
        measurement_capture_plan: dict[str, Any] | None = None,
        telemetry: list[dict[str, Any]],
        detail: dict[str, Any],
        result: dict[str, Any],
        events: list[dict[str, Any]],
        afas_dataset: dict[str, Any] | None = None,
        keyframes: list[dict[str, Any]] | None = None,
    ) -> Path:
        session_dir = self._session_dir(session_id)
        session_dir.mkdir(parents=True, exist_ok=True)

        (session_dir / "definition.json").write_text(
            json.dumps(definition, ensure_ascii=True, indent=2),
            encoding="utf-8",
        )
        if definition_original is not None:
            (session_dir / _DEFINITION_ORIGINAL_ARTIFACT_NAME).write_text(
                json.dumps(definition_original, ensure_ascii=True, indent=2),
                encoding="utf-8",
            )
        if definition_effective_local is not None:
            (session_dir / _DEFINITION_EFFECTIVE_LOCAL_ARTIFACT_NAME).write_text(
                json.dumps(definition_effective_local, ensure_ascii=True, indent=2),
                encoding="utf-8",
            )
        if measurement_capture_plan is not None:
            (session_dir / _MEASUREMENT_CAPTURE_PLAN_ARTIFACT_NAME).write_text(
                json.dumps(measurement_capture_plan, ensure_ascii=True, indent=2),
                encoding="utf-8",
            )
        serializable_detail = _serialize_live_detail(detail)
        (session_dir / "detail.json").write_text(
            json.dumps(serializable_detail, ensure_ascii=True, indent=2),
            encoding="utf-8",
        )
        result_payload = _merge_runtime_artifact_refs(
            result,
            definition_original=_DEFINITION_ORIGINAL_ARTIFACT_NAME if definition_original is not None else None,
            definition_effective_local=
            _DEFINITION_EFFECTIVE_LOCAL_ARTIFACT_NAME if definition_effective_local is not None else None,
            measurement_capture_plan=
            _MEASUREMENT_CAPTURE_PLAN_ARTIFACT_NAME if measurement_capture_plan is not None else None,
        )
        result.clear()
        result.update(result_payload)
        (session_dir / "result.json").write_text(
            json.dumps(result_payload, ensure_ascii=True, indent=2),
            encoding="utf-8",
        )
        if afas_dataset is not None:
            (session_dir / "afas_dataset.json").write_text(
                json.dumps(afas_dataset, ensure_ascii=True, indent=2),
                encoding="utf-8",
            )

        telemetry_path = session_dir / "telemetry.csv"
        with telemetry_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "timestamp_ms",
                    "sample_index",
                    "sample_interval_ms",
                    "frame_id",
                    "frame_timestamp_ms",
                    "temp_timestamp_ms",
                    "metric_timestamp_ms",
                    "camera_resulting_fps",
                    "temperature_celsius",
                    "space1_px",
                    "tracking_quality",
                    "point_a_px",
                    "point_b_px",
                    "tracking_mode",
                    "tracking_state",
                    "selection_mode",
                    "reason",
                    "observation_selection_mode",
                    "observation_reason",
                    "component_area",
                    "threshold_value",
                    "endpoint_jump_px",
                    "midpoint_drift_px",
                    "span_change_ratio",
                    "consecutive_misses",
                    "frame_read_ms",
                    "temp_read_ms",
                    "metric_extract_ms",
                    "sample_loop_ms",
                    "telemetry_row_ms",
                    "sample_callbacks_ms",
                    "post_sample_ms",
                ],
                extrasaction="ignore",
            )
            writer.writeheader()
            writer.writerows(telemetry)

        events_path = session_dir / "events.jsonl"
        with events_path.open("w", encoding="utf-8") as handle:
            for event in events:
                handle.write(json.dumps(event, ensure_ascii=True))
                handle.write("\n")

        self._write_keyframes(session_dir, keyframes or [])

        return session_dir

    def save_imported_afas_bundle(
        self,
        session_id: str,
        *,
        detail: dict[str, Any],
        afas_dataset: dict[str, Any],
        result: dict[str, Any] | None = None,
        afas_analysis: dict[str, Any] | None = None,
    ) -> Path:
        session_dir = self._session_dir(session_id)
        session_dir.mkdir(parents=True, exist_ok=True)

        serializable_detail = _serialize_live_detail(detail)
        (session_dir / "detail.json").write_text(
            json.dumps(serializable_detail, ensure_ascii=True, indent=2),
            encoding="utf-8",
        )
        (session_dir / "afas_dataset.json").write_text(
            json.dumps(afas_dataset, ensure_ascii=True, indent=2),
            encoding="utf-8",
        )
        if result is not None:
            (session_dir / "result.json").write_text(
                json.dumps(result, ensure_ascii=True, indent=2),
                encoding="utf-8",
            )
        if afas_analysis is not None:
            (session_dir / _AFAS_ANALYSIS_ARTIFACT_NAME).write_text(
                json.dumps(afas_analysis, ensure_ascii=True, indent=2),
                encoding="utf-8",
            )
        return session_dir

    def session_exists(self, session_id: str) -> bool:
        session_dir = self._session_dir(session_id)
        return session_dir.exists() or self._path_for(session_id).exists()

    def get_result(self, session_id: str) -> dict[str, Any] | None:
        path = self._session_dir(session_id) / "result.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def get_afas_dataset(self, session_id: str) -> dict[str, Any] | None:
        path = self._session_dir(session_id) / "afas_dataset.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def save_afas_analysis(self, session_id: str, payload: dict[str, Any]) -> Path:
        path = self._session_dir(session_id) / _AFAS_ANALYSIS_ARTIFACT_NAME
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
        self._merge_result_artifact_refs(session_id, afas_analysis=_AFAS_ANALYSIS_ARTIFACT_NAME)
        return path

    def get_afas_analysis(self, session_id: str) -> dict[str, Any] | None:
        path = self._session_dir(session_id) / _AFAS_ANALYSIS_ARTIFACT_NAME
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def save_afas_plot(self, session_id: str, png_bytes: bytes) -> Path:
        path = self._session_dir(session_id) / _AFAS_PLOT_ARTIFACT_NAME
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(png_bytes)
        self._merge_result_artifact_refs(session_id, afas_plot=_AFAS_PLOT_ARTIFACT_NAME)
        return path

    def save_afas_report(self, session_id: str, workbook_bytes: bytes) -> Path:
        path = self._session_dir(session_id) / _AFAS_REPORT_ARTIFACT_NAME
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(workbook_bytes)
        self._merge_result_artifact_refs(session_id, afas_report=_AFAS_REPORT_ARTIFACT_NAME)
        return path

    def get_telemetry(self, session_id: str) -> list[dict[str, Any]] | None:
        path = self._session_dir(session_id) / "telemetry.csv"
        if not path.exists():
            return None

        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            return [_decode_telemetry_row(row) for row in reader]

    def validate_live_bundle(self, session_id: str, *, expected_keyframes: list[str] | None = None) -> list[str]:
        session_dir = self._session_dir(session_id)
        missing: list[str] = []
        for name in ("definition.json", "telemetry.csv", "events.jsonl", "detail.json", "result.json"):
            if not (session_dir / name).exists():
                missing.append(name)
        result = self.get_result(session_id)
        artifact_refs = {} if result is None else dict(result.get("artifacts", {}))
        for key in (
            "afas_dataset",
            "afas_analysis",
            "afas_plot",
            "afas_report",
            "definition_original",
            "definition_effective_local",
            "measurement_capture_plan",
        ):
            artifact_ref = artifact_refs.get(key)
            if artifact_ref and not (session_dir / str(artifact_ref)).exists():
                missing.append(str(artifact_ref))
        for keyframe in expected_keyframes or []:
            if not (session_dir / keyframe).exists():
                missing.append(keyframe)
        return missing

    def _path_for(self, session_id: str) -> Path:
        return self.artifact_dir / f"{session_id}.json"

    def _session_dir(self, session_id: str) -> Path:
        return self.artifact_dir / session_id

    def _write_keyframes(self, session_dir: Path, keyframes: list[dict[str, Any]]) -> None:
        if not keyframes:
            return
        keyframe_dir = session_dir / "keyframes"
        keyframe_dir.mkdir(parents=True, exist_ok=True)
        for keyframe in keyframes:
            label = str(keyframe.get("label", "") or "").strip()
            image = keyframe.get("image")
            if not label or image is None:
                continue
            path = keyframe_dir / f"{label}.png"
            bitmap = _build_preview_bitmap(
                image,
                max_width=_ARTIFACT_KEYFRAME_MAX_WIDTH,
                max_height=_ARTIFACT_KEYFRAME_MAX_HEIGHT,
            )
            path.write_bytes(_encode_grayscale_png_bitmap(bitmap))

    def _merge_result_artifact_refs(self, session_id: str, **refs: str | None) -> None:
        result_path = self._session_dir(session_id) / "result.json"
        if not result_path.exists():
            return
        payload = json.loads(result_path.read_text(encoding="utf-8"))
        artifact_payload = dict(payload.get("artifacts", {}))
        for key, value in refs.items():
            if value is not None:
                artifact_payload[key] = value
        payload["artifacts"] = artifact_payload
        result_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


def _merge_runtime_artifact_refs(payload: dict[str, Any], **refs: str | None) -> dict[str, Any]:
    merged_payload = dict(payload)
    artifact_payload = dict(merged_payload.get("artifacts", {}))
    for key, value in refs.items():
        artifact_payload[key] = value
    merged_payload["artifacts"] = artifact_payload
    return merged_payload


def _encode_grayscale_png_bitmap(bitmap: _PreviewBitmap) -> bytes:
    width = bitmap.width
    height = bitmap.height
    raw = bytearray(height * (width + 1))
    write_index = 0
    pixel_index = 0
    for _ in range(height):
        raw[write_index] = 0
        write_index += 1
        row_end = pixel_index + width
        raw[write_index : write_index + width] = bitmap.pixels[pixel_index:row_end]
        write_index += width
        pixel_index = row_end

    def _chunk(chunk_type: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + chunk_type
            + data
            + struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
        )

    signature = b"\x89PNG\r\n\x1a\n"
    ihdr = _chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0))
    idat = _chunk(b"IDAT", zlib.compress(bytes(raw)))
    iend = _chunk(b"IEND", b"")
    return signature + ihdr + idat + iend


def _serialize_live_detail(detail: dict[str, Any]) -> dict[str, Any]:
    payload = dict(detail)
    key_frames = payload.get("key_frames")
    if not isinstance(key_frames, list):
        return payload
    sanitized_key_frames: list[dict[str, Any]] = []
    for key_frame in key_frames:
        if isinstance(key_frame, dict):
            sanitized_key_frame = dict(key_frame)
            image = sanitized_key_frame.get("image")
            if image is not None:
                sanitized_key_frame["image"] = _build_preview_rows(
                    image,
                    max_width=_DETAIL_KEYFRAME_MAX_WIDTH,
                    max_height=_DETAIL_KEYFRAME_MAX_HEIGHT,
                )
            sanitized_key_frames.append(sanitized_key_frame)
        else:
            sanitized_key_frames.append(key_frame)
    payload["key_frames"] = sanitized_key_frames
    return payload


def _build_preview_rows(image: Any, *, max_width: int, max_height: int) -> list[list[int]]:
    native_downsample = getattr(image, "downsample_rows", None)
    if callable(native_downsample):
        preview_rows = native_downsample(max_width=max_width, max_height=max_height)
        if preview_rows:
            return preview_rows
    return downsample_grayscale_image(
        normalize_frame_image(image),
        max_width=max_width,
        max_height=max_height,
    )


def _build_preview_bitmap(image: Any, *, max_width: int, max_height: int) -> _PreviewBitmap:
    native_bitmap_payload = getattr(image, "downsample_bitmap_payload", None)
    if callable(native_bitmap_payload):
        width, height, pixels = native_bitmap_payload(max_width=max_width, max_height=max_height)
        return _PreviewBitmap(width=width, height=height, pixels=pixels)
    rows = _build_preview_rows(image, max_width=max_width, max_height=max_height)
    width = len(rows[0]) if rows else 1
    height = len(rows) if rows else 1
    pixels = bytearray()
    for row in rows:
        pixels.extend(max(0, min(255, int(value))) for value in row)
    return _PreviewBitmap(width=width, height=height, pixels=bytes(pixels))


def _decode_telemetry_row(row: dict[str, str]) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "timestamp_ms": int(row["timestamp_ms"]),
        "temperature_celsius": float(row["temperature_celsius"]),
        "space1_px": float(row["space1_px"]),
        "tracking_quality": float(row["tracking_quality"]),
    }
    for key in ("point_a_px", "point_b_px"):
        value = _optional_csv_json_array(row.get(key))
        if value is not None:
            payload[key] = value
    for key in (
        "sample_index",
        "sample_interval_ms",
        "frame_id",
        "frame_timestamp_ms",
        "temp_timestamp_ms",
        "metric_timestamp_ms",
        "component_area",
        "consecutive_misses",
    ):
        value = _optional_csv_int(row.get(key))
        if value is not None:
            payload[key] = value
    for key in (
        "camera_resulting_fps",
        "threshold_value",
        "endpoint_jump_px",
        "midpoint_drift_px",
        "span_change_ratio",
        "frame_read_ms",
        "temp_read_ms",
        "metric_extract_ms",
        "sample_loop_ms",
        "telemetry_row_ms",
        "sample_callbacks_ms",
        "post_sample_ms",
    ):
        value = _optional_csv_float(row.get(key))
        if value is not None:
            payload[key] = value
    for key in (
        "tracking_mode",
        "tracking_state",
        "selection_mode",
        "reason",
        "observation_selection_mode",
        "observation_reason",
    ):
        value = _optional_csv_text(row.get(key))
        if value is not None:
            payload[key] = value
    return payload


def _optional_csv_int(value: str | None) -> int | None:
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    return int(text)


def _optional_csv_float(value: str | None) -> float | None:
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    return float(text)


def _optional_csv_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    return text


def _optional_csv_json_array(value: str | None) -> list[int] | None:
    text = _optional_csv_text(value)
    if text is None:
        return None
    parsed = json.loads(text)
    if not isinstance(parsed, list) or len(parsed) != 2:
        return None
    return [int(parsed[0]), int(parsed[1])]
