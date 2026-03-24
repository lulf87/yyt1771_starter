"""JSON-backed storage for lightweight session detail artifacts."""

from __future__ import annotations

import csv
import json
from pathlib import Path
import struct
from typing import Any
import zlib


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
        telemetry: list[dict[str, Any]],
        detail: dict[str, Any],
        result: dict[str, Any],
        events: list[dict[str, Any]],
        keyframes: list[dict[str, Any]] | None = None,
    ) -> Path:
        session_dir = self._session_dir(session_id)
        session_dir.mkdir(parents=True, exist_ok=True)

        (session_dir / "definition.json").write_text(
            json.dumps(definition, ensure_ascii=True, indent=2),
            encoding="utf-8",
        )
        (session_dir / "detail.json").write_text(
            json.dumps(detail, ensure_ascii=True, indent=2),
            encoding="utf-8",
        )
        (session_dir / "result.json").write_text(
            json.dumps(result, ensure_ascii=True, indent=2),
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

    def get_result(self, session_id: str) -> dict[str, Any] | None:
        path = self._session_dir(session_id) / "result.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

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
            path.write_bytes(_encode_grayscale_png(image))


def _encode_grayscale_png(image: list[list[int]]) -> bytes:
    width = len(image[0]) if image else 1
    height = len(image) if image else 1
    raw = bytearray()
    for row in image:
        raw.append(0)
        raw.extend(max(0, min(255, int(value))) for value in row)

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


def _decode_telemetry_row(row: dict[str, str]) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "timestamp_ms": int(row["timestamp_ms"]),
        "temperature_celsius": float(row["temperature_celsius"]),
        "space1_px": float(row["space1_px"]),
        "tracking_quality": float(row["tracking_quality"]),
    }
    for key in (
        "sample_index",
        "sample_interval_ms",
        "frame_id",
        "frame_timestamp_ms",
        "temp_timestamp_ms",
        "metric_timestamp_ms",
    ):
        value = _optional_csv_int(row.get(key))
        if value is not None:
            payload[key] = value
    camera_resulting_fps = _optional_csv_float(row.get("camera_resulting_fps"))
    if camera_resulting_fps is not None:
        payload["camera_resulting_fps"] = camera_resulting_fps
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
