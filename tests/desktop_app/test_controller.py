import time
from pathlib import Path

from src.core.enums import RunStatus
from src.core.models import MeasurementDefinition, MetricBox, PixelPoint, RectRegion
from src.desktop_app.controller import DesktopWorkbenchController, build_desktop_app_context


def _sample_definition() -> MeasurementDefinition:
    return MeasurementDefinition(
        analysis_roi=RectRegion(x=0, y=0, width=96, height=64),
        metric_box=MetricBox(center_x=48, center_y=32, width=80, height=24, angle_deg=0.0),
        point_a_px=PixelPoint(x=12, y=32),
        point_b_px=PixelPoint(x=83, y=32),
        foreground_polarity="dark_on_light",
        threshold_mode="adaptive",
        ignore_internal_texture=True,
        min_target_area_px=150,
    )


def test_build_desktop_app_context_uses_shared_application_container() -> None:
    context = build_desktop_app_context(profile="dev_mock")

    assert context.profile == "dev_mock"
    assert context.container.runtime_config is context.runtime_config
    assert context.project_root == Path(__file__).resolve().parents[2]


def test_desktop_workbench_controller_runs_minimum_mock_flow(tmp_path: Path) -> None:
    context = build_desktop_app_context(profile="dev_mock")
    context.runtime_config.storage["sqlite_path"] = str(tmp_path / "desktop.db")
    context.runtime_config.storage["artifact_dir"] = str(tmp_path / "artifacts")
    controller = DesktopWorkbenchController(context)

    precheck = controller.get_precheck()
    run = controller.create_run(preset="balloon")
    first_frame = controller.start_preview(run.run_id)
    stopped_snapshot = controller.stop_preview(run.run_id)
    updated = controller.save_definition(run.run_id, _sample_definition())
    controller.start_live_run(run.run_id, target_temperature_celsius=80.0)

    deadline = time.time() + 3.0
    current = updated
    while time.time() < deadline:
        current = controller.get_run(run.run_id)
        assert current is not None
        if current.status == RunStatus.COMPLETED:
            break
        time.sleep(0.05)
    else:
        raise AssertionError(f"desktop controller did not complete run; last status={current.status.value}")

    result = controller.get_result(run.run_id)
    detail = controller.get_detail(run.run_id)
    telemetry = controller.get_telemetry(run.run_id)

    assert precheck["profile"] == "dev_mock"
    assert first_frame.source == "mock_camera"
    assert stopped_snapshot.frozen_frame_available is True
    assert updated.status == RunStatus.RUN_READY
    assert result is not None
    assert detail is not None
    assert telemetry is not None
