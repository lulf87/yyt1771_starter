"""Placeholder end-displacement metric extractor."""

from src.core.contracts import VisionMetricExtractor
from src.core.models import FramePacket, ShapeMetric


class EndDisplacementMetricExtractor(VisionMetricExtractor):
    def extract(self, frame: FramePacket) -> ShapeMetric:
        if frame.image is None:
            return ShapeMetric(
                timestamp_ms=frame.timestamp_ms,
                quality=0.0,
                meta={"reason": "missing_image", "source": frame.source},
            )

        return ShapeMetric(
            timestamp_ms=frame.timestamp_ms,
            metric_name="end_displacement",
            metric_raw=None,
            metric_norm=None,
            quality=0.1,
            meta={"source": frame.source, "frame_id": frame.frame_id},
        )
