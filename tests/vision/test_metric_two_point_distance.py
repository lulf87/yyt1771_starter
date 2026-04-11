import math

import numpy as np

from src.core.models import FramePacket, MetricBox, PixelPoint, RectRegion
from src.vision.metric_two_point_distance import (
    RoiLongestSpanPointDetector,
    TwoPointDistanceMetricExtractor,
    normalize_frame_image,
)


def _blank(width: int = 16, height: int = 10, value: int = 240) -> list[list[int]]:
    return [[value for _ in range(width)] for _ in range(height)]


def _draw_rect(
    image: list[list[int]],
    x: int,
    y: int,
    width: int,
    height: int,
    value: int,
) -> list[list[int]]:
    for row in range(y, y + height):
        for col in range(x, x + width):
            image[row][col] = value
    return image


def _draw_polyline(
    image: list[list[int]],
    points: list[tuple[int, int]],
    *,
    value: int,
    thickness: int = 1,
) -> list[list[int]]:
    for x, y in points:
        for dy in range(-thickness + 1, thickness):
            for dx in range(-thickness + 1, thickness):
                xx = max(0, min(len(image[0]) - 1, x + dx))
                yy = max(0, min(len(image) - 1, y + dy))
                image[yy][xx] = value
    return image


def test_normalize_frame_image_supports_numpy_uint8_without_python_list_conversion() -> None:
    image = np.array(
        [
            [240, 120, 30],
            [250, 110, 20],
        ],
        dtype=np.uint8,
    )

    normalized = normalize_frame_image(image)

    assert isinstance(normalized, np.ndarray)
    assert normalized.dtype == np.uint8
    assert normalized.shape == (2, 3)
    assert normalized[0, 0] == 240


def test_normalize_frame_image_averages_numpy_color_channels_like_sequence_path() -> None:
    image = np.array(
        [
            [[255, 0, 0], [0, 255, 0]],
            [[0, 0, 255], [30, 60, 90]],
        ],
        dtype=np.uint8,
    )

    normalized = normalize_frame_image(image)

    assert isinstance(normalized, np.ndarray)
    assert normalized.shape == (2, 2)
    assert normalized[0, 0] == 85
    assert normalized[0, 1] == 85
    assert normalized[1, 0] == 85
    assert normalized[1, 1] == 60


def test_normalize_frame_image_preserves_mono8_image_view_without_materializing_lists() -> None:
    image = __import__("src.camera.hik_gige_mvs", fromlist=["_Mono8ImageView"])._Mono8ImageView(
        bytes([10, 20, 30, 40, 50, 60]),
        width=3,
        height=2,
    )

    normalized = normalize_frame_image(image)

    assert normalized is image


def test_roi_outside_image_returns_clear_failure_reason() -> None:
    extractor = TwoPointDistanceMetricExtractor(
        analysis_roi=RectRegion(x=20, y=20, width=10, height=10),
        metric_box=MetricBox(center_x=25, center_y=25, width=4, height=4),
    )

    metric = extractor.extract(FramePacket(timestamp_ms=1, source="fixture", image=_blank()))

    assert metric.metric_raw is None
    assert metric.meta["reason"] == "roi_outside_image"


def test_metric_box_outside_roi_returns_clear_failure_reason() -> None:
    extractor = TwoPointDistanceMetricExtractor(
        analysis_roi=RectRegion(x=0, y=0, width=12, height=8),
        metric_box=MetricBox(center_x=11, center_y=4, width=8, height=4),
    )

    metric = extractor.extract(FramePacket(timestamp_ms=1, source="fixture", image=_blank(width=12, height=8)))

    assert metric.metric_raw is None
    assert metric.meta["reason"] == "metric_box_outside_roi"


def test_dark_on_light_binary_path_detects_left_and_right_extremes() -> None:
    image = _draw_rect(_blank(width=14, height=8), x=2, y=2, width=8, height=3, value=24)
    extractor = TwoPointDistanceMetricExtractor(
        analysis_roi=RectRegion(x=0, y=0, width=14, height=8),
        metric_box=MetricBox(center_x=6, center_y=3, width=10, height=4),
        foreground_polarity="dark_on_light",
        threshold_mode="binary",
        threshold_margin=12,
        min_target_area_px=8,
    )

    metric = extractor.extract(FramePacket(timestamp_ms=1, source="fixture", image=image))

    assert metric.metric_raw is not None
    assert metric.point_a_px == (2, 3)
    assert metric.point_b_px == (9, 3)
    assert metric.meta["selection_mode"] == "auto_extremes"


