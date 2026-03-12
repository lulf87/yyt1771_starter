"""JSON-backed storage for lightweight session detail artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class SessionArtifactStore:
    def __init__(self, artifact_dir: str | Path) -> None:
        self.artifact_dir = Path(artifact_dir)
        self.artifact_dir.mkdir(parents=True, exist_ok=True)

    def save_detail(self, session_id: str, payload: dict[str, Any]) -> Path:
        path = self._path_for(session_id)
        path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
        return path

    def get_detail(self, session_id: str) -> dict[str, Any] | None:
        path = self._path_for(session_id)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def _path_for(self, session_id: str) -> Path:
        return self.artifact_dir / f"{session_id}.json"
