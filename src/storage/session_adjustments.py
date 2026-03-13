"""JSON-backed storage for manual adjustment drafts and version history."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class SessionAdjustmentStore:
    def __init__(self, artifact_dir: str | Path) -> None:
        self.artifact_dir = Path(artifact_dir) / "adjustments"
        self.artifact_dir.mkdir(parents=True, exist_ok=True)

    def get_adjustment(self, session_id: str) -> dict[str, Any]:
        path = self._path_for(session_id)
        if not path.exists():
            return {
                "session_id": session_id,
                "draft": None,
                "applied_versions": [],
            }
        return json.loads(path.read_text(encoding="utf-8"))

    def save_adjustment(self, session_id: str, payload: dict[str, Any]) -> Path:
        path = self._path_for(session_id)
        path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
        return path

    def _path_for(self, session_id: str) -> Path:
        return self.artifact_dir / f"{session_id}.json"
