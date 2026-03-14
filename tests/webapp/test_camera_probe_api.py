from pathlib import Path

from fastapi.testclient import TestClient

from src.webapp.app import create_app
from src.webapp.deps import get_camera_probe_runner
from src.workflow.camera_probe import run_camera_probe


class FakeProbeHandle:
    def __init__(self, frame: object | None = None) -> None:
        self.frame = frame if frame is not None else [[0, 255], [255, 0]]
        self.opened = False

    def open(self) -> None:
        self.opened = True

    def is_opened(self) -> bool:
        return self.opened

    def read_frame(self, *, timeout_ms: int = 1000) -> object:
        return self.frame

    def close(self) -> None:
        self.opened = False


def _make_client(tmp_path: Path, profile: str) -> TestClient:
    app = create_app(profile=profile)
    app.state.runtime_config.storage["sqlite_path"] = str(tmp_path / f"{profile}.db")
    app.state.runtime_config.storage["artifact_dir"] = str(tmp_path / "artifacts")
    return TestClient(app)


def test_camera_probe_api_fails_for_dev_mock_backend(tmp_path: Path) -> None:
    client = _make_client(tmp_path, profile="dev_mock")

    response = client.post("/api/system/camera/probe")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "fail"
    assert payload["backend"] == "mock"
    assert "does not support real GigE probe" in payload["detail"]


def test_camera_probe_api_fails_when_prod_identity_is_missing(tmp_path: Path) -> None:
    client = _make_client(tmp_path, profile="prod_win")

    response = client.post("/api/system/camera/probe")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "fail"
    assert payload["backend"] == "hik_gige_mvs"
    assert payload["model"] == "MV-CU060-10GM"
    assert payload["detail"] == "Camera identity is missing. Configure serial_number or ip before probing."


def test_camera_probe_api_returns_ok_with_injected_fake_probe(tmp_path: Path) -> None:
    client = _make_client(tmp_path, profile="prod_win")
    client.app.state.runtime_config.camera["serial_number"] = "MV-SERIAL-001"

    def fake_runner(runtime_config):
        return run_camera_probe(
            runtime_config,
            camera_factory=lambda: FakeProbeHandle(frame=[[0, 255, 0], [255, 0, 255]]),
        )

    client.app.dependency_overrides[get_camera_probe_runner] = lambda: fake_runner

    response = client.post("/api/system/camera/probe")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["backend"] == "hik_gige_mvs"
    assert payload["model"] == "MV-CU060-10GM"
    assert payload["identity"]["serial_number"] == "MV-SERIAL-001"
    assert payload["frame"]["width"] == 3
    assert payload["frame"]["height"] == 2
    assert payload["frame"]["pixel_format"] == "mono8"
    assert "image" not in payload
    assert "image" not in payload["frame"]
