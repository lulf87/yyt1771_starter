import numpy as np
import pytest
import math

from src.core.models import FramePacket, MetricBox, PixelPoint, RectRegion
import src.vision.contour_direction as contour_direction
from src.vision.contour_direction import (
    DirectionalContourConfig,
    DirectionalContourMetricExtractor,
    detect_directional_contour,
    project_component_mask_onto_direction,
    project_points_onto_direction,
)


def _point_in_rotated_metric_box(box: MetricBox, point: PixelPoint) -> bool:
    angle_rad = np.deg2rad(box.angle_deg)
    cos_theta = float(np.cos(angle_rad))
    sin_theta = float(np.sin(angle_rad))
    translated_x = float(point.x) - float(box.center_x)
    translated_y = float(point.y) - float(box.center_y)
    local_x = translated_x * cos_theta + translated_y * sin_theta
    local_y = -translated_x * sin_theta + translated_y * cos_theta
    return abs(local_x) <= float(box.width) / 2.0 and abs(local_y) <= float(box.height) / 2.0


def test_directional_contour_extracts_boundary_ab_from_main_component() -> None:
    image = np.full((12, 20), 240, dtype=np.uint8)
    image[4:7, 3:12] = 30
    config = DirectionalContourConfig(
        analysis_roi=RectRegion(x=0, y=0, width=20, height=12),
        direction_angle_deg=0.0,
        threshold_mode="binary",
        min_target_area_px=6,
    )

    result = detect_directional_contour(image, config)

    assert result.point_a.x == 3
    assert result.point_b.x == 11
    assert result.point_a.y == result.point_b.y == 5
    assert result.point_a == result.axis_point_a
    assert result.point_b == result.axis_point_b
    assert result.metric_raw == 8.0
    assert result.component_area >= 20


def test_directional_contour_config_defaults_match_offline_truth_ab_contract() -> None:
    config = DirectionalContourConfig(
        analysis_roi=RectRegion(x=0, y=0, width=2048, height=1364),
        direction_angle_deg=0.0,
    )

    assert config.foreground_polarity == "dark_on_light"
    assert config.threshold_mode == "adaptive"
    assert config.ignore_internal_texture is False
    assert config.min_target_area_px == 200
    assert config.projection_mode == "max_chord"


def test_directional_contour_refines_downsampled_boundary_points_on_original_frame() -> None:
    image = np.full((120, 1000), 230, dtype=np.uint8)
    image[46:55, 123:877] = 20
    config = DirectionalContourConfig(
        analysis_roi=RectRegion(x=0, y=0, width=1000, height=120),
        direction_angle_deg=0.0,
        threshold_mode="binary",
        threshold_value=100.0,
        foreground_polarity="dark_on_light",
        min_target_area_px=20,
        processing_max_side_px=120,
        projection_mode="mask_projection",
    )

    result = detect_directional_contour(image, config)

    assert result.metric_raw == pytest.approx(753.0, abs=2.0)
    assert result.point_a.x == pytest.approx(123, abs=2)
    assert result.point_b.x == pytest.approx(876, abs=2)
    assert image[result.point_a.y, result.point_a.x] == 20
    assert image[result.point_b.y, result.point_b.x] == 20


def test_directional_contour_respects_rotated_metric_box_mask() -> None:
    image = np.full((120, 160), 240, dtype=np.uint8)
    metric_box = MetricBox(center_x=82, center_y=66, width=74, height=22, angle_deg=24.0)
    angle_rad = np.deg2rad(metric_box.angle_deg)
    cos_theta = float(np.cos(angle_rad))
    sin_theta = float(np.sin(angle_rad))

    # A longer distracting contour inside the axis-aligned analysis ROI but
    # outside the rotated ROI must not define A/B.
    image[14:18, 8:150] = 30

    for local_x in range(-31, 32):
        for local_y in range(-3, 4):
            world_x = int(round(metric_box.center_x + local_x * cos_theta - local_y * sin_theta))
            world_y = int(round(metric_box.center_y + local_x * sin_theta + local_y * cos_theta))
            if 0 <= world_x < image.shape[1] and 0 <= world_y < image.shape[0]:
                image[world_y, world_x] = 30

    result = detect_directional_contour(
        image,
        DirectionalContourConfig(
            analysis_roi=RectRegion(x=0, y=0, width=160, height=120),
            metric_box=metric_box,
            direction_angle_deg=metric_box.angle_deg,
            threshold_mode="binary",
            foreground_polarity="dark_on_light",
            min_target_area_px=20,
            sensitivity=0.0,
            projection_mode="mask_projection",
        ),
    )

    assert result.metric_raw == pytest.approx(62.0, abs=4.0)
    assert _point_in_rotated_metric_box_with_tolerance(metric_box, result.point_a)
    assert _point_in_rotated_metric_box_with_tolerance(metric_box, result.point_b)
    assert result.point_a.y > 40
    assert result.point_b.y > 40


