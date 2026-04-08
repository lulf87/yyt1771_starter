from src.application.live_preview_service import LivePreviewService
from src.application.live_run_service import (
    _augment_telemetry_for_setup_preview,
    _composite_tracking_frame_into_setup_preview,
)
from src.core.models import FramePacket


def test_augment_telemetry_for_setup_preview_adds_preview_coordinates() -> None:
    row = {
        "point_a_px": [80, 92],
        "point_b_px": [280, 92],
    }
    measurement_capture_plan = {
        "effective_local_origin_in_setup_preview_px": {
            "x": 840,
            "y": 568,
        }
    }

    _augment_telemetry_for_setup_preview(row, measurement_capture_plan)

    assert row["point_a_preview_px"] == [920, 660]
    assert row["point_b_preview_px"] == [1120, 660]


def test_composite_tracking_frame_into_setup_preview_pastes_measurement_frame_into_cached_preview() -> None:
    preview_service = LivePreviewService()
    preview_service.cache_frame(
        run_id="run-001",
        frame=FramePacket(
            timestamp_ms=1_000,
            source="setup_preview",
            image=[
                [10, 10, 10, 10, 10],
                [10, 10, 10, 10, 10],
                [10, 10, 10, 10, 10],
                [10, 10, 10, 10, 10],
            ],
            frame_id=1,
        ),
    )
    measurement_frame = FramePacket(
        timestamp_ms=2_000,
        source="measurement",
        image=[
            [200, 201],
            [202, 203],
        ],
        frame_id=2,
    )
    measurement_capture_plan = {
        "effective_local_origin_in_setup_preview_px": {
            "x": 2,
            "y": 1,
        }
    }

    composited = _composite_tracking_frame_into_setup_preview(
        preview_service=preview_service,
        run_id="run-001",
        measurement_frame=measurement_frame,
        measurement_capture_plan=measurement_capture_plan,
    )

    assert composited.frame_id == 2
    assert composited.meta["tracking_composited"] is True
    assert composited.meta["tracking_origin_px"] == [2, 1]
    assert composited.image.tolist() == [
        [10, 10, 10, 10, 10],
        [10, 10, 200, 201, 10],
        [10, 10, 202, 203, 10],
        [10, 10, 10, 10, 10],
    ]
