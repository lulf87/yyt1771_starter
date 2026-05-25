# Real/Offline A-B Alignment Status - 2026-05-25

This file records the current alignment contract for the two active operator
states:

1. `dev_offline_capture` offline material replay
2. `dev_lab` real camera + real temperature-controller mode

The purpose is to prevent drift between the accepted offline material path and
the later real-device path. The offline material is the current truth source
for pixel geometry, contour extraction, and formal A/B point selection until
the real hardware is connected and revalidated.

## Hardware State During This Update

No real camera and no real temperature controller were connected during this
update. Therefore:

- offline/browser/code validation is current evidence
- real Hik camera acquisition remains unverified in the current hardware
  session
- real LU92XX temperature read/write behavior remains unverified in the
  current hardware session
- do not report `dev_lab` as hardware-verified from this update alone

## Truth Source

Current standard offline material:

```text
examples/runtime/camera_captures/20260522-183158-dev_lab
```

Current material properties from the existing freeze document and capture
manifest:

```text
source profile: dev_lab
camera profile: measurement
frame count: 5807
frame shape: 1364 x 2048
dtype: uint8
target fps: 10.0
temperature csv: temperature.csv
```

The accepted offline behavior is the baseline for later real-device behavior.
When real hardware is connected, any visible mismatch should be treated as a
`dev_lab` acquisition/profile/coordinate problem unless stronger evidence
shows the offline truth source is stale.

## Locked Alignment Requirements

### 1. Pixel Geometry

`dev_lab` and `dev_offline_capture` must use the same logical source pixels for
operator setup and live run:

```text
setup source size: 2048 x 1364
measurement source size: 2048 x 1364
preview display bound: 816 x 544
```

The real camera profile has a sensor ROI offset because it crops from the
physical camera sensor:

```text
dev_lab setup/measurement device_roi: x=512, y=342, width=2048, height=1364
```

The offline capture already stores the cropped source pixels, so its replay ROI
starts at zero:

```text
dev_offline_capture setup/measurement device_roi: x=0, y=0, width=2048, height=1364
```

The accepted invariant is not equal sensor origin; it is equal local source
pixels after translating out the real-camera sensor ROI origin.

### 2. Preset Definition Coordinate Space

Web setup definitions are source-frame coordinates. Live run startup must not
infer that small ROI values are display-frame coordinates and scale them again.

Current guarding commit:

```text
4a73312 Preserve source-coordinate definitions for live run
```

This prevents source-coordinate ROIs near the upper-left from being
misinterpreted as `816 x 543` display coordinates.

### 3. Contour Detection And Formal A/B Points

The formal A/B points must be target-object contour/boundary points. They are
not helper projections, source-vs-axis duplicate points, or operator-facing
display-only points.

Live preview overlay, live telemetry, live curve, persisted telemetry, and
analysis must all derive from the same formal pair:

```text
point_a_px / point_b_px
```

Current guarding commits:

```text
44933fa Stabilize offline AB tracking
c05751b Guard real and offline metric alignment
```

`c05751b` adds a 12-angle parity guard that compares `dev_lab` and
`dev_offline_capture` at every 30 degrees from `0` to `330` degrees using the
same source pixels and definition. It asserts:

- equal effective metric definition
- equal measurement source dimensions
- equal measurement-local coordinates after sensor-origin translation
- equal contour selection mode
- equal `point_a_px`
- equal `point_b_px`
- equal `metric_raw`

The system precheck now also includes a runtime guard:

```text
real_offline_pixel_alignment
```

For `dev_lab` and `dev_offline_capture`, this item fails if setup and live run
device ROI pixels drift away from the locked offline truth contract. It also
treats `offline_capture` as a supported active camera backend rather than a
failed unknown backend.

For a direct command-line audit of pixel geometry, contour selection, and formal
A/B parity across the 12 locked ROI angles, run:

```bash
../_local/yyt1771_starter/.conda-desktop-x86/bin/python3.11 -m src.application.real_offline_alignment
```

This command does not open the camera or temperature controller. It loads
`dev_lab` and `dev_offline_capture`, compares their effective measurement
source pixels, then runs the same metric chain on synthetic source frames at
every 30 degrees.

