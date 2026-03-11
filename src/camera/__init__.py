"""Camera adapters."""

from src.camera.hik_rtsp_opencv import HikRtspCamera, build_hik_rtsp_url
from src.camera.mock_camera import MockCamera

__all__ = ["HikRtspCamera", "MockCamera", "build_hik_rtsp_url"]