def test_directional_contour_uses_requested_direction_not_world_extremes() -> None:
    points = np.array(
        [
            [4.0, 12.0],
            [7.0, 9.0],
            [10.0, 6.0],
            [13.0, 3.0],
        ],
        dtype=float,
    )

    projection = project_points_onto_direction(points, -45.0, image_shape=(20, 20))

    assert projection.point_a.x == 4
    assert projection.point_a.y == 12
    assert projection.point_b.x == 13
    assert projection.point_b.y == 3
    assert projection.metric_raw > 12.0


def test_direction_selection_returns_contour_extrema_without_axis_projection() -> None:
    points = np.array(
        [
            [30.0, 0.0],
            [31.0, 0.0],
            [10.0, 60.0],
            [11.0, 60.0],
            [40.0, 30.0],
        ],
        dtype=float,
    )

    projection = project_points_onto_direction(points, 90.0, image_shape=(80, 80))

    assert (projection.point_a.x, projection.point_a.y) == (30, 0)
    assert (projection.point_b.x, projection.point_b.y) == (10, 60)
    assert (projection.source_point_a.x, projection.source_point_a.y) == (30, 0)
    assert (projection.source_point_b.x, projection.source_point_b.y) == (10, 60)
    assert projection.axis_point_a == projection.point_a
    assert projection.axis_point_b == projection.point_b
    assert projection.metric_raw == pytest.approx(np.hypot(20.0, 60.0))


def test_directional_ab_points_are_contour_points_not_axis_projections() -> None:
    points = np.array(
        [
            [30.0, 0.0],
            [31.0, 0.0],
            [10.0, 60.0],
            [11.0, 60.0],
            [40.0, 30.0],
        ],
        dtype=float,
    )

    projection = project_points_onto_direction(points, 90.0, image_shape=(80, 80))

    assert projection.point_a == projection.source_point_a
    assert projection.point_b == projection.source_point_b
    assert (projection.point_a.x, projection.point_a.y) == (30, 0)
    assert (projection.point_b.x, projection.point_b.y) == (10, 60)


def test_direction_selection_does_not_create_parallel_axis_points() -> None:
    points = np.array(
        [
            [163.0, 129.0],
            [457.0, 131.0],
            [320.0, 260.0],
            [345.0, 60.0],
        ],
        dtype=float,
    )

    projection = project_points_onto_direction(points, -70.0, image_shape=(320, 520))
    assert projection.point_a == projection.source_point_a
    assert projection.point_b == projection.source_point_b
    assert projection.axis_point_a == projection.point_a
    assert projection.axis_point_b == projection.point_b


def test_directional_contour_uses_contour_boundary_points_for_oblique_direction() -> None:
    image = np.full((90, 140), 240, dtype=np.uint8)
    yy, xx = np.mgrid[0 : image.shape[0], 0 : image.shape[1]]
    body = ((xx - 70.0) / 42.0) ** 2 + ((yy - 45.0) / 14.0) ** 2 <= 1.0
    image[body] = 30
    config = DirectionalContourConfig(
        analysis_roi=RectRegion(x=0, y=0, width=140, height=90),
        direction_angle_deg=-25.0,
        threshold_mode="binary",
        foreground_polarity="dark_on_light",
        min_target_area_px=80,
        sensitivity=0.0,
        projection_mode="mask_projection",
    )

    result = detect_directional_contour(image, config)
    assert result.point_a == result.source_point_a == result.axis_point_a
    assert result.point_b == result.source_point_b == result.axis_point_b
    assert image[result.point_a.y, result.point_a.x] == 30
    assert image[result.point_b.y, result.point_b.x] == 30
    assert result.projection_point_mode == "mask_projection"


