"""Shared in-memory registry for live-run drafts."""

from __future__ import annotations

from dataclasses import replace
import time
import uuid

from src.core.enums import CaptureMode, RunStatus
from src.core.models import MeasurementDefinition, RunDraftRecord, TemperatureSettingsBundle


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
            status=_ready_status(definition=definition, temperature_settings=record.temperature_settings),
            updated_at_ms=_now_ms(),
        )
        self._records[run_id] = updated_record
        return updated_record

    def save_temperature_settings(self, run_id: str, settings: TemperatureSettingsBundle) -> RunDraftRecord:
        record = self.get(run_id)
        if record is None:
            raise LookupError(f"Run not found: {run_id}")

        updated_record = replace(
            record,
            temperature_settings=settings,
            status=_ready_status(definition=record.definition, temperature_settings=settings),
            updated_at_ms=_now_ms(),
        )
        self._records[run_id] = updated_record
        return updated_record

    def mark_temperature_power_zero_after_stop(self, run_id: str) -> RunDraftRecord:
        record = self.get(run_id)
        if record is None:
            raise LookupError(f"Run not found: {run_id}")
        if record.temperature_settings is None:
            return record

        now_ms = _now_ms()
        updated_settings = replace(
            record.temperature_settings,
            output_power_percent=0.0,
            confirmed_output_power_percent=0.0,
            confirmed_at_ms=now_ms,
            source="live_run_stop",
        )
        updated_record = replace(
            record,
            temperature_settings=updated_settings,
            updated_at_ms=now_ms,
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

        next_status = _ready_status(definition=record.definition, temperature_settings=record.temperature_settings)
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


def _ready_status(
    *,
    definition: MeasurementDefinition | None,
    temperature_settings: TemperatureSettingsBundle | None,
) -> RunStatus:
    if definition is not None and definition.is_complete() and temperature_settings is not None:
        return RunStatus.RUN_READY
    return RunStatus.DEFINITION_EDITING
