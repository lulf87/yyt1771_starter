from src.core.models import FramePacket, MetricBox, PixelPoint, RectRegion
from src.vision.metric_two_point_distance import TwoPointDistanceMetricExtractor


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