def test_adaptive_threshold_path_detects_mid_contrast_target() -> None:
    image = _draw_rect(_blank(width=14, height=8, value=160), x=3, y=2, width=7, height=3, value=70)
    extractor = TwoPointDistanceMetricExtractor(
        analysis_roi=RectRegion(x=0, y=0, width=14, height=8),
        metric_box=MetricBox(center_x=6, center_y=3, width=10, height=4),
        foreground_polarity="dark_on_light",
        threshold_mode="adaptive",
        min_target_area_px=8,
    )

    metric = extractor.extract(FramePacket(timestamp_ms=1, source="fixture", image=image))

    assert metric.metric_raw is not None
    assert metric.point_a_px == (3, 3)
    assert metric.point_b_px == (9, 3)
    assert metric.quality >= 0.75


def test_roi_local_boundary_quality_accepts_reasonable_span_inside_metric_box() -> None:
    image = _draw_rect(_blank(width=24, height=16, value=220), x=6, y=5, width=12, height=4, value=40)
    extractor = TwoPointDistanceMetricExtractor(
        analysis_roi=RectRegion(x=0, y=0, width=24, height=16),
        metric_box=MetricBox(center_x=12, center_y=7, width=20, height=6, angle_deg=0.0),
        foreground_polarity="dark_on_light",
        threshold_mode="adaptive",
        ignore_internal_texture=True,
        min_target_area_px=8,
        quality_threshold=0.75,
        selection_strategy="roi_local_horizontal_boundary",
    )

    metric = extractor.extract(FramePacket(timestamp_ms=1, source="fixture", image=image))

    assert metric.metric_raw is not None
    assert metric.metric_raw >= 11.0
    assert metric.quality >= 0.75
    assert "reason" not in metric.meta


def test_extractor_accepts_numpy_grayscale_images_on_fast_path() -> None:
    image = np.full((8, 14), 240, dtype=np.uint8)
    image[2:5, 3:10] = 24
    extractor = TwoPointDistanceMetricExtractor(
        analysis_roi=RectRegion(x=0, y=0, width=14, height=8),
        metric_box=MetricBox(center_x=6, center_y=3, width=10, height=4),
        foreground_polarity="dark_on_light",
        threshold_mode="binary",
        threshold_margin=12,
        min_target_area_px=8,
    )

    metric = extractor.extract(FramePacket(timestamp_ms=1, source="fixture", image=image))

    assert metric.metric_raw is not None
    assert metric.point_a_px == (3, 3)
    assert metric.point_b_px == (9, 3)


def test_extractor_can_downsample_large_working_box_and_remap_points_to_source_space() -> None:
    image = np.full((600, 800), 220, dtype=np.uint8)
    image[250:310, 260:540] = 30
    extractor = TwoPointDistanceMetricExtractor(
        analysis_roi=RectRegion(x=0, y=0, width=800, height=600),
        metric_box=MetricBox(center_x=400, center_y=280, width=320, height=100, angle_deg=0.0),
        foreground_polarity="dark_on_light",
        threshold_mode="adaptive",
        ignore_internal_texture=True,
        min_target_area_px=100,
        selection_strategy="roi_local_horizontal_boundary",
        working_max_width=160,
        working_max_height=80,
    )

    metric = extractor.extract(FramePacket(timestamp_ms=1, source="fixture", image=image))

    assert metric.metric_raw is not None
    assert metric.point_a_px is not None
    assert metric.point_b_px is not None
    assert abs(metric.point_a_px[0] - 260) <= 3
    assert abs(metric.point_b_px[0] - 539) <= 3
    assert abs(metric.point_a_px[1] - 280) <= 3
    assert abs(metric.point_b_px[1] - 280) <= 3
    assert abs(metric.metric_raw - 279.0) <= 6.0
    assert metric.meta["working_scale_x"] > 1.0
    assert metric.meta["working_scale_y"] > 1.0


