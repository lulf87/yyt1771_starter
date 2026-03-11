"""Session container for workflow orchestration."""

from dataclasses import dataclass

from src.core.models import SessionRecord


@dataclass(slots=True)
class WorkflowSession:
    record: SessionRecord
