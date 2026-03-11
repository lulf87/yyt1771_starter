from src.core.models import FramePacket, PlcSnapshot, TempReading
from src.sync.hub import SyncHub


def test_sync_hub_uses_latest_timestamp() -> None:
    hub = SyncHub()
    frame = FramePacket(timestamp_ms=1000, source="fixture")
    temp = TempReading(timestamp_ms=1002, celsius=25.0, source="fixture")
    plc = PlcSnapshot(timestamp_ms=1001, values={"ready": True}, source="fixture")

    hub.update_frame(frame)
    hub.update_temp(temp)
    hub.update_plc(plc)

    snapshot = hub.snapshot()

    assert snapshot.timestamp_ms == 1002
    assert snapshot.frame == frame
    assert snapshot.temp == temp
    assert snapshot.plc == plc