def test_directional_contour_max_chord_finds_widest_parallel_contour_section() -> None:
    image = np.full((160, 240), 240, dtype=np.uint8)
    yy, xx = np.mgrid[0 : image.shape[0], 0 : image.shape[1]]
    body = ((xx - 120.0) / 70.0) ** 2 + ((yy - 80.0) / 22.0) ** 2 <= 1.0
    image[body] = 30
    config = DirectionalContourConfig(
        analysis_roi=RectRegion(x=20, y=35, width=200, height=90),
        direction_angle_deg=-70.0,
        threshold_mode="binary",
        foreground_polarity="dark_on_light",
        min_target_area_px=400,
        sensitivity=0.0,
        projection_mode="max_chord",
    )

    result = detect_directional_contour(image, config)
    same_direction_selection = project_component_mask_onto_direction(
        result.component_mask,
        result.roi,
        -70.0,
        image_shape=image.shape,
        clip_region=result.roi,
    )
    direction = contour_direction.directional_unit_vector(-70.0)
    normal = np.array([-direction[1], direction[0]], dtype=float)
    displayed = np.array(
        [
            result.point_b.x - result.point_a.x,
            result.point_b.y - result.point_a.y,
        ],
        dtype=float,
    )
    displayed /= np.linalg.norm(displayed)
    source_a = np.array([result.source_point_a.x, result.source_point_a.y], dtype=float)
    source_b = np.array([result.source_point_b.x, result.source_point_b.y], dtype=float)

    cross = float(direction[0] * displayed[1] - direction[1] * displayed[0])
    assert abs(cross) < 0.04
    assert abs(float(source_a @ normal) - float(source_b @ normal)) <= 3.0
    assert image[result.source_point_a.y, result.source_point_a.x] == 30
    assert image[result.source_point_b.y, result.source_point_b.x] == 30
    assert result.metric_raw == pytest.approx(same_direction_selection.metric_raw, abs=5.0)
    assert result.projection_point_mode == "max_chord"


def test_directional_contour_max_chord_can_follow_axis_prior() -> None:
    image = np.full((70, 110), 230, dtype=np.uint8)
    image[20:24, 24:84] = 35
    image[42:46, 6:104] = 35
    image[20:46, 52:56] = 35
    config = DirectionalContourConfig(
        analysis_roi=RectRegion(x=0, y=0, width=110, height=70),
        direction_angle_deg=0.0,
        foreground_polarity="dark_on_light",
        threshold_mode="binary",
        threshold_value=100.0,
        min_target_area_px=20,
        sensitivity=0.0,
        ignore_internal_texture=False,
        component_bridge_kernel=1,
        open_kernel=1,
        projection_mode="max_chord",
        max_chord_axis_prior_point=PixelPoint(x=54, y=22),
        max_chord_axis_prior_tolerance_px=6.0,
        processing_max_side_px=0,
    )

    result = detect_directional_contour(image, config)

    assert result.metric_raw < 70
    assert abs(result.point_a.y - 22) <= 1
    assert abs(result.point_b.y - 22) <= 1
    assert result.projection_point_mode == "max_chord"


def test_directional_contour_mask_mode_keeps_ab_on_detected_object_with_off_object_prior() -> None:
    image = np.full((70, 110), 230, dtype=np.uint8)
    image[42:46, 6:104] = 35
    config = DirectionalContourConfig(
        analysis_roi=RectRegion(x=0, y=0, width=110, height=70),
        direction_angle_deg=0.0,
        foreground_polarity="dark_on_light",
        threshold_mode="binary",
        threshold_value=100.0,
        min_target_area_px=20,
        sensitivity=0.0,
        ignore_internal_texture=False,
        component_bridge_kernel=1,
        open_kernel=1,
        projection_mode="mask_projection",
        max_chord_axis_prior_point=PixelPoint(x=54, y=22),
        max_chord_axis_prior_tolerance_px=8.0,
        processing_max_side_px=0,
    )

    result = detect_directional_contour(image, config)

    assert result.metric_raw >= 95.0
    assert result.projection_point_mode == "mask_projection"
    assert result.point_a == result.source_point_a == result.axis_point_a
    assert result.point_b == result.source_point_b == result.axis_point_b
    assert result.point_a.y >= 42
    assert result.point_b.y >= 42


def test_directional_contour_mask_projection_uses_prior_band_for_source_extrema() -> None:
    image = np.full((70, 110), 230, dtype=np.uint8)
    image[20:24, 24:84] = 35
    image[42:46, 6:104] = 35
    image[20:46, 52:56] = 35
    config = DirectionalContourConfig(
        analysis_roi=RectRegion(x=0, y=0, width=110, height=70),
        direction_angle_deg=0.0,
        foreground_polarity="dark_on_light",
        threshold_mode="binary",
        threshold_value=100.0,
        min_target_area_px=20,
        sensitivity=0.0,
        ignore_internal_texture=False,
        component_bridge_kernel=1,
        open_kernel=1,
        projection_mode="mask_projection",
        max_chord_axis_prior_point=PixelPoint(x=54, y=22),
        max_chord_axis_prior_tolerance_px=6.0,
        processing_max_side_px=0,
    )

    result = detect_directional_contour(image, config)

    assert result.metric_raw < 70.0
    assert abs(result.point_a.y - 22) <= 1
    assert abs(result.point_b.y - 22) <= 1
    assert abs(result.source_point_a.y - 22) <= 3
    assert abs(result.source_point_b.y - 22) <= 3
    assert 20 <= result.source_point_a.x <= 28
    assert 80 <= result.source_point_b.x <= 88


