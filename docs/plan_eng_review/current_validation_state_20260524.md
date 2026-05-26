# Current Validation State - 2026-05-24

This file records what should be preserved from the current worktree before
cleanup. It intentionally separates verified state, working assumptions, and
remaining risks.

## Current Product Center

The active product repository is:

```text
/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/yyt1771_starter
```

The surrounding `/1771` directory is a workspace that also contains local
runtime data, historical reference material, and archived device/source
references.

## Local Checkpoint

A local checkpoint was created without deleting or reverting files:

```text
/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/_local/checkpoints/yyt1771_starter-20260524-112416
```

It contains:

```text
git-status-short.txt
git-status-ignored-short.txt
tracked-working-tree.diff
project-file-index-maxdepth3.txt
listening-python-ports.txt
dev_lab.yaml
dev_lab.local.yaml
dev_offline_capture.yaml
```

This checkpoint is not a replacement for a proper git commit. It is only a
recoverability aid before cleanup.

## Preserved Engineering Rules

The live setup and live run A/B rule to preserve:

```text
Formal A/B points are the target object's real contour or boundary points.
There should not be separate projected/source-vs-axis point pairs in the
operator-facing measurement chain. Live curves, telemetry, and analysis must
derive from the same point pair displayed to the operator.
```

The current fixed data chain remains:

```text
Frame -> ShapeMetric -> SyncPoint -> Curve -> Result
```

The current `mac-finish` delivery direction is:

```text
webapp -> application -> workflow / storage / report
```

`desktop_app` remains in the repository as paused legacy / fallback material,
but it is not the current Windows migration path.

## Known Preserved Capabilities

Current worktree contains implementation work for:

- real Hik GigE / MVS camera adapter path
- LU92XX Modbus RTU temperature controller adapter path
- offline capture camera adapter
- offline capture temperature adapter
- camera-frame capture tool for generating offline material
- Web live setup with Freeze -> ROI -> A/B recompute -> live run
- rotated ROI interaction and direction-aware contour detection
- persisted run telemetry and analysis artifacts

These capabilities are part of the current成果 and should not be removed during
cleanup.

## Current Offline Material Baseline

The active offline material is:

```text
examples/runtime/camera_captures/20260522-183158-dev_lab
```

It is the current standard replay source because it was captured from the real
camera measurement profile as grayscale `uint8` frames at measurement
resolution.

Observed material facts from current files:

```text
frame_count: 5807
shape: 1364 x 2048
dtype: uint8
target_fps: 10.0
achieved_fps: 9.677583513485446
temperature source: temperature.csv
temperature range: about 1.2 C to 15.0 C
```

## Current Runtime Observation

During this freeze, one Python Web process was listening on:

```text
127.0.0.1:8002
```

That corresponds to the offline replay state.

Recent offline live run telemetry showed that the displayed `3-5 Hz` value is
the actual live processing/sample rate, not the source material frame rate.
The source material is about `9.7 fps`; the current bottleneck is A/B contour
metric extraction, which can take hundreds of milliseconds per sample.

This is a remaining performance issue, not a cleanup issue.

## Remaining Risks

Do not claim these are solved until they are revalidated:

- A/B contour detection stability over full offline material at operator-visible
  10 Hz replay
- live run throughput meeting the configured 10 Hz offline and real hardware
  target
- real camera + real temperature controller end-to-end validation in the current
  hardware session
- temperature output power write/readback behavior on the real LU92XX
  controller
- UI clarity around preset A/B points versus live telemetry A/B points
- any cleanup that removes runtime artifacts or old materials before confirming
  they are not needed for reproduction

## Verification Policy For Future Fixes

For UI or vision-visible changes, do not deliver based only on unit tests.
Use the real browser against the local Web app and visually confirm the
operator-visible behavior before claiming completion.

For hardware-dependent claims, state exactly which hardware/profile was used.
If no real hardware was connected, report that hardware validation is
unverified.
