from src.core.models import FramePacket
from src.vision.metric_end_displacement import EndDisplacementMetricExtractor


def test_metric_extractor_returns_placeholder_metric() -> None:
    extractor = EndDisplacementMetricExtractor()

    metric = extractor.extract(
        FramePacket(
            timestamp_ms=1234,
            source="fixture",
            image=[[0, 255], [0, 255]],
            frame_id=7,
        )
    )

    assert metric.timestamp_ms == 1234
    assert metric.metric_name == "end_displacement"
    assert metric.metric_raw is None
    assert metric.metric_norm is None
    assert metric.quality == 0.1
    assert metric.meta["frame_id"] == 7