def test_directional_contour_refinement_keeps_axis_prior_in_original_roi_coordinates() -> None:
    image = np.full((240, 320), 230, dtype=np.uint8)
    image[108:116, 90:170] = 35
    image[148:156, 70:250] = 35
    image[108:156, 148:156] = 35
    config = DirectionalContourConfig(
        analysis_roi=RectRegion(x=50, y=80, width=240, height=120),
        direction_angle_deg=0.0,
        foreground_polarity="dark_on_light",
        threshold_mode="binary",
        threshold_value=100.0,
        min_target_area_px=5,
        sensitivity=0.0,
        ignore_internal_texture=False,
        component_bridge_kernel=1,
        open_kernel=1,
        projection_mode="mask_projection",
        max_chord_axis_prior_point=PixelPoint(x=130, y=112),
        max_chord_axis_prior_tolerance_px=8.0,
        processing_max_side_px=80,
    )

    result = detect_directional_contour(image, config)

    assert result.metric_raw < 100.0
    assert abs(result.point_a.y - 112) <= 2
    assert abs(result.point_b.y - 112) <= 2
    assert image[result.point_a.y, result.point_a.x] == 35
    assert image[result.point_b.y, result.point_b.x] == 35


def test_directional_contour_refinement_keeps_points_inside_rotated_metric_box() -> None:
    image = np.full((800, 1000), 230, dtype=np.uint8)
    metric_box = MetricBox(center_x=500, center_y=350, width=400, height=160, angle_deg=150.0)
    _paint_test_line_local(image, metric_box, -190.0, 310.0, width=17, value=35)
    config = DirectionalContourConfig(
        analysis_roi=RectRegion(x=100, y=80, width=800, height=640),
        metric_box=metric_box,
        direction_angle_deg=150.0,
        foreground_polarity="dark_on_light",
        threshold_mode="binary",
        threshold_value=100.0,
        min_target_area_px=2,
        sensitivity=0.0,
        ignore_internal_texture=False,
        component_bridge_kernel=1,
        open_kernel=1,
        projection_mode="mask_projection",
        processing_max_side_px=120,
    )

    result = detect_directional_contour(image, config)

    assert _point_in_rotated_metric_box_with_tolerance(metric_box, result.point_a)
    assert _point_in_rotated_metric_box_with_tolerance(metric_box, result.point_b)
    assert image[result.point_a.y, result.point_a.x] == 35
    assert image[result.point_b.y, result.point_b.x] == 35


