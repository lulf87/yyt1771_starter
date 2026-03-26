"""Shared preview-image rendering helpers for delivery shells."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from PIL import Image, ImageEnhance, ImageOps

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
    pixel_min = min(bitmap.pixels)
    pixel_max = max(bitmap.pixels)
    pixel_mean = sum(bitmap.pixels) / len(bitmap.pixels)
    if pixel_max <= pixel_min:
        return bitmap
    if (pixel_max - pixel_min) >= contrast_floor and pixel_mean >= mean_floor:
        return bitmap

    image = Image.frombytes("L", (bitmap.width, bitmap.height), bitmap.pixels)
    adjusted = ImageOps.autocontrast(image, cutoff=0)
    if gamma != 1.0:
        lut = [
            max(0, min(255, int(round(((index / 255.0) ** gamma) * 255.0))))
            for index in range(256)
        ]
        adjusted = adjusted.point(lut)
    adjusted_pixels = adjusted.tobytes()
    adjusted_mean = sum(adjusted_pixels) / len(adjusted_pixels) if adjusted_pixels else 0.0
    if adjusted_mean < target_mean and max_brightness_boost > 1.0:
        brightness_boost = min(max_brightness_boost, max(1.0, target_mean / max(adjusted_mean, 1.0)))
        adjusted = ImageEnhance.Brightness(adjusted).enhance(brightness_boost)
    return PreviewBitmap(width=bitmap.width, height=bitmap.height, pixels=adjusted.tobytes())
