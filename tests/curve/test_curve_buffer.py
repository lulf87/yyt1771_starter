from src.core.models import CurvePoint
from src.curve.buffer import CurveBuffer


def test_curve_buffer_preserves_append_order() -> None:
    buffer = CurveBuffer()
    buffer.append(CurvePoint(timestamp_ms=1, value=10.0))
    buffer.append(CurvePoint(timestamp_ms=2, value=11.5))

    assert len(buffer) == 2
    assert buffer.values() == [10.0, 11.5]