def test_measurement_axis_can_follow_short_axis_without_rotating_metric_box_geometry() -> None:
    image = _draw_rect(_blank(width=14, height=10, value=220), x=2, y=2, width=8, height=5, value=40)
    extractor = TwoPointDistanceMetricExtractor(
        analysis_roi=RectRegion(x=0, y=0, width=14, height=10),
        metric_box=MetricBox(center_x=6, center_y=4, width=10, height=6, angle_deg=0.0),
        measurement_axis_deg=90.0,
        foreground_polarity="dark_on_light",
        threshold_mode="binary",
        threshold_margin=12,
        min_target_area_px=8,
    )

    metric = extractor.extract(FramePacket(timestamp_ms=1, source="fixture", image=image))

    assert metric.metric_raw is not None
    assert metric.point_a_px == (5, 2)
    assert metric.point_b_px == (5, 6)
    assert metric.meta["measurement_axis_deg"] == 90.0


def test_ignore_internal_texture_fills_split_target_before_extreme_detection() -> None:
    image = _draw_rect(_blank(width=16, height=8), x=2, y=2, width=10, height=3, value=28)
    for row in range(2, 5):
        image[row][6] = 240
        image[row][7] = 240

    plain_extractor = TwoPointDistanceMetricExtractor(
        analysis_roi=RectRegion(x=0, y=0, width=16, height=8),
        metric_box=MetricBox(center_x=7, center_y=3, width=12, height=4),
        foreground_polarity="dark_on_light",
        threshold_mode="binary",
        threshold_margin=10,
        ignore_internal_texture=False,
        min_target_area_px=6,
    )
    ignore_texture_extractor = TwoPointDistanceMetricExtractor(
        analysis_roi=RectRegion(x=0, y=0, width=16, height=8),
        metric_box=MetricBox(center_x=7, center_y=3, width=12, height=4),
        foreground_polarity="dark_on_light",
        threshold_mode="binary",
        threshold_margin=10,
        ignore_internal_texture=True,
        min_target_area_px=6,
    )

    plain_metric = plain_extractor.extract(FramePacket(timestamp_ms=1, source="fixture", image=image))
    ignore_texture_metric = ignore_texture_extractor.extract(FramePacket(timestamp_ms=2, source="fixture", image=image))

    assert plain_metric.metric_raw is not None
    assert ignore_texture_metric.metric_raw is not None
    assert ignore_texture_metric.metric_raw > plain_metric.metric_raw
    assert ignore_texture_metric.point_a_px == (2, 3)
    assert ignore_texture_metric.point_b_px == (11, 3)


def test_manual_points_locked_path_bypasses_auto_detection() -> None:
    extractor = TwoPointDistanceMetricExtractor(
        analysis_roi=RectRegion(x=0, y=0, width=20, height=20),
        metric_box=MetricBox(center_x=10, center_y=10, width=18, height=8),
        locked_points=(PixelPoint(x=4, y=10), PixelPoint(x=9, y=10)),
    )

    metric = extractor.extract(FramePacket(timestamp_ms=1, source="fixture", image=_blank(width=20, height=20)))

    assert metric.metric_raw == 5.0
    assert metric.point_a_px == (4, 10)
    assert metric.point_b_px == (9, 10)
    assert metric.meta["selection_mode"] == "locked_points"


def test_quality_below_threshold_keeps_metric_but_marks_reason() -> None:
    image = _blank(width=30, height=20)
    image[10][14] = 20
    image[10][15] = 20
    extractor = TwoPointDistanceMetricExtractor(
        analysis_roi=RectRegion(x=0, y=0, width=30, height=20),
        metric_box=MetricBox(center_x=15, center_y=10, width=20, height=6),
        foreground_polarity="dark_on_light",
        threshold_mode="binary",
        threshold_margin=8,
        min_target_area_px=1,
        quality_threshold=0.95,
    )

    metric = extractor.extract(FramePacket(timestamp_ms=1, source="fixture", image=image))

    assert metric.metric_raw == 1.0
    assert metric.quality < 0.95
    assert metric.meta["reason"] == "quality_below_threshold"


def test_roi_longest_span_detector_prefers_interior_component_over_border_touching_background() -> None:
    image = _blank(width=20, height=12, value=240)
    image = _draw_rect(image, x=0, y=0, width=20, height=2, value=32)
    image = _draw_rect(image, x=5, y=4, width=9, height=2, value=32)
    detector = RoiLongestSpanPointDetector(
        analysis_roi=RectRegion(x=0, y=0, width=20, height=12),
        foreground_polarity="dark_on_light",
        threshold_mode="binary",
        threshold_margin=20,
        min_target_area_px=6,
    )

    metric = detector.extract(FramePacket(timestamp_ms=1, source="fixture", image=image))

    assert metric.metric_raw is not None
    assert metric.point_a_px == (5, 5)
    assert metric.point_b_px == (13, 5)
    assert metric.meta["component_border_touch_count"] == 0
    assert metric.meta["selection_axis"] == "horizontal"


