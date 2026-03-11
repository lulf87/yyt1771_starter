"""Enum definitions shared by multiple modules."""

from enum import Enum


class AcquisitionState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    STOPPED = "stopped"


class SessionState(str, Enum):
    CREATED = "created"
    PRECHECK = "precheck"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
