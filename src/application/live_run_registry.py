"""Shared in-memory registry for live-run drafts."""

from __future__ import annotations

from dataclasses import replace
import time
import uuid

from src.core.enums import CaptureMode, RunStatus
from src.core.models import MeasurementDefinition, RunDraftRecord


class LiveRunDraftRegistry:
    """Thin in-memory registry for live-run drafts."""

    def __init__(self) -> None:
        self._records: dict[str, RunDraftRecord] = {}

    def create(self, *, profile: str, preset: str) -> RunDraftRecord:
        now_ms = _now_ms()
        run_id = f"run-{uuid.uuid4().hex[:12]}"
        record = RunDraftRecord(
            run_id=run_id,
            profile=profile,
            preset=preset,
            status=RunStatus.CREATED,
            capture_mode=CaptureMode.IDLE,
            created_at_ms=now_ms,
            updated_at_ms=now_ms,
        )
        self._records[run_id] = record
        return record

    def get(self, run_id: str) -> RunDraftRecord | None:
        return self._records.get(run_id)

    def save_definition(self, run_id: str, definition: MeasurementDefinition) -> RunDraftRecord:
        record = self.get(run_id)
        if record is None:
            raise LookupError(f"Run not found: {run_id}")

        updated_record = replace(
            record,
            definition=definition,
            status=RunStatus.RUN_READY if definition.is_complete() else RunStatus.DEFINITION_EDITING,
            updated_at_ms=_now_ms(),
        )
        self._records[run_id] = updated_record
        return updated_record

    def mark_preview_streaming(self, run_id: str) -> RunDraftRecord:
        record = self.get(run_id)
        if record is None:
            raise LookupError(f"Run not found: {run_id}")

        next_status = record.status
        if record.status in {RunStatus.CREATED, RunStatus.DEVICE_READY}:
            next_status = RunStatus.PREVIEW_READY
        updated_record = replace(
            record,
            status=next_status,
            capture_mode=CaptureMode.SETUP_PREVIEW,
            updated_at_ms=_now_ms(),
        )
        self._records[run_id] = updated_record
        return updated_record

    def mark_preview_frozen(self, run_id: str) -> RunDraftRecord:
        record = self.get(run_id)
        if record is None:
            raise LookupError(f"Run not found: {run_id}")

        next_status = RunStatus.RUN_READY if record.definition and record.definition.is_complete() else RunStatus.DEFINITION_EDITING
        updated_record = replace(
            record,
            status=next_status,
            capture_mode=CaptureMode.SETUP_PREVIEW,
            updated_at_ms=_now_ms(),
        )
        self._records[run_id] = updated_record
        return updated_record

    def update_status(
        self,
        run_id: str,
        status: RunStatus,
        *,
        capture_mode: CaptureMode | None = None,
    ) -> RunDraftRecord:
        record = self.get(run_id)
        if record is None:
            raise LookupError(f"Run not found: {run_id}")

        updated_record = replace(
            record,
            status=status,
            capture_mode=record.capture_mode if capture_mode is None else capture_mode,
            updated_at_ms=_now_ms(),
        )
        self._records[run_id] = updated_record
        return updated_record


def _now_ms() -> int:
    return int(time.time() * 1000)
