"""ROI helpers reserved for later image-processing tasks."""


def full_frame_roi(width: int, height: int) -> tuple[int, int, int, int]:
    return (0, 0, width, height)
