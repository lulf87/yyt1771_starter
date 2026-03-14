"""Lightweight JSONL storage for camera probe diagnostics."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ProbeDiagnosticStore:
    def __init__(self, root_dir: str | Path) -> None:
        self.root_dir = Path(root_dir) / "probe_diagnostics"
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self.file_path = self.root_dir / "camera_probe.jsonl"

    def append(self, payload: dict[str, Any]) -> Path:
        line = json.dumps(payload, ensure_ascii=True)
        with self.file_path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
        return self.file_path

    def read_all(self) -> list[dict[str, Any]]:
        if not self.file_path.exists():
            return []
        return [
            json.loads(line)
            for line in self.file_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
