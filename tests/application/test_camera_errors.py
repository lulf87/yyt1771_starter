from src.application.camera_errors import normalize_camera_runtime_error


def test_normalize_hik_open_device_access_denied_error() -> None:
    detail = normalize_camera_runtime_error(
        RuntimeError("Failed to open device via Hik MVS SDK (ret=0x80000203)")
    )

    assert "Hik MVS camera access denied" in detail
    assert "0x80000203" in detail
    assert "another camera client" in detail
    assert "not connected" in detail


def test_normalize_hik_sdk_import_error() -> None:
    detail = normalize_camera_runtime_error(
        RuntimeError("Hik MVS SDK Python binding MvCameraControl_class is not importable on this machine.")
    )

    assert "Hik MVS SDK is not available" in detail
    assert "No live camera access was attempted" in detail
