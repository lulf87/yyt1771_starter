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


class RunStatus(str, Enum):
    CREATED = "created"
    DEVICE_READY = "device_ready"
    PREVIEW_READY = "preview_ready"
    DEFINITION_EDITING = "definition_editing"
    RUN_READY = "run_ready"
    RUNNING = "running"
    STOPPING = "stopping"
    COMPLETED = "completed"
    FAILED = "failed"
    INVALIDATED = "invalidated"
    ABORTED = "aborted"


class CaptureMode(str, Enum):
    IDLE = "idle"
    SETUP_PREVIEW = "setup_preview"
    MEASUREMENT = "measurement"
    POST_RUN_REVIEW = "post_run_review"


class ObservationAxis(str, Enum):
    LONG_AXIS = "long_axis"
    SHORT_AXIS = "short_axis"