def test_roi_longest_span_detector_prefers_long_target_over_tiny_interior_noise_even_when_target_touches_roi_border() -> None:
    image = _blank(width=24, height=14, value=240)
    image = _draw_rect(image, x=0, y=6, width=24, height=2, value=32)
    image = _draw_rect(image, x=9, y=1, width=4, height=4, value=32)
    detector = RoiLongestSpanPointDetector(
        analysis_roi=RectRegion(x=0, y=0, width=24, height=14),
        foreground_polarity="dark_on_light",
        threshold_mode="binary",
        threshold_margin=20,
        min_target_area_px=6,
    )

    metric = detector.extract(FramePacket(timestamp_ms=1, source="fixture", image=image))

    assert metric.metric_raw is not None
    assert metric.point_a_px == (0, 7)
    assert metric.point_b_px == (23, 7)
    assert metric.meta["component_border_touch_count"] == 2
    assert metric.quality >= 0.75
    assert metric.meta["selection_axis"] == "horizontal"


def test_roi_longest_span_detector_finds_curve_endpoints_for_guidewire_like_shape() -> None:
    image = _blank(width=32, height=20, value=240)
    guidewire_points = [
        (3, 13),
        (4, 12),
        (5, 12),
        (6, 11),
        (7, 10),
        (8, 10),
        (9, 9),
        (10, 8),
        (11, 8),
        (12, 7),
        (13, 7),
        (14, 7),
        (15, 8),
        (16, 8),
        (17, 9),
        (18, 9),
        (19, 10),
        (20, 10),
        (21, 11),
        (22, 12),
        (23, 12),
        (24, 13),
        (25, 13),
        (26, 14),
        (27, 14),
    ]
    image = _draw_polyline(image, guidewire_points, value=24, thickness=1)
    detector = RoiLongestSpanPointDetector(
        analysis_roi=RectRegion(x=1, y=5, width=29, height=12),
        foreground_polarity="dark_on_light",
        threshold_mode="binary",
        threshold_margin=20,
        min_target_area_px=8,
    )

    metric = detector.extract(FramePacket(timestamp_ms=1, source="fixture", image=image))

    assert metric.metric_raw is not None
    assert metric.point_a_px == (3, 10)
    assert metric.point_b_px == (27, 10)
    assert metric.quality >= 0.75
    assert metric.meta["selection_axis"] == "horizontal"


def test_roi_longest_span_detector_finds_longest_points_for_balloon_like_shape_with_light_foreground() -> None:
    image = _blank(width=30, height=18, value=24)
    image = _draw_rect(image, x=6, y=4, width=18, height=10, value=236)
    detector = RoiLongestSpanPointDetector(
        analysis_roi=RectRegion(x=4, y=2, width=22, height=14),
        foreground_polarity="light_on_dark",
        threshold_mode="binary",
        threshold_margin=20,
        min_target_area_px=12,
    )

    metric = detector.extract(FramePacket(timestamp_ms=1, source="fixture", image=image))

    assert metric.metric_raw is not None
    assert metric.point_a_px == (6, 9)
    assert metric.point_b_px == (23, 9)
    assert metric.quality >= 0.75
    assert metric.meta["selection_axis"] == "horizontal"


def test_roi_longest_span_detector_uses_vertical_pair_for_tall_target() -> None:
    image = _blank(width=18, height=24, value=240)
    image = _draw_rect(image, x=7, y=3, width=4, height=16, value=24)
    detector = RoiLongestSpanPointDetector(
        analysis_roi=RectRegion(x=5, y=1, width=8, height=20),
        foreground_polarity="dark_on_light",
        threshold_mode="binary",
        threshold_margin=20,
        min_target_area_px=8,
    )

    metric = detector.extract(FramePacket(timestamp_ms=1, source="fixture", image=image))

    assert metric.metric_raw is not None
    assert metric.point_a_px == (9, 3)
    assert metric.point_b_px == (9, 18)
    assert metric.meta["selection_axis"] == "vertical"


