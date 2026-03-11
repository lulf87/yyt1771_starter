"""In-memory storage placeholder used by tests and demos."""

from src.core.models import SessionRecord


class InMemorySessionStore:
    def __init__(self) -> None:
        self._items: list[SessionRecord] = []

    def add(self, record: SessionRecord) -> None:
        self._items.append(record)

    def list_all(self) -> list[SessionRecord]:
        return list(self._items)