def test_directional_contour_downsampled_refinement_avoids_second_full_component_pass(monkeypatch) -> None:
    image = np.full((800, 1000), 230, dtype=np.uint8)
    metric_box = MetricBox(center_x=500, center_y=350, width=420, height=160, angle_deg=30.0)
    _paint_test_line_local(image, metric_box, -190.0, 190.0, width=15, value=35)
    calls = 0
    original = contour_direction._largest_component_mask

    def counted_largest_component_mask(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(contour_direction, "_largest_component_mask", counted_largest_component_mask)

    result = detect_directional_contour(
        image,
        DirectionalContourConfig(
            analysis_roi=RectRegion(x=240, y=80, width=520, height=540),
            metric_box=metric_box,
            direction_angle_deg=30.0,
            threshold_mode="binary",
            threshold_value=100.0,
            foreground_polarity="dark_on_light",
            min_target_area_px=20,
            sensitivity=0.0,
            component_bridge_kernel=1,
            processing_max_side_px=120,
            projection_mode="max_chord",
        ),
    )

    assert calls == 1
    assert image[result.point_a.y, result.point_a.x] == 35
    assert image[result.point_b.y, result.point_b.x] == 35


def test_directional_contour_quality_uses_rotated_metric_box_reference() -> None:
    image = np.full((800, 1000), 230, dtype=np.uint8)
    metric_box = MetricBox(center_x=500, center_y=350, width=420, height=160, angle_deg=30.0)
    _paint_test_line_local(image, metric_box, -190.0, 190.0, width=15, value=35)
    config = DirectionalContourConfig(
        analysis_roi=RectRegion(x=240, y=80, width=520, height=540),
        metric_box=metric_box,
        direction_angle_deg=30.0,
        foreground_polarity="dark_on_light",
        threshold_mode="binary",
        threshold_value=100.0,
        min_target_area_px=20,
        sensitivity=0.0,
        ignore_internal_texture=False,
        component_bridge_kernel=1,
        open_kernel=1,
        projection_mode="mask_projection",
        processing_max_side_px=0,
    )

    result = detect_directional_contour(image, config)

    assert result.metric_raw >= 360.0
    assert result.quality >= 0.75


def test_directional_contour_quality_accepts_valid_object_smaller_than_roi_box() -> None:
    image = np.full((800, 1000), 230, dtype=np.uint8)
    metric_box = MetricBox(center_x=500, center_y=350, width=420, height=360, angle_deg=90.0)
    _paint_test_line_local(image, metric_box, -120.0, 120.0, width=13, value=35)
    config = DirectionalContourConfig(
        analysis_roi=RectRegion(x=300, y=120, width=400, height=520),
        metric_box=metric_box,
        direction_angle_deg=90.0,
        foreground_polarity="dark_on_light",
        threshold_mode="binary",
        threshold_value=100.0,
        min_target_area_px=20,
        sensitivity=0.0,
        ignore_internal_texture=False,
        component_bridge_kernel=1,
        open_kernel=1,
        projection_mode="mask_projection",
        processing_max_side_px=0,
    )

    result = detect_directional_contour(image, config)

    assert 230.0 <= result.metric_raw <= 260.0
    assert result.quality >= 0.75


def test_directional_contour_auto_selects_max_chord_for_wide_component() -> None:
    image = np.full((160, 240), 240, dtype=np.uint8)
    yy, xx = np.mgrid[0 : image.shape[0], 0 : image.shape[1]]
    body = ((xx - 120.0) / 70.0) ** 2 + ((yy - 80.0) / 22.0) ** 2 <= 1.0
    image[body] = 30
    config = DirectionalContourConfig(
        analysis_roi=RectRegion(x=20, y=35, width=200, height=90),
        direction_angle_deg=-70.0,
        threshold_mode="binary",
        foreground_polarity="dark_on_light",
        min_target_area_px=400,
        sensitivity=0.0,
        projection_mode="auto",
    )

    result = detect_directional_contour(image, config)

    assert result.projection_point_mode == "max_chord"
    assert 40.0 <= result.metric_raw <= 50.0


def test_directional_contour_auto_uses_mask_projection_for_textured_mesh_component() -> None:
    image = np.full((96, 160), 240, dtype=np.uint8)
    image[30:33, 24:136] = 30
    image[62:65, 24:136] = 30
    image[30:65, 24:27] = 30
    image[30:65, 133:136] = 30
    for x in range(36, 128, 12):
        image[33:62, x : x + 3] = 30
    for offset in range(0, 84, 14):
        for step in range(28):
            x = 30 + offset + step
            y = 34 + step
            if 24 <= x < 136 and 30 <= y < 65:
                image[y : y + 2, x : x + 2] = 30

    config = DirectionalContourConfig(
        analysis_roi=RectRegion(x=10, y=20, width=140, height=60),
        direction_angle_deg=0.0,
        threshold_mode="binary",
        foreground_polarity="dark_on_light",
        min_target_area_px=200,
        sensitivity=50.0,
        ignore_internal_texture=True,
        component_bridge_kernel=11,
        projection_mode="auto",
    )

    result = detect_directional_contour(image, config)

    assert result.projection_point_mode == "mask_projection"
    assert result.metric_raw >= 108.0
    assert result.point_a.x <= 28
    assert result.point_b.x >= 132


def test_component_mask_direction_selection_uses_real_boundary_points() -> None:
    mask = np.zeros((64, 128), dtype=np.uint8)
    mask[20:41, 20:80] = 255
    mask[26, 80] = 255
    roi = RectRegion(x=0, y=0, width=128, height=64)

    projection = project_component_mask_onto_direction(mask, roi, -20.0, image_shape=mask.shape)
    direction = contour_direction.directional_unit_vector(-20.0)
    displayed = np.array(
        [
            projection.point_b.x - projection.point_a.x,
            projection.point_b.y - projection.point_a.y,
        ],
        dtype=float,
    )
    displayed /= np.linalg.norm(displayed)
    cross = float(direction[0] * displayed[1] - direction[1] * displayed[0])

    assert abs(cross) < 0.04
    assert projection.point_a == projection.axis_point_a
    assert projection.point_b == projection.axis_point_b
    assert mask[projection.source_point_a.y, projection.source_point_a.x] == 255
    assert mask[projection.source_point_b.y, projection.source_point_b.x] == 255
    assert projection.metric_raw >= 60.0


def test_directional_contour_uses_real_chord_points_for_oblique_wire_like_shape() -> None:
    image = np.full((110, 150), 240, dtype=np.uint8)
    _paint_test_line(image, (22, 78), (86, 48), width=11, value=30)
    _paint_test_line(image, (86, 48), (90, 12), width=11, value=30)
    config = DirectionalContourConfig(
        analysis_roi=RectRegion(x=0, y=0, width=150, height=110),
        direction_angle_deg=-10.0,
        threshold_mode="binary",
        foreground_polarity="dark_on_light",
        min_target_area_px=80,
        sensitivity=0.0,
        component_bridge_kernel=1,
        projection_mode="mask_projection",
    )

    result = detect_directional_contour(image, config)

    assert result.projection_point_mode == "mask_projection"
    assert result.metric_raw > 50.0
    assert abs(result.point_b.y - result.point_a.y) <= 20
    assert image[result.point_a.y, result.point_a.x] == 30
    assert image[result.point_b.y, result.point_b.x] == 30


def test_directional_contour_auto_selects_mask_projection_for_wire_like_shape() -> None:
    image = np.full((110, 150), 240, dtype=np.uint8)
    _paint_test_line(image, (22, 78), (86, 48), width=11, value=30)
    _paint_test_line(image, (86, 48), (90, 12), width=11, value=30)
    config = DirectionalContourConfig(
        analysis_roi=RectRegion(x=0, y=0, width=150, height=110),
        direction_angle_deg=-10.0,
        threshold_mode="binary",
        foreground_polarity="dark_on_light",
        min_target_area_px=80,
        sensitivity=0.0,
        component_bridge_kernel=1,
        projection_mode="auto",
    )

    result = detect_directional_contour(image, config)

    assert result.projection_point_mode == "max_chord"
    assert result.metric_raw > 50.0
    assert abs(result.point_b.y - result.point_a.y) <= 20
    assert image[result.point_a.y, result.point_a.x] == 30
    assert image[result.point_b.y, result.point_b.x] == 30


def test_direction_selection_clips_boundary_points_to_roi() -> None:
    points = np.array(
        [
            [0.0, 598.0],
            [859.0, 220.0],
        ],
        dtype=float,
    )
    roi = RectRegion(x=0, y=220, width=860, height=380)

    projection = project_points_onto_direction(points, -18.0, image_shape=(620, 1120), clip_region=roi)

    assert roi.x <= projection.point_a.x < roi.x + roi.width
    assert roi.y <= projection.point_a.y < roi.y + roi.height
    assert roi.x <= projection.point_b.x < roi.x + roi.width
    assert roi.y <= projection.point_b.y < roi.y + roi.height
    assert projection.metric_raw > 900.0


def test_directional_contour_selects_largest_component_inside_roi() -> None:
    image = np.full((16, 28), 240, dtype=np.uint8)
    image[2:4, 2:5] = 30
    image[7:11, 12:23] = 30
    config = DirectionalContourConfig(
        analysis_roi=RectRegion(x=0, y=0, width=28, height=16),
        direction_angle_deg=0.0,
        threshold_mode="binary",
        min_target_area_px=8,
    )

    result = detect_directional_contour(image, config)

    assert result.point_a.x == 12
    assert result.point_b.x == 22
    assert result.component_area > 30


def test_directional_contour_bridges_nearby_fragments_for_boundary_span() -> None:
    image = np.full((24, 56), 240, dtype=np.uint8)
    image[9:14, 6:20] = 30
    image[9:14, 28:44] = 30
    config = DirectionalContourConfig(
        analysis_roi=RectRegion(x=0, y=0, width=56, height=24),
        direction_angle_deg=0.0,
        threshold_mode="binary",
        foreground_polarity="dark_on_light",
        min_target_area_px=20,
        sensitivity=0.0,
    )

    result = detect_directional_contour(image, config)

    assert result.point_a.x == 6
    assert result.point_b.x == 43
    assert result.metric_raw == pytest.approx(37.0, abs=1.0)


def test_directional_contour_prefers_supported_boundary_chord_over_fake_diagonal_span() -> None:
    image = np.full((64, 72), 240, dtype=np.uint8)
    image[0:31, 34:45] = 30
    image[33:45, 10:28] = 30
    config = DirectionalContourConfig(
        analysis_roi=RectRegion(x=0, y=0, width=72, height=64),
        direction_angle_deg=90.0,
        threshold_mode="binary",
        foreground_polarity="dark_on_light",
        min_target_area_px=80,
        sensitivity=0.0,
        projection_mode="mask_projection",
    )

    result = detect_directional_contour(image, config)

    assert result.point_a.y == 0
    assert result.point_b.y == 30
    assert result.metric_raw == 30.0
    assert image[result.point_a.y, result.point_a.x] == 30
    assert image[result.point_b.y, result.point_b.x] == 30


def test_directional_contour_rejects_projected_distal_gap_as_ab_span() -> None:
    image = np.full((72, 72), 240, dtype=np.uint8)
    image[0:36, 34:50] = 30
    image[49:60, 8:22] = 30
    config = DirectionalContourConfig(
        analysis_roi=RectRegion(x=0, y=0, width=72, height=72),
        direction_angle_deg=90.0,
        threshold_mode="binary",
        foreground_polarity="dark_on_light",
        min_target_area_px=80,
        sensitivity=0.0,
        projection_mode="mask_projection",
    )

    result = detect_directional_contour(image, config)

    assert result.point_a.y == 0
    assert result.point_b.y == 35
    assert result.metric_raw == 35.0
    assert image[result.point_a.y, result.point_a.x] == 30
    assert image[result.point_b.y, result.point_b.x] == 30


def test_directional_contour_preserves_thin_connected_wire_segments() -> None:
    image = np.full((80, 80), 240, dtype=np.uint8)
    image[0:20, 52:62] = 30
    image[62:72, 4:16] = 30
    for index, y in enumerate(range(20, 62)):
        x = 52 - index
        if 12 <= x < 52:
            image[y, x] = 30
    config = DirectionalContourConfig(
        analysis_roi=RectRegion(x=0, y=0, width=80, height=80),
        direction_angle_deg=90.0,
        threshold_mode="binary",
        threshold_value=200.0,
        foreground_polarity="dark_on_light",
        min_target_area_px=80,
        sensitivity=50.0,
        component_bridge_kernel=1,
        projection_mode="mask_projection",
    )

    result = detect_directional_contour(image, config)

    assert result.point_a.y == 0
    assert result.point_b.y >= 19
    assert result.metric_raw >= 19.0
    assert image[result.point_a.y, result.point_a.x] == 30
    assert image[result.point_b.y, result.point_b.x] == 30


def test_directional_contour_quality_accepts_valid_thin_wire_span() -> None:
    image = np.full((120, 160), 240, dtype=np.uint8)
    image[58:63, 20:141] = 30
    config = DirectionalContourConfig(
        analysis_roi=RectRegion(x=0, y=0, width=160, height=120),
        direction_angle_deg=0.0,
        threshold_mode="binary",
        foreground_polarity="dark_on_light",
        min_target_area_px=80,
        sensitivity=0.0,
    )

    result = detect_directional_contour(image, config)

    assert result.metric_raw >= 120.0
    assert result.quality >= 0.75


def test_directional_contour_without_cv2_handles_large_roi(monkeypatch) -> None:
    monkeypatch.setattr(contour_direction, "_try_import_cv2", lambda: None)
    image = np.full((480, 640), 245, dtype=np.uint8)
    image[130:410, 80:560] = 35
    image[190:260, 220:420] = 180
    config = DirectionalContourConfig(
        analysis_roi=RectRegion(x=20, y=80, width=580, height=360),
        direction_angle_deg=0.0,
        threshold_mode="binary",
        foreground_polarity="dark_on_light",
        min_target_area_px=500,
        ignore_internal_texture=True,
    )

    result = detect_directional_contour(image, config)

    assert result.point_a.x == 80
    assert result.point_b.x == 559
    assert result.metric_raw == 479.0
    assert result.component_area > 120_000


def test_directional_contour_keeps_projected_ab_inside_roi() -> None:
    image = np.full((40, 60), 240, dtype=np.uint8)
    for y in range(18, 34):
        start_x = max(0, int((34 - y) * 1.8))
        image[y, start_x : min(start_x + 36, 52)] = 30
    roi = RectRegion(x=0, y=15, width=48, height=22)
    config = DirectionalContourConfig(
        analysis_roi=roi,
        direction_angle_deg=-18.0,
        threshold_mode="binary",
        foreground_polarity="dark_on_light",
        min_target_area_px=20,
    )

    result = detect_directional_contour(image, config)

    assert roi.x <= result.point_a.x < roi.x + roi.width
    assert roi.y <= result.point_a.y < roi.y + roi.height
    assert roi.x <= result.point_b.x < roi.x + roi.width
    assert roi.y <= result.point_b.y < roi.y + roi.height


def test_directional_contour_metric_reports_machine_readable_failure_reason() -> None:
    image = np.full((8, 12), 240, dtype=np.uint8)
    extractor = DirectionalContourMetricExtractor(
        DirectionalContourConfig(
            analysis_roi=RectRegion(x=20, y=20, width=4, height=4),
            direction_angle_deg=0.0,
            threshold_mode="binary",
        )
    )

    metric = extractor.extract(FramePacket(timestamp_ms=123, source="fixture", image=image))

    assert metric.metric_raw is None
    assert metric.quality == 0.0
    assert metric.meta["reason"] == "roi_outside_image"
    assert metric.meta["direction_angle_deg"] == 0.0


def test_directional_contour_metric_wraps_success_as_shape_metric() -> None:
    image = np.full((12, 20), 240, dtype=np.uint8)
    image[4:7, 3:12] = 30
    extractor = DirectionalContourMetricExtractor(
        DirectionalContourConfig(
            analysis_roi=RectRegion(x=0, y=0, width=20, height=12),
            direction_angle_deg=0.0,
            threshold_mode="binary",
            min_target_area_px=6,
        )
    )

    metric = extractor.extract(FramePacket(timestamp_ms=123, source="fixture", image=image))

    assert metric.metric_name == "directional_contour_span"
    assert metric.metric_raw == 8.0
    assert metric.point_a_px == (3, 5)
    assert metric.point_b_px == (11, 5)
    assert "source_point_a_px" not in metric.meta
    assert "source_point_b_px" not in metric.meta
    assert "axis_point_a_px" not in metric.meta
    assert "axis_point_b_px" not in metric.meta
    assert metric.meta["projection_point_mode"] == "max_chord"
    assert metric.meta["selection_mode"] == "directional_contour_max_chord"


def _paint_test_line(
    image: np.ndarray,
    start: tuple[int, int],
    end: tuple[int, int],
    *,
    width: int,
    value: int,
) -> None:
    x0, y0 = start
    x1, y1 = end
    steps = max(abs(x1 - x0), abs(y1 - y0), 1)
    radius = max(0, int(width) // 2)
    for index in range(steps + 1):
        ratio = index / steps
        x = int(round(x0 + (x1 - x0) * ratio))
        y = int(round(y0 + (y1 - y0) * ratio))
        image[
            max(0, y - radius) : min(image.shape[0], y + radius + 1),
            max(0, x - radius) : min(image.shape[1], x + radius + 1),
        ] = value


def _point_in_rotated_metric_box_with_tolerance(box: MetricBox, point: PixelPoint, epsilon: float = 2.0) -> bool:
    angle_rad = math.radians(float(box.angle_deg))
    cos_theta = math.cos(angle_rad)
    sin_theta = math.sin(angle_rad)
    translated_x = float(point.x) - float(box.center_x)
    translated_y = float(point.y) - float(box.center_y)
    local_x = translated_x * cos_theta + translated_y * sin_theta
    local_y = -translated_x * sin_theta + translated_y * cos_theta
    return abs(local_x) <= float(box.width) / 2.0 + epsilon and abs(local_y) <= float(box.height) / 2.0 + epsilon


def _paint_test_line_local(
    image: np.ndarray,
    box: MetricBox,
    start_local_x: float,
    end_local_x: float,
    *,
    local_y: float = 0.0,
    width: int,
    value: int,
) -> None:
    angle_rad = math.radians(float(box.angle_deg))
    cos_theta = math.cos(angle_rad)
    sin_theta = math.sin(angle_rad)
    steps = max(2, int(abs(float(end_local_x) - float(start_local_x)) * 2))
    radius = max(0, int(width) // 2)
    for index in range(steps + 1):
        ratio = index / steps
        local_x = float(start_local_x) + (float(end_local_x) - float(start_local_x)) * ratio
        x = int(round(float(box.center_x) + local_x * cos_theta - float(local_y) * sin_theta))
        y = int(round(float(box.center_y) + local_x * sin_theta + float(local_y) * cos_theta))
        image[
            max(0, y - radius) : min(image.shape[0], y + radius + 1),
            max(0, x - radius) : min(image.shape[1], x + radius + 1),
        ] = value
