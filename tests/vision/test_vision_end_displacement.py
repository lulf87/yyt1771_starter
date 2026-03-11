from src.core.models import FramePacket
from src.vision.metric_end_displacement import EndDisplacementMetricExtractor


def _blank(width: int = 12, height: int = 8) -> list[list[int]]:
    return [[0 for _ in range(width)] for _ in range(height)]


def _draw_rect(
    image: list[list[int]],
    x: int,
    y: int,
    width: int,
    height: int,
    value: int = 255,
) -> list[list[int]]:
    for row in range(y, y + height):
        for col in range(x, x + width):
            image[row][col] = value
    return image


def test_metric_raw_increases_when_target_moves_right() -> None:
    extractor = EndDisplacementMetricExtractor()
    frame_a = FramePacket(timestamp_ms=1, source="fixture", image=_draw_rect(_blank(), x=2, y=2, width=3, height=3))
    frame_b = FramePacket(timestamp_ms=2, source="fixture", image=_draw_rect(_blank(), x=4, y=2, width=3, height=3))
    frame_c = FramePacket(timestamp_ms=3, source="fixture", image=_draw_rect(_blank(), x=6, y=2, width=3, height=3))

    metric_a = extractor.extract(frame_a)
    metric_b = extractor.extract(frame_b)
    metric_c = extractor.extract(frame_c)

    assert metric_a.metric_raw == 0.0
    assert metric_b.metric_raw is not None and metric_b.metric_raw > metric_a.metric_raw
    assert metric_c.metric_raw is not None and metric_c.metric_raw > metric_b.metric_raw


def test_roi_ignores_noise_outside_region() -> None:
    extractor = EndDisplacementMetricExtractor(roi=(0, 0, 8, 8))
    clean = _draw_rect(_blank(width=12), x=2, y=2, width=3, height=3)
    noisy = [row[:] for row in clean]
    noisy = _draw_rect(noisy, x=10, y=0, width=2, height=2)

    clean_metric = extractor.extract(FramePacket(timestamp_ms=1, source="fixture", image=clean))
    noisy_metric = extractor.extract(FramePacket(timestamp_ms=2, source="fixture", image=noisy))

    assert clean_metric.feature_point_px == noisy_metric.feature_point_px
    assert clean_metric.baseline_px == noisy_metric.baseline_px
    assert noisy_metric.metric_raw == 0.0


def test_returns_low_quality_when_no_valid_foreground() -> None:
    extractor = EndDisplacementMetricExtractor(min_area_px=4)
    image = _draw_rect(_blank(), x=1, y=1, width=1, height=1)

    metric = extractor.extract(FramePacket(timestamp_ms=1, source="fixture", image=image))

    assert metric.metric_raw is None
    assert metric.quality <= 0.2
    assert metric.meta["reason"] == "no_valid_component"


def test_auto_locks_baseline_and_reports_global_feature_point() -> None:
    extractor = EndDisplacementMetricExtractor(roi=(2, 1, 8, 6))
    first = _draw_rect(_blank(width=14, height=10), x=4, y=3, width=3, height=3)
    second = _draw_rect(_blank(width=14, height=10), x=7, y=3, width=3, height=3)

    first_metric = extractor.extract(FramePacket(timestamp_ms=1, source="fixture", image=first))
    second_metric = extractor.extract(FramePacket(timestamp_ms=2, source="fixture", image=second))

    assert first_metric.feature_point_px == (6, 4)
    assert first_metric.baseline_px == 6.0
    assert first_metric.metric_raw == 0.0
    assert second_metric.feature_point_px == (9, 4)
    assert second_metric.baseline_px == 6.0
    assert second_metric.metric_raw == 3.0
    assert second_metric.quality >= 0.7
