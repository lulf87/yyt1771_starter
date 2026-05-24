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

    deadline = time.time() + 5.0
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
    assert updated.status == RunStatus.DEFINITION_EDITING
    assert result is not None
    assert detail is not None
    assert telemetry is not None


def test_desktop_workbench_controller_exposes_cached_preview_frame_and_smoke_summary(tmp_path: Path) -> None:
    context = build_desktop_app_context(profile="dev_mock")
    context.runtime_config.storage["sqlite_path"] = str(tmp_path / "desktop-smoke.db")
    context.runtime_config.storage["artifact_dir"] = str(tmp_path / "desktop-smoke-artifacts")
    controller = DesktopWorkbenchController(context)

    run = controller.create_run(preset="balloon")
    first_frame = controller.start_preview(run.run_id)
    cached_frame = controller.get_cached_preview_frame(run.run_id)
    controller.stop_preview(run.run_id)

    summary = controller.run_bootstrap_smoke()

    assert cached_frame is not None
    assert cached_frame.frame_id is not None
    assert first_frame.frame_id is not None
    assert cached_frame.frame_id >= first_frame.frame_id
    assert summary["profile"] == "dev_mock"
    assert summary["run_status"] == RunStatus.COMPLETED.value
    assert summary["definition_complete"] is True
    assert summary["result_available"] is True
    assert summary["detail_available"] is True
    assert summary["telemetry_points"] > 0


def test_desktop_workbench_controller_reports_preview_benchmark_summary(tmp_path: Path) -> None:
    context = build_desktop_app_context(profile="dev_mock")
    context.runtime_config.storage["sqlite_path"] = str(tmp_path / "desktop-preview.db")
    context.runtime_config.storage["artifact_dir"] = str(tmp_path / "desktop-preview-artifacts")
    context.runtime_config.live.run.preview_target_fps = 50.0
    context.runtime_config.live.run.preview_poll_ms = 20
    controller = DesktopWorkbenchController(context)

    summary = controller.run_preview_benchmark(duration_s=0.25)

    assert summary["profile"] == "dev_mock"
    assert summary["run_id"].startswith("run-")
    assert summary["presented_frames"] >= 2
    assert summary["measured_presented_fps"] > 0
    assert summary["preview_display_fps"] is not None
    assert summary["frozen_frame_available"] is True
    assert summary["target_preview_fps"] == 50.0