def test_roi_longest_span_detector_returns_strictly_horizontal_pair_for_rotated_blob() -> None:
    image = _blank(width=24, height=20, value=240)
    rotated_blob = [
        (6, 11), (7, 10), (8, 9), (9, 8), (10, 7), (11, 6),
        (7, 12), (8, 11), (9, 10), (10, 9), (11, 8), (12, 7),
        (8, 13), (9, 12), (10, 11), (11, 10), (12, 9), (13, 8),
        (9, 14), (10, 13), (11, 12), (12, 11), (13, 10), (14, 9),
        (10, 15), (11, 14), (12, 13), (13, 12), (14, 11), (15, 10),
        (11, 16), (12, 15), (13, 14), (14, 13), (15, 12), (16, 11),
    ]
    image = _draw_polyline(image, rotated_blob, value=24, thickness=1)
    detector = RoiLongestSpanPointDetector(
        analysis_roi=RectRegion(x=4, y=5, width=14, height=13),
        foreground_polarity="dark_on_light",
        threshold_mode="binary",
        threshold_margin=20,
        min_target_area_px=8,
    )

    metric = detector.extract(FramePacket(timestamp_ms=1, source="fixture", image=image))

    assert metric.metric_raw is not None
    assert metric.point_a_px == (6, 11)
    assert metric.point_b_px == (16, 11)
    assert metric.point_a_px[1] == metric.point_b_px[1]
    assert metric.meta["selection_axis"] == "horizontal"


def test_roi_local_horizontal_boundary_strategy_uses_rotated_roi_local_axis() -> None:
    image = _blank(width=48, height=48, value=240)
    roi_box = MetricBox(center_x=24, center_y=24, width=26, height=10, angle_deg=32.0)
    angle_rad = math.radians(roi_box.angle_deg)

    for local_x in range(-11, 12):
        for local_y in range(-2, 3):
            world_x = int(round(roi_box.center_x + local_x * math.cos(angle_rad) - local_y * math.sin(angle_rad)))
            world_y = int(round(roi_box.center_y + local_x * math.sin(angle_rad) + local_y * math.cos(angle_rad)))
            if 0 <= world_x < 48 and 0 <= world_y < 48:
                image[world_y][world_x] = 24

    detector = RoiLongestSpanPointDetector(
        analysis_roi=RectRegion(x=8, y=8, width=32, height=32),
        roi_box=roi_box,
        foreground_polarity="dark_on_light",
        threshold_mode="binary",
        threshold_margin=20,
        min_target_area_px=12,
        selection_strategy="roi_local_horizontal_boundary",
    )

    metric = detector.extract(FramePacket(timestamp_ms=1, source="fixture", image=image))

    assert metric.metric_raw is not None
    assert metric.meta["selection_mode"] == "roi_local_horizontal_boundary"
    assert metric.meta["selection_axis"] == "roi_local_horizontal"

    point_a = PixelPoint(*metric.point_a_px)
    point_b = PixelPoint(*metric.point_b_px)
    point_a_local_x = (point_a.x - roi_box.center_x) * math.cos(angle_rad) + (point_a.y - roi_box.center_y) * math.sin(angle_rad)
    point_b_local_x = (point_b.x - roi_box.center_x) * math.cos(angle_rad) + (point_b.y - roi_box.center_y) * math.sin(angle_rad)
    point_a_local_y = -(point_a.x - roi_box.center_x) * math.sin(angle_rad) + (point_a.y - roi_box.center_y) * math.cos(angle_rad)
    point_b_local_y = -(point_b.x - roi_box.center_x) * math.sin(angle_rad) + (point_b.y - roi_box.center_y) * math.cos(angle_rad)

    assert point_a_local_x < -8.0
    assert point_b_local_x > 8.0
    assert abs(point_a_local_y) <= 2.5
    assert abs(point_b_local_y) <= 2.5


