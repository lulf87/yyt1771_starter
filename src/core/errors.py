"""Project-level exceptions used by placeholders."""


class ProjectError(Exception):
    """Base project exception."""


class AdapterNotConfiguredError(ProjectError):
    """Raised by hardware adapters that are present but not configured yet."""


class PlaceholderNotImplementedError(ProjectError, NotImplementedError):
    """Raised by scaffold-only modules that intentionally stop short of real logic."""
