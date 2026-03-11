"""Hikvision RTSP adapter placeholder."""

from src.core.contracts import CameraPort
from src.core.errors import AdapterNotConfiguredError
from src.core.models import FramePacket


class HikRtspCamera(CameraPort):
    def __init__(self, rtsp_url: str) -> None:
        self.rtsp_url = rtsp_url

    def read_frame(self) -> FramePacket:
        raise AdapterNotConfiguredError("Real RTSP camera access is deferred after scaffold freeze.")
