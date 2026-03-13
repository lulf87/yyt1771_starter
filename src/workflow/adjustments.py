"""Manual adjustment contract assembly and version tracking."""

from __future__ import annotations

import time
from typing import Any, Protocol

from src.storage.sqlite_repo import SessionSummary

RESULT_KEYS = ("af95", "as_value", "af_value", "af_tan")


class SessionSummaryReader(Protocol):
    def get_summary(self, session_id: str) -> SessionSummary | None:
        """Load one persisted session summary."""


class AdjustmentStorePort(Protocol):
    def get_adjustment(self, session_id: str) -> dict[str, Any]:
        """Load the persisted adjustment artifact, or a default shell."""

    def save_adjustment(self, session_id: str, payload: dict[str, Any]) -> object:
        """Persist one adjustment artifact."""


class AdjustmentService:
    def __init__(self, repo: SessionSummaryReader, store: AdjustmentStorePort) -> None:
        self.repo = repo
        self.store = store

    def get_adjustment_state(self, session_id: str) -> dict[str, Any]:
        summary = self._get_summary_or_raise(session_id)
        artifact = self.store.get_adjustment(session_id)
        auto_result = _result_from_summary(summary)
        applied_versions = list(artifact.get("applied_versions") or [])
        latest_result = applied_versions[-1]["result_after"] if applied_versions else auto_result
        return {
            "session_id": session_id,
            "auto_result": auto_result,
            "latest_result": latest_result,
            "draft": artifact.get("draft"),
            "applied_versions": applied_versions,
        }

    def save_draft(self, session_id: str, overrides: dict[str, float | None], reason: str) -> dict[str, Any]:
        self._get_summary_or_raise(session_id)
        cleaned_overrides = _validate_overrides(overrides)
        artifact = self.store.get_adjustment(session_id)
        artifact["session_id"] = session_id
        artifact["draft"] = {
            "overrides": cleaned_overrides,
            "reason": reason.strip(),
            "updated_at_ms": int(time.time() * 1000),
        }
        artifact["applied_versions"] = list(artifact.get("applied_versions") or [])
        self.store.save_adjustment(session_id, artifact)
        return self.get_adjustment_state(session_id)

    def apply_draft(self, session_id: str) -> dict[str, Any]:
        current_state = self.get_adjustment_state(session_id)
        artifact = self.store.get_adjustment(session_id)
        draft = artifact.get("draft")
        if draft is None:
            raise RuntimeError(f"No adjustment draft available for session: {session_id}")

        applied_versions = list(artifact.get("applied_versions") or [])
        version = (applied_versions[-1]["version"] + 1) if applied_versions else 1
        result_before = dict(current_state["latest_result"])
        result_after = _apply_overrides(result_before, draft["overrides"])
        applied_versions.append(
            {
                "version": version,
                "result_before": result_before,
                "overrides": dict(draft["overrides"]),
                "result_after": result_after,
                "reason": draft["reason"],
                "created_at_ms": int(time.time() * 1000),
            }
        )
        artifact["session_id"] = session_id
        artifact["draft"] = None
        artifact["applied_versions"] = applied_versions
        self.store.save_adjustment(session_id, artifact)
        return self.get_adjustment_state(session_id)

    def _get_summary_or_raise(self, session_id: str) -> SessionSummary:
        summary = self.repo.get_summary(session_id)
        if summary is None:
            raise LookupError(f"Session not found: {session_id}")
        return summary


def _result_from_summary(summary: SessionSummary) -> dict[str, float | None]:
    return {
        "af95": summary.af95,
        "as_value": None,
        "af_value": None,
        "af_tan": None,
    }


def _validate_overrides(overrides: dict[str, float | None]) -> dict[str, float | None]:
    invalid_keys = sorted(key for key in overrides if key not in RESULT_KEYS)
    if invalid_keys:
        raise ValueError(f"Unsupported adjustment keys: {', '.join(invalid_keys)}")
    return {key: overrides[key] for key in RESULT_KEYS if key in overrides}


def _apply_overrides(
    base_result: dict[str, float | None],
    overrides: dict[str, float | None],
) -> dict[str, float | None]:
    merged = dict(base_result)
    merged.update(overrides)
    return merged
