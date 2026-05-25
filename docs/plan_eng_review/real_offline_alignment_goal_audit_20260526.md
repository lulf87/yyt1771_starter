# Real / Offline Alignment Goal Audit 2026-05-26

## Goal

Use the accepted `dev_offline_capture` material as the truth source, and keep
all locked real-device profiles aligned with it for:

1. preset and live-run source pixels
2. contour-detection settings
3. formal A/B point selection
4. previously observed Hik SDK open-device error handling

## Current Hardware Boundary

Real camera and temperature controller are currently not connected. Therefore:

- no real camera frame capture has been validated in this audit
- no LU92XX / Modbus hardware write has been validated in this audit
- hardware behavior must remain `unverified` until the devices are connected

All evidence below is no-hardware evidence from config contracts, offline
material, CLI audits, automated tests, and browser-visible local Web APIs.

## Offline Truth Source

- profile: `dev_offline_capture`
- capture directory:
  `examples/runtime/camera_captures/20260522-183158-dev_lab`
- reference run:
  `examples/runtime/artifacts/run-9953bd601113`
- frame count: `5807`
- source frame size: `2048 x 1364`
- dtype: `uint8`

## Locked Profiles Under Audit

- `dev_lab`
- `dev_lab_camera_mock_temp`
- `prod_win`

## Requirement Evidence

| Requirement | Current evidence | Status |
| --- | --- | --- |
| Preset and live-run source pixels must match the offline truth | `src.workflow.precheck` requires setup/measurement `device_roi`, acquisition fields, preview display bounds, and fails if any locked profile drifts. `src.application.real_offline_alignment` audits all locked real profiles against `dev_offline_capture`. | No-hardware contract verified |
| Preset and live-run source pixels must both be `2048 x 1364` | Alignment audit reports `source_size_px={"width": 2048, "height": 1364}` for all locked real profiles. Browser `/api/system/real-offline-alignment` returned the same value for `dev_lab_camera_mock_temp`. | No-hardware contract verified |
| Contour detection must match the offline truth | `algorithm_contract.vision` locks `foreground_polarity=dark_on_light`, `threshold_mode=adaptive`, `edge_threshold=10.0`, `ignore_internal_texture=false`, `min_target_area_px=200`, and `quality_threshold=0.75`. Precheck now fails if the locked profile does not provide or match this vision contract. | No-hardware contract verified |
| Formal A/B point selection must match the offline truth | `algorithm_contract.ab_selection` records formal A/B as `target_contour_boundary`, fields `point_a_px / point_b_px`, and `projected_points_exposed_as_formal_ab=false`. The 12-angle audit uses `directional_contour_max_chord` at 30 degree steps. | No-hardware contract verified |
| The same formal A/B pair must feed overlay, telemetry, curve, and analysis | Canonical requirement `live_setup_freeze_roi_tracking_requirement_v1.md` R6.1 / R6.2 locks this semantic rule. This audit verifies the no-hardware profile/algorithm contract, but does not prove live hardware overlay behavior without a connected camera. | Partially verified; hardware visual check pending |
| Hik SDK `ret=0x80000203` open-device errors must be actionable | Commit `0d317dd Normalize Hik camera runtime errors` adds operator-facing normalization for `Failed to open device via Hik MVS SDK (ret=0x80000203)`. Targeted tests cover preview fetch, preview stream start, and failed live run normalization. | Verified in tests |

## Verification Commands Run

```bash
../_local/yyt1771_starter/.conda-desktop-x86/bin/python3.11 -m pytest \
  tests/workflow/test_precheck.py \
  tests/webapp/test_precheck_api.py \
  tests/application/test_real_offline_alignment.py -q
```

Result: `34 passed`.

```bash
../_local/yyt1771_starter/.conda-desktop-x86/bin/python3.11 -m src.application.real_offline_alignment --all-profiles
```

Result summary:

```text
ok 3 not_attempted
dev_lab ok {'width': 2048, 'height': 1364} adaptive False target_contour_boundary ['directional_contour_max_chord']
dev_lab_camera_mock_temp ok {'width': 2048, 'height': 1364} adaptive False target_contour_boundary ['directional_contour_max_chord']
prod_win ok {'width': 2048, 'height': 1364} adaptive False target_contour_boundary ['directional_contour_max_chord']
```

```bash
../_local/yyt1771_starter/.conda-desktop-x86/bin/python3.11 -m pytest \
  tests/application/test_real_offline_alignment.py \
  tests/application/test_device_factory.py \
  tests/application/test_live_preview_service.py \
  tests/application/test_live_run_service.py \
  tests/webapp/test_live_run_api.py \
  tests/webapp/test_config_loader.py \
  tests/webapp/test_precheck_api.py \
  tests/workflow/test_precheck.py -q
```

Result: `178 passed, 1 warning`.

```bash
../_local/yyt1771_starter/.conda-desktop-x86/bin/python3.11 -m pytest \
  tests/application/test_camera_errors.py \
  tests/webapp/test_live_run_api.py::test_preview_frame_fetch_normalizes_hik_access_denied_error \
  tests/webapp/test_live_run_api.py::test_preview_stream_start_normalizes_hik_access_denied_error \
  tests/webapp/test_live_run_api.py::test_failed_live_run_normalizes_hik_access_denied_error -q
```

Result: `5 passed`.

```bash
../_local/yyt1771_starter/.conda-desktop-x86/bin/python3.11 -m compileall src tests
node --check src/webapp/static/app.js
git diff --check
```

Result: passed.

## Browser Verification

Profile: `dev_lab_camera_mock_temp`

URL:

- `http://127.0.0.1:8002/api/system/precheck`
- `http://127.0.0.1:8002/api/system/real-offline-alignment`

Observed in the real browser:

- precheck alignment item was `ok`
- detail included `source pixels and algorithm settings match`
- detail included `origin=(512, 342), size=(2048, 1364)`
- detail included `preview_display=816x544`
- detail included `acquisition=mono8/50000us/12.0dB`
- detail included `vision=dark_on_light/adaptive`
- detail included `tracking=continue_on_invalid`
- detail included `ab_points=formal target-contour point_a_px/point_b_px`
- alignment audit returned `hardware_access=not_attempted`
- alignment audit returned `algorithm_contract.ab_selection`

## Remaining Hardware Validation

The goal is not fully complete until real devices are connected and the
following are validated on actual hardware:

1. `dev_lab` startup opens the camera without SDK/device-access error.
2. Real setup preview produces the same local source pixel size as the offline
   truth: `2048 x 1364`.
3. Real live run uses the same local source pixel size and acquisition contract
   as setup preview.
4. Real preset A/B points visually sit on the target contour for representative
   ROI angles.
5. Real live-run A/B points stay on the target contour and do not diverge from
   the offline-validated behavior.
6. LU92XX temperature controller behavior is verified separately with connected
   hardware.

