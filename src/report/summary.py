"""Result summary helpers."""

from src.core.models import SessionRecord


def build_summary(record: SessionRecord, point_count: int) -> dict[str, str | int]:
    return {
        "session_id": record.session_id,
        "state": record.state.value,
        "point_count": point_count,
    }
