from pathlib import Path

from fastapi.testclient import TestClient

from src.workflow import camera_probe as camera_probe_module
from src.webapp.app import create_app
from src.webapp.deps import get_camera_probe_runner
from src.workflow.camera_probe import run_camera_probe


class FakeProbeHandle:
    def __init__(
        self,
        frame: object | None = None,
        *,
        model: str = "MV-CU060-10GM",
        serial_number: str = "",
        ip: str = "",
    ) -> None:
        self.frame = frame if frame is not None else [[0, 255], [255, 0]]
        self.opened = False
        self.model = model
        self.serial_number = serial_number
        self.ip = ip

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
    assert payload["error_code"] == "BACKEND_NOT_SUPPORTED"
    assert payload["error_stage"] == "config_contract"
    assert "does not support real GigE probe" in payload["detail"]


def test_camera_probe_api_supports_protocol_any_without_identity(tmp_path: Path) -> None:
    client = _make_client(tmp_path, profile="prod_win")

    def fake_runner(runtime_config, override=None):
        return run_camera_probe(
            runtime_config,
            override=override,
            camera_factory=lambda: FakeProbeHandle(
                frame=[[0, 255, 0], [255, 0, 255]],
                model="DISCOVERED-MODEL",
                serial_number="DISCOVERED-001",
                ip="192.168.1.88",
            ),
        )

    client.app.dependency_overrides[get_camera_probe_runner] = lambda: fake_runner

    response = client.post("/api/system/camera/probe", json={"probe_mode": "protocol_any"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["error_code"] is None
    assert payload["error_stage"] is None
    assert payload["probe_mode"] == "protocol_any"
    assert payload["matched_by"] == "first_discovered"
    assert payload["device"]["model"] == "DISCOVERED-MODEL"
    assert payload["identity"]["serial_number"] == "DISCOVERED-001"
    assert payload["identity"]["ip"] == "192.168.1.88"
    assert payload["frame"]["width"] == 3
    assert payload["frame"]["height"] == 2
    assert "image" not in payload
    assert "image" not in payload["frame"]


def test_camera_probe_api_fails_for_pinned_mode_without_identity(tmp_path: Path) -> None:
    client = _make_client(tmp_path, profile="prod_win")

    response = client.post(
        "/api/system/camera/probe",
        json={"probe_mode": "pinned", "allowed_models": ["MV-CU060-10GM"]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "fail"
    assert payload["probe_mode"] == "pinned"
    assert payload["error_code"] == "PINNED_IDENTITY_MISSING"
    assert payload["error_stage"] == "config_contract"
    assert payload["detail"] == "Pinned probe mode requires serial_number or ip before probing."


def test_camera_probe_api_fails_when_pinned_mode_has_no_allowed_models(tmp_path: Path) -> None:
    client = _make_client(tmp_path, profile="prod_win")

    response = client.post(
        "/api/system/camera/probe",
        json={"probe_mode": "pinned", "allowed_models": [], "serial_number": "MV-SERIAL-001"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "fail"
    assert payload["error_code"] == "ALLOWED_MODELS_MISSING"
    assert payload["error_stage"] == "config_contract"


def test_camera_probe_api_pinned_mode_succeeds_when_allowlist_and_serial_match(tmp_path: Path) -> None:
    client = _make_client(tmp_path, profile="prod_win")

    def fake_runner(runtime_config, override=None):
        return run_camera_probe(
            runtime_config,
            override=override,
            camera_factory=lambda: FakeProbeHandle(
                frame=[[0, 255], [255, 0]],
                model="MV-CU060-10GM",
                serial_number="MV-SERIAL-001",
                ip="192.168.1.10",
            ),
        )

    client.app.dependency_overrides[get_camera_probe_runner] = lambda: fake_runner

    response = client.post(
        "/api/system/camera/probe",
        json={
            "probe_mode": "pinned",
            "allowed_models": ["MV-CU060-10GM"],
            "serial_number": "MV-SERIAL-001",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["error_code"] is None
    assert payload["error_stage"] is None
    assert payload["probe_mode"] == "pinned"
    assert payload["matched_by"] == "serial_number"
    assert payload["device"]["model"] == "MV-CU060-10GM"
    assert payload["identity"]["serial_number"] == "MV-SERIAL-001"


def test_camera_probe_api_fails_when_detected_model_is_outside_allowlist(tmp_path: Path) -> None:
    client = _make_client(tmp_path, profile="prod_win")

    def fake_runner(runtime_config, override=None):
        return run_camera_probe(
            runtime_config,
            override=override,
            camera_factory=lambda: FakeProbeHandle(
                frame=[[0, 255], [255, 0]],
                model="OTHER-MODEL",
                serial_number="MV-SERIAL-001",
                ip="192.168.1.10",
            ),
        )

    client.app.dependency_overrides[get_camera_probe_runner] = lambda: fake_runner

    response = client.post(
        "/api/system/camera/probe",
        json={
            "probe_mode": "pinned",
            "allowed_models": ["MV-CU060-10GM"],
            "serial_number": "MV-SERIAL-001",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "fail"
    assert payload["error_code"] == "DETECTED_MODEL_NOT_ALLOWED"
    assert payload["error_stage"] == "device_validation"
    assert payload["device"]["model"] == "OTHER-MODEL"
    assert "not in the allowed_models whitelist" in payload["detail"]


def test_camera_probe_api_fails_for_invalid_probe_mode(tmp_path: Path) -> None:
    client = _make_client(tmp_path, profile="prod_win")

    response = client.post("/api/system/camera/probe", json={"probe_mode": "broken_mode"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "fail"
    assert payload["error_code"] == "PROBE_MODE_INVALID"
    assert payload["error_stage"] == "config_contract"


def test_camera_probe_api_reports_sdk_import_not_ready(tmp_path: Path, monkeypatch) -> None:
    client = _make_client(tmp_path, profile="prod_win")
    client.app.state.runtime_config.camera["probe_mode"] = "protocol_any"
    client.app.state.runtime_config.camera["allowed_models"] = []

    def fake_import() -> object:
        raise RuntimeError("Hik MVS SDK Python binding MvCameraControl_class is not importable on this machine.")

    monkeypatch.setattr(camera_probe_module, "import_hik_mvs_sdk_module", fake_import)

    response = client.post("/api/system/camera/probe")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "fail"
    assert payload["error_code"] == "SDK_IMPORT_NOT_READY"
    assert payload["error_stage"] == "sdk_runtime"
    assert "No live device access was attempted." in payload["detail"]


def test_camera_probe_api_reports_frame_read_failure(tmp_path: Path) -> None:
    client = _make_client(tmp_path, profile="prod_win")

    class BrokenFrameHandle(FakeProbeHandle):
        def read_frame(self, *, timeout_ms: int = 1000) -> object | None:
            return None

    def fake_runner(runtime_config, override=None):
        return run_camera_probe(
            runtime_config,
            override=override,
            camera_factory=lambda: BrokenFrameHandle(
                model="DISCOVERED-MODEL",
                serial_number="DISCOVERED-001",
                ip="192.168.1.77",
            ),
        )

    client.app.dependency_overrides[get_camera_probe_runner] = lambda: fake_runner

    response = client.post("/api/system/camera/probe", json={"probe_mode": "protocol_any"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "fail"
    assert payload["error_code"] == "FRAME_READ_FAILED"
    assert payload["error_stage"] == "frame_read"


def test_camera_probe_api_request_body_overrides_profile_default_mode(tmp_path: Path) -> None:
    client = _make_client(tmp_path, profile="prod_win")

    def fake_runner(runtime_config, override=None):
        return run_camera_probe(
            runtime_config,
            override=override,
            camera_factory=lambda: FakeProbeHandle(
                frame=[[0, 255]],
                model="DISCOVERED-MODEL",
                serial_number="DISCOVERED-001",
                ip="192.168.1.77",
            ),
        )

    client.app.dependency_overrides[get_camera_probe_runner] = lambda: fake_runner

    response = client.post("/api/system/camera/probe", json={"probe_mode": "protocol_any"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["error_code"] is None
    assert payload["error_stage"] is None
    assert payload["probe_mode"] == "protocol_any"
    assert payload["matched_by"] == "first_discovered"
