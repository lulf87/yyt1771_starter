import numpy as np

from src.application.preview_render import build_preview_bitmap, build_preview_rows, enhance_preview_bitmap


class _NativeDownsampleImage:
    def __init__(self) -> None:
        self.calls: list[tuple[int, int]] = []

    def downsample_rows(self, *, max_width: int, max_height: int) -> list[list[int]]:
        self.calls.append((max_width, max_height))
        return [[10, 20], [30, 40]]


class _NativeBitmapImage:
    def __init__(self) -> None:
        self.calls: list[tuple[int, int]] = []

    def downsample_bitmap_payload(self, *, max_width: int, max_height: int) -> tuple[int, int, bytes]:
        self.calls.append((max_width, max_height))
        return (2, 2, bytes([1, 2, 3, 4]))


class _NativeBitmapArrayImage:
    def __init__(self) -> None:
        self.calls: list[tuple[int, int]] = []

    def downsample_bitmap_payload(self, *, max_width: int, max_height: int):
        self.calls.append((max_width, max_height))
        return (2, 2, np.array([1, 2, 3, 4], dtype=np.uint8))


def test_build_preview_rows_prefers_native_downsample() -> None:
    image = _NativeDownsampleImage()

    rows = build_preview_rows(image, max_width=200, max_height=100)

    assert rows == [[10, 20], [30, 40]]
    assert image.calls == [(200, 100)]


def test_build_preview_bitmap_flattens_grayscale_rows() -> None:
    image = [[0, 127, 255], [255, 127, 0]]

    bitmap = build_preview_bitmap(image, max_width=10, max_height=10)

    assert bitmap.width == 3
    assert bitmap.height == 2
    assert bitmap.pixels == bytes([0, 127, 255, 255, 127, 0])


def test_build_preview_bitmap_accepts_numpy_grayscale_arrays() -> None:
    image = np.array([[0, 127, 255], [255, 127, 0]], dtype=np.uint8)

    bitmap = build_preview_bitmap(image, max_width=10, max_height=10)

    assert bitmap.width == 3
    assert bitmap.height == 2
    assert bitmap.pixels == bytes([0, 127, 255, 255, 127, 0])


def test_build_preview_bitmap_prefers_native_bitmap_payload() -> None:
    image = _NativeBitmapImage()

    bitmap = build_preview_bitmap(image, max_width=320, max_height=240)

    assert bitmap.width == 2
    assert bitmap.height == 2
    assert bitmap.pixels == bytes([1, 2, 3, 4])
    assert image.calls == [(320, 240)]


def test_build_preview_bitmap_coerces_numpy_native_bitmap_payload_to_bytes() -> None:
    image = _NativeBitmapArrayImage()

    bitmap = build_preview_bitmap(image, max_width=320, max_height=240)

    assert bitmap.width == 2
    assert bitmap.height == 2
    assert bitmap.pixels == bytes([1, 2, 3, 4])
    assert image.calls == [(320, 240)]


def test_enhance_preview_bitmap_brightens_low_contrast_bitmap() -> None:
    bitmap = enhance_preview_bitmap(
        build_preview_bitmap([[0, 1, 2, 3], [0, 1, 2, 3]], max_width=10, max_height=10)
    )

    assert bitmap.width == 4
    assert bitmap.height == 2
    assert min(bitmap.pixels) == 0
    assert max(bitmap.pixels) == 255
    assert sum(bitmap.pixels) > sum([0, 1, 2, 3, 0, 1, 2, 3])
    assert sum(bitmap.pixels) / len(bitmap.pixels) >= 40.0


def test_enhance_preview_bitmap_keeps_high_contrast_bitmap_unchanged() -> None:
    original = build_preview_bitmap([[0, 128, 255], [255, 128, 0]], max_width=10, max_height=10)

    enhanced = enhance_preview_bitmap(original)

    assert enhanced == original