When the standard offline material and its accepted reference run are present,
the audit also reads the actual recorded grayscale material:

```text
examples/runtime/camera_captures/20260522-183158-dev_lab
examples/runtime/artifacts/run-9953bd601113
```

It verifies that the recorded material still has `5807` `uint8` frames at
`2048 x 1364`, checks that the recorded camera ROI still matches the
`dev_lab` measurement ROI, rebuilds the accepted effective acquisition ROI
(`x=275, y=0, width=1759, height=1289`), and then compares `dev_lab` and
`dev_offline_capture` metrics on representative low/mid/high temperature
sample frames from the actual material. This is still a no-hardware audit:
the real camera and temperature controller are not opened.

The same audit is exposed through the operator Web service for browser/API
diagnostics:

```text
GET /api/system/real-offline-alignment
```

This endpoint also does not open the camera or temperature controller. It is a
configuration and algorithm parity check only, and its response includes
`hardware_access: not_attempted` by design.

The operator runtime also enforces the locked pixel contract before vision
processing:

- setup preview one-shot freeze validates the actual returned frame pixels
- setup preview stream validates every emitted frame
- live-run measurement wraps `camera.read_frame()` and validates every
  measurement frame before contour extraction

For the locked real/offline profiles, a returned frame that is not `2048 x
1364` fails immediately with a pixel-contract error instead of flowing into
contour detection or formal A/B selection. This is intended to surface true
camera SDK / ROI drift early, before it can produce misleading A/B points or
curve data.

### 4. Run Guard Behavior

Both active profiles must avoid silently stopping valid long runs because of
temporary tracking invalidation:

```text
manual_stop_max_samples: 0
stop_on_invalid_tracking: false
invalid_tracking_grace_samples: 5
```

Current guarding commit:

```text
fe47911 Align real and offline run profile guards
```

## Hik SDK Error Handling

The recent Hik SDK open-device failure has been normalized so the operator sees
the likely cause instead of an opaque SDK code.

Current guarding commit:

```text
0d317dd Normalize Hik camera runtime errors
```

Current normalized error coverage includes:

```text
0x80000203 -> access denied / another camera client / camera not connected
SDK import missing -> selected runtime cannot access Hik MVS binding
0x80000004 -> handle creation / SDK runtime issue
```

This is an error-reporting and result-preservation fix. It does not prove real
camera access while hardware is disconnected.

## Current Verification Evidence

The following checks were run with:

```bash
../_local/yyt1771_starter/.conda-desktop-x86/bin/python3.11
```

Relevant passed checks:

```text
tests/application/test_device_factory.py::test_real_and_offline_profiles_share_metric_pixels_across_roi_angles
12 passed

tests/application/test_device_factory.py
tests/webapp/test_config_loader.py
tests/application/test_live_run_service.py
tests/webapp/test_live_run_api.py
119 passed, 1 existing warning

tests/vision/test_contour_direction.py
tests/workflow/test_offline_capture_tracking_regression.py
tests/architecture
52 passed

compileall src tests
node --check src/webapp/static/app.js
git diff --check
passed
```

Browser evidence:

```text
profile: dev_offline_capture
URL: http://127.0.0.1:8002/
Observed: offline grayscale preview stream rendered nonblank material
```

The browser check verifies the offline material path remains visible. It does
not verify real hardware.

## Required Real-Hardware Revalidation

When the real camera and temperature controller are connected, validate with:

```bash
../_local/yyt1771_starter/.conda-desktop-x86/bin/python3.11 -m src.webapp.serve --profile dev_lab
```

Expected URL:

```text
http://127.0.0.1:8000/
```

Required visual checks:

1. The home page reports source pixels equivalent to `2048 x 1364`.
2. Preset/freeze uses the same object geometry as offline replay.
3. ROI rotation does not change the intended local source coordinate chain.
4. A/B points are on the target contour/boundary in preset.
5. After live run starts, A/B telemetry remains the same formal point pair
   source used by the overlay and curve.
6. If Hik open fails, the normalized `0x80000203` message is shown and the run
   result preserves the failure detail.

Do not mark the real/offline alignment goal complete until these real-hardware
checks have been observed in the current hardware session.
