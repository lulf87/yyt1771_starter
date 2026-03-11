"""SQLite repository placeholder."""

from src.core.errors import PlaceholderNotImplementedError


class SqliteSessionRepo:
    def save(self, session_id: str) -> None:
        raise PlaceholderNotImplementedError("SQLite persistence is scheduled for a later task.")
