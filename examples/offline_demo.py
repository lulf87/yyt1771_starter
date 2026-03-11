"""Readable offline demo that exercises only scaffold-safe placeholder code."""

from src.camera.mock_camera import MockCamera
from src.plc.mock_plc import MockPlc
from src.sync.hub import SyncHub
from src.temp.mock_temp import MockTempReader
from src.vision.metric_end_displacement import EndDisplacementMetricExtractor


def main() -> None:
    camera = MockCamera()
    temp_reader = MockTempReader()
    plc = MockPlc()
    extractor = EndDisplacementMetricExtractor()
    hub = SyncHub()

    frame = camera.read_frame()
    metric = extractor.extract(frame)
    hub.update_frame(frame)
    hub.update_temp(temp_reader.read())
    hub.update_plc(plc.read())
    hub.update_metric(metric)

    print(
        {
            "frame_has_image": frame.image is not None,
            "metric_name": metric.metric_name,
            "metric_raw": metric.metric_raw,
            "metric_norm": metric.metric_norm,
            "quality": metric.quality,
            "sync_point": hub.snapshot(),
        }
    )


if __name__ == "__main__":
    main()
