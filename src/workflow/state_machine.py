"""Minimal workflow state machine scaffold."""

from src.core.enums import SessionState
from src.core.models import SessionRecord


class WorkflowStateMachine:
    def __init__(self, record: SessionRecord) -> None:
        self.record = record

    def advance(self, next_state: SessionState) -> SessionRecord:
        self.record.state = next_state
        return self.record
