from src.core.models import MeasurementDefinition, MetricBox, PixelPoint, RectRegion
from src.desktop_app.overlay_math import (
    clamp_metric_box_to_roi,
    ensure_definition_geometry,
    metric_box_corners,
    point_in_rotated_metric_box,
    seed_points_for_metric_box,
)


def test_seed_points_for_metric_box_places_points_along_window_axis() -> None:
    box = MetricBox(center_x=50, center_y=40, width=60, height=20, angle_deg=0.0)

    point_a, point_b = seed_points_for_metric_box(box)

    assert point_a == PixelPoint(x=32, y=40)
    assert point_b == PixelPoint(x=68, y=40)


def test_clamp_metric_box_to_roi_keeps_window_inside_roi() -> None:
    roi = RectRegion(x=10, y=20, width=100, height=60)
    box = MetricBox(center_x=500, center_y=-100, width=500, height=120, angle_deg=15.0)

    clamped = clamp_metric_box_to_roi(roi, box)

    assert clamped.width == 100
    assert clamped.height == 60
    assert 10 <= clamped.center_x <= 110
    assert 20 <= clamped.center_y <= 80


def test_ensure_definition_geometry_reseeds_points_outside_metric_box() -> None:
    definition = MeasurementDefinition(
        analysis_roi=RectRegion(x=0, y=0, width=120, height=80),
        metric_box=MetricBox(center_x=60, center_y=40, width=80, height=20, angle_deg=0.0),
        point_a_px=PixelPoint(x=0, y=0),
        point_b_px=PixelPoint(x=119, y=79),
        foreground_polarity="dark_on_light",
        threshold_mode="adaptive",
        ignore_internal_texture=True,
        min_target_area_px=150,
    )

    normalized = ensure_definition_geometry(definition)

    assert point_in_rotated_metric_box(normalized.metric_box, normalized.point_a_px.x, normalized.point_a_px.y)
    assert point_in_rotated_metric_box(normalized.metric_box, normalized.point_b_px.x, normalized.point_b_px.y)


def test_metric_box_corners_return_four_points() -> None:
    corners = metric_box_corners(MetricBox(center_x=50, center_y=40, width=20, height=10, angle_deg=30.0))

    assert len(corners) == 4