def test_roi_local_horizontal_boundary_accepts_tight_rotated_roi_bounds() -> None:
    image = _blank(width=72, height=72, value=240)
    roi_box = MetricBox(center_x=36, center_y=36, width=18, height=40, angle_deg=82.0)
    angle_rad = math.radians(roi_box.angle_deg)

    for local_x in range(-4, 5):
        for local_y in range(-17, 18):
            world_x = int(round(roi_box.center_x + local_x * math.cos(angle_rad) - local_y * math.sin(angle_rad)))
            world_y = int(round(roi_box.center_y + local_x * math.sin(angle_rad) + local_y * math.cos(angle_rad)))
            if 0 <= world_x < 72 and 0 <= world_y < 72:
                image[world_y][world_x] = 24

    corners = []
    half_width = roi_box.width / 2
    half_height = roi_box.height / 2
    for local_x, local_y in (
        (-half_width, -half_height),
        (half_width, -half_height),
        (half_width, half_height),
        (-half_width, half_height),
    ):
        corners.append(
            (
                roi_box.center_x + local_x * math.cos(angle_rad) - local_y * math.sin(angle_rad),
                roi_box.center_y + local_x * math.sin(angle_rad) + local_y * math.cos(angle_rad),
            )
        )
    roi = RectRegion(
        x=math.floor(min(x for x, _ in corners)),
        y=math.floor(min(y for _, y in corners)),
        width=max(1, math.ceil(max(x for x, _ in corners)) - math.floor(min(x for x, _ in corners))),
        height=max(1, math.ceil(max(y for _, y in corners)) - math.floor(min(y for _, y in corners))),
    )

    detector = RoiLongestSpanPointDetector(
        analysis_roi=roi,
        roi_box=roi_box,
        foreground_polarity="dark_on_light",
        threshold_mode="binary",
        threshold_margin=20,
        min_target_area_px=20,
        selection_strategy="roi_local_horizontal_boundary",
    )

    metric = detector.extract(FramePacket(timestamp_ms=1, source="fixture", image=image))

    assert metric.metric_raw is not None
    assert metric.meta["selection_mode"] == "roi_local_horizontal_boundary"
    assert metric.meta.get("reason") != "roi_box_outside_roi"


def test_roi_local_horizontal_boundary_ignores_detached_far_side_noise() -> None:
    image = _blank(width=56, height=40, value=240)
    roi_box = MetricBox(center_x=28, center_y=20, width=34, height=10, angle_deg=0.0)

    for x in range(14, 39):
        for y in range(18, 23):
            image[y][x] = 24

    image[20][47] = 24
    image[20][48] = 24

    extractor = TwoPointDistanceMetricExtractor(
        analysis_roi=RectRegion(x=10, y=14, width=42, height=12),
        metric_box=roi_box,
        foreground_polarity="dark_on_light",
        threshold_mode="binary",
        threshold_margin=20,
        min_target_area_px=8,
        selection_strategy="roi_local_horizontal_boundary",
    )

    metric = extractor.extract(FramePacket(timestamp_ms=1, source="fixture", image=image))

    assert metric.metric_raw is not None
    assert metric.meta["selection_mode"] == "roi_local_horizontal_boundary"
    assert metric.point_a_px == (14, 20)
    assert metric.point_b_px == (38, 20)


def test_live_roi_local_horizontal_boundary_matches_setup_detector_on_same_frame() -> None:
    image = _blank(width=64, height=48, value=240)
    roi_box = MetricBox(center_x=32, center_y=24, width=30, height=12, angle_deg=0.0)
    analysis_roi = RectRegion(x=14, y=16, width=36, height=16)

    for x in range(18, 43):
        for y in range(20, 25):
            image[y][x] = 24

    frame = FramePacket(timestamp_ms=1, source="fixture", image=image)

    setup_detector = RoiLongestSpanPointDetector(
        analysis_roi=analysis_roi,
        roi_box=roi_box,
        foreground_polarity="dark_on_light",
        threshold_mode="adaptive",
        threshold_margin=10,
        ignore_internal_texture=True,
        min_target_area_px=8,
        sensitivity=50,
        selection_strategy="roi_local_horizontal_boundary",
    )
    live_extractor = TwoPointDistanceMetricExtractor(
        analysis_roi=analysis_roi,
        metric_box=roi_box,
        foreground_polarity="dark_on_light",
        threshold_mode="adaptive",
        threshold_margin=10,
        ignore_internal_texture=True,
        min_target_area_px=8,
        sensitivity=50,
        selection_strategy="roi_local_horizontal_boundary",
    )

    setup_metric = setup_detector.extract(frame)
    live_metric = live_extractor.extract(frame)

    assert setup_metric.point_a_px == live_metric.point_a_px
    assert setup_metric.point_b_px == live_metric.point_b_px
    assert setup_metric.metric_raw == live_metric.metric_raw
