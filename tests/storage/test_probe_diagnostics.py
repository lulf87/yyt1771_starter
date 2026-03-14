from pathlib import Path

from src.storage.probe_diagnostics import ProbeDiagnosticStore


def test_probe_diagnostic_store_appends_and_reads_jsonl_entries(tmp_path: Path) -> None:
    store = ProbeDiagnosticStore(tmp_path / "logs")

    store.append(
        {
            "timestamp_ms": 1,
            "profile": "dev_lab",
            "status": "fail",
            "probe_mode": "protocol_any",
            "matched_by": "first_discovered",
            "backend": "hik_gige_mvs",
            "transport": "gige_vision",
            "sdk": "hik_mvs",
            "device_model": "",
            "device_serial_number": "",
            "device_ip": "",
            "frame_width": 0,
            "frame_height": 0,
            "pixel_format": "",
            "frame_id": 0,
            "frame_timestamp_ms": 0,
            "error_code": "SDK_IMPORT_NOT_READY",
            "error_stage": "sdk_runtime",
            "detail": "sdk import failed",
        }
    )
    store.append(
        {
            "timestamp_ms": 2,
            "profile": "prod_win",
            "status": "ok",
            "probe_mode": "pinned",
            "matched_by": "serial_number",
            "backend": "hik_gige_mvs",
            "transport": "gige_vision",
            "sdk": "hik_mvs",
            "device_model": "MV-CU060-10GM",
            "device_serial_number": "MV-001",
            "device_ip": "192.168.1.10",
            "frame_width": 3072,
            "frame_height": 2048,
            "pixel_format": "mono8",
            "frame_id": 1,
            "frame_timestamp_ms": 123456789,
            "error_code": None,
            "error_stage": None,
            "detail": "ok",
        }
    )

    items = store.read_all()

    assert store.file_path == tmp_path / "logs" / "probe_diagnostics" / "camera_probe.jsonl"
    assert len(items) == 2
    assert items[0]["error_code"] == "SDK_IMPORT_NOT_READY"
    assert items[1]["status"] == "ok"
    assert items[1]["device_model"] == "MV-CU060-10GM"
