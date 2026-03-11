from src.core.models import FramePacket, ShapeMetric
from src.vision.metric_end_displacement import EndDisplacementMetricExtractor


def test_frame_packet_supports_image_field() -> None:
    frame = FramePacket(
        timestamp_ms=1000,
        source="fixture",
        image=[[0, 255], [255, 0]],
        frame_id=5,
        meta={"kind": "test"},
    )

    assert frame.image == [[0, 255], [255, 0]]
    assert frame.frame_id == 5
    assert frame.meta["kind"] == "test"


def test_shape_metric_exposes_frozen_core_fields() -> None:
    metric = ShapeMetric(timestamp_ms=1000)

    assert metric.metric_name == "end_displacement"
    assert metric.metric_raw is None
    assert metric.metric_norm is None
    assert metric.quality == 0.0


def test_metric_extractor_handles_missing_image() -> None:
    extractor = EndDisplacementMetricExtractor()

    metric = extractor.extract(FramePacket(timestamp_ms=1000, source="fixture", image=None))

    assert metric.timestamp_ms == 1000
    assert metric.metric_name == "end_displacement"
    assert metric.quality == 0.0
    assert metric.meta["reason"] == "missing_image"
