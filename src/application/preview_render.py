"""Shared preview-image rendering helpers for delivery shells."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from PIL import Image

from src.vision.metric_two_point_distance import downsample_grayscale_image, normalize_frame_image


@dataclass(slots=True)
class PreviewBitmap:
    """UI-friendly grayscale bitmap derived from an arbitrary frame payload."""

    width: int
    height: int
    pixels: bytes


def build_preview_rows(
    image: Any,
    *,
    max_width: int = 640,
    max_height: int = 480,
) -> list[list[int]]:
    native_downsample = getattr(image, "downsample_rows", None)
    if callable(native_downsample):
        preview_rows = native_downsample(max_width=max_width, max_height=max_height)
        if preview_rows:
            return preview_rows
    return downsample_grayscale_image(
        normalize_frame_image(image),
        max_width=max_width,
        max_height=max_height,
    )


def build_preview_bitmap(
    image: Any,
    *,
    max_width: int = 640,
    max_height: int = 480,
) -> PreviewBitmap:
    native_bitmap_payload = getattr(image, "downsample_bitmap_payload", None)
    if callable(native_bitmap_payload):
        width, height, pixels = native_bitmap_payload(max_width=max_width, max_height=max_height)
        return PreviewBitmap(width=width, height=height, pixels=pixels)
    rows = build_preview_rows(image, max_width=max_width, max_height=max_height)
    width = len(rows[0]) if rows else 1
    height = len(rows) if rows else 1
    pixels = bytearray()
    for row in rows:
        pixels.extend(max(0, min(255, int(value))) for value in row)
    return PreviewBitmap(width=width, height=height, pixels=bytes(pixels))


def enhance_preview_bitmap(
    bitmap: PreviewBitmap,
    *,
    mean_floor: float = 48.0,
    contrast_floor: int = 96,
    gamma: float = 0.5,
    target_mean: float = 42.0,
    max_brightness_boost: float = 8.0,
) -> PreviewBitmap:
    if not bitmap.pixels:
        return bitmap
    array = np.frombuffer(bitmap.pixels, dtype=np.uint8)
    if array.size == 0:
        return bitmap
    pixel_min = int(array.min())
    pixel_max = int(array.max())
    if pixel_max <= pixel_min:
        return bitmap
    pixel_mean = float(array.mean())
    if (pixel_max - pixel_min) >= contrast_floor and pixel_mean >= mean_floor:
        return bitmap

    adjusted = array.astype(np.float32)
    adjusted = (adjusted - pixel_min) * (255.0 / max(1, pixel_max - pixel_min))
    adjusted = np.clip(adjusted, 0.0, 255.0)
    if gamma != 1.0:
        adjusted = np.power(adjusted / 255.0, gamma) * 255.0
    adjusted_mean = float(adjusted.mean()) if adjusted.size else 0.0
    if adjusted_mean < target_mean and max_brightness_boost > 1.0:
        brightness_boost = min(max_brightness_boost, max(1.0, target_mean / max(adjusted_mean, 1.0)))
        adjusted *= brightness_boost
    adjusted = np.clip(adjusted, 0.0, 255.0).astype(np.uint8, copy=False)
    return PreviewBitmap(width=bitmap.width, height=bitmap.height, pixels=adjusted.tobytes())
