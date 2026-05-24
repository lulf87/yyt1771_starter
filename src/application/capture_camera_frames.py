"""CLI for recording direct camera frames for offline debugging."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Sequence

from src.application.device_factory import build_temp_controller, open_camera
from src.application.runtime_config import load_runtime_config
from src.camera.camera_frame_capture import CaptureOptions, capture_frames


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    runtime_config = load_runtime_config(args.profile)
    output_dir = args.output_dir or _default_output_dir(args.profile)
    camera = open_camera(runtime_config, profile_name=args.camera_profile)
    temp_reader = (
        build_temp_controller(runtime_config)
        if _needs_temp_controller(
            with_temp=args.with_temp,
            target_temperature_celsius=args.target_temperature_celsius,
            output_power_percent=args.output_power_percent,
            start_output=args.start_temp_output,
        )
        else None
    )
    if temp_reader is not None:
        _configure_temp_controller(
            temp_reader,
            target_temperature_celsius=args.target_temperature_celsius,
            output_power_percent=args.output_power_percent,
            start_output=args.start_temp_output,
        )
    summary = capture_frames(
        camera,
        CaptureOptions(
            output_dir=output_dir,
            profile=runtime_config.profile,
            camera_profile=args.camera_profile,
            frame_format=args.frame_format,
            save_video=not args.no_video,
            video_fps=args.video_fps,
            duration_sec=args.duration_sec,
            max_frames=args.max_frames,
            target_fps=args.target_fps,
            temp_every_n_frames=args.temp_every_n_frames,
        ),
        temp_reader=temp_reader,
    )
    print(f"Captured {summary.frame_count} frame(s) to {summary.output_dir}")
    print(f"Manifest: {summary.manifest_path}")
    if summary.video_path is not None:
        print(f"Video: {summary.video_path}")
    if summary.temperature_csv_path is not None:
        print(f"Temperature CSV: {summary.temperature_csv_path}")
    return 0


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Record direct grayscale camera frames and an optional debug video.",
    )
    parser.add_argument(
        "--profile",
        default="dev_lab",
        help="Runtime profile used to open the camera, for example dev_lab or dev_lab_camera_mock_temp.",
    )
    parser.add_argument(
        "--camera-profile",
        choices=("setup_preview", "measurement"),
        default="measurement",
        help="Camera acquisition profile to use.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Capture output directory. Defaults to examples/runtime/camera_captures/<timestamp>-<profile>.",
    )
    parser.add_argument(
        "--duration-sec",
        type=float,
        default=30.0,
        help="Maximum capture duration in seconds.",
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        default=None,
        help="Optional maximum frame count. The capture stops at whichever limit is reached first.",
    )
    parser.add_argument(
        "--target-fps",
        type=float,
        default=None,
        help="Optional software-side rate limit for capture.",
    )
    parser.add_argument(
        "--frame-format",
        choices=("none", "npy", "png", "both"),
        default="npy",
        help="Per-frame output format. Use npy for raw grayscale values; png is an 8-bit preview.",
    )
    parser.add_argument(
        "--no-video",
        action="store_true",
        help="Disable MJPEG AVI preview video output.",
    )
    parser.add_argument(
        "--video-fps",
        type=float,
        default=20.0,
        help="FPS metadata used for the optional AVI video.",
    )
    parser.add_argument(
        "--with-temp",
        action="store_true",
        help="Also read the configured temperature backend and write temperature.csv.",
    )
    parser.add_argument(
        "--temp-every-n-frames",
        type=int,
        default=1,
        help="Read temperature every N frames and carry the latest reading on intermediate frames.",
    )
    parser.add_argument(
        "--target-temperature-celsius",
        "--set-temp-c",
        dest="target_temperature_celsius",
        type=float,
        default=None,
        help="Set the configured temperature controller target before capture.",
    )
    parser.add_argument(
        "--output-power-percent",
        type=float,
        default=None,
        help="Set the configured temperature controller output power before capture.",
    )
    parser.add_argument(
        "--start-temp-output",
        action="store_true",
        help="Start temperature-controller output before capture.",
    )
    return parser.parse_args(argv)


def _default_output_dir(profile: str) -> Path:
    project_root = Path(__file__).resolve().parents[2]
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_profile = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in profile)
    return project_root / "examples" / "runtime" / "camera_captures" / f"{stamp}-{safe_profile}"


def _needs_temp_controller(
    *,
    with_temp: bool,
    target_temperature_celsius: float | None,
    output_power_percent: float | None,
    start_output: bool,
) -> bool:
    return bool(
        with_temp
        or target_temperature_celsius is not None
        or output_power_percent is not None
        or start_output
    )


def _configure_temp_controller(
    temp_controller: object,
    *,
    target_temperature_celsius: float | None,
    output_power_percent: float | None,
    start_output: bool,
) -> None:
    if target_temperature_celsius is not None:
        temp_controller.set_target_temperature(float(target_temperature_celsius))
    if output_power_percent is not None:
        temp_controller.set_output_power_percent(float(output_power_percent))
    if start_output:
        temp_controller.start_output()


if __name__ == "__main__":
    raise SystemExit(main())
