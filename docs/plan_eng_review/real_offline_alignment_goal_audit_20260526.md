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
| Formal A/B point selection must match the offline truth | `algorithm_contract.ab_selection` records formal A/B as `target_contour_boundary`, fields `point_a_px / point_b_px`, `direction_projection_mode=max_chord`, and `projected_points_exposed_as_formal_ab=false`. The 12-angle audit uses `directional_contour_max_chord` at 30 degree steps. | No-hardware contract verified |
| Connected real camera must prove setup and measurement pixels with actual frames | `src.application.real_camera_alignment_probe.probe_real_camera_alignment()`, `python -m src.application.real_camera_alignment_probe --profile dev_lab`, and `POST /api/system/real-offline-alignment/live-probe` first report the real/offline `alignment_contract`, then attempt live camera access, read one `setup_preview` frame and one `measurement` frame, and validate both with the same frame pixel contract. Browser verification without connected hardware returned `hardware_access=attempted` and a structured camera-discovery failure instead of a false pass. | Implemented; hardware pass pending |
| One live probe response must expose pixel, contour, and A/B rule status together | `live-probe` and the CLI now include `alignment_contract.pixel_contract`, `alignment_contract.algorithm_contract.vision`, and `alignment_contract.algorithm_contract.ab_selection` before hardware frame results. If the offline-truth contract fails, the probe returns `hardware_access=not_attempted` and does not open the camera. | No-hardware contract verified |
| Runtime preset and live-run paths must not bypass the alignment contract | `src.application.real_offline_alignment_guard.assert_real_offline_alignment_ready()` gates locked profiles before `definition/auto` and before `LiveRunService.start_run()`. If source pixels, contour settings, or live A/B tracking policy drift from the offline truth, preset auto-detect returns `409` before fetching a frame and live run start returns `409` before opening the camera. | No-hardware runtime guard verified |
| Operator/request contour settings must not bypass the offline truth | Locked profiles now validate the request or saved `MeasurementDefinition` contour fields before save-definition, preset auto-detect, and live-run start. The locked auto-detect path uses only the offline-truth contour candidate (`dark_on_light`, `adaptive`, `ignore_internal_texture=false`, `min_target_area_px=200`) instead of searching alternate threshold/polarity combinations. | No-hardware runtime guard verified |
| Operator/request A/B selection mode must not bypass the offline truth | Locked profiles now reject `direction_projection_mode=auto` and `direction_projection_mode=mask_projection` before preset auto-detect, save-definition, and live-run start. The Web default now sends `max_chord`, the precheck detail exposes `direction_projection_mode=max_chord`, and the standard offline-material sample audit overrides the historical reference definition's old `mask_projection` value to verify the current formal A/B rule. | No-hardware runtime guard verified |
| Browser operator defaults must start from the offline truth | The home page detection controls now default to the offline-truth contour settings. In particular, `live-ignore-internal-texture` is not checked by default, so a normal operator ROI recompute does not immediately violate the locked-profile contour guard. | Browser shell verified |
| The no-hardware 12-angle audit must use the same contour settings as the offline truth | The synthetic angle audit now builds its `MeasurementDefinition` contour fields from `dev_offline_capture` runtime vision settings and exposes `contour_settings` per angle. This prevents the real/offline audit from proving A/B parity with stale historical definition parameters. | No-hardware contract verified |
| The same formal A/B pair must feed overlay, telemetry, curve, and analysis | Canonical requirement `live_setup_freeze_roi_tracking_requirement_v1.md` R6.1 / R6.2 locks this semantic rule. This audit verifies the no-hardware profile/algorithm contract, but does not prove live hardware overlay behavior without a connected camera. | Partially verified; hardware visual check pending |
| Hik SDK `ret=0x80000203` open-device errors must be actionable | Commit `0d317dd Normalize Hik camera runtime errors` adds operator-facing normalization for `Failed to open device via Hik MVS SDK (ret=0x80000203)`. Current normalization also reads wrapped exception causes and gives an actionable message for generic `Failed to open Hik GigE / MVS camera` open-state failures. Targeted tests cover direct and wrapped SDK failures, preview fetch, preview stream start, and failed live run normalization. | Verified in tests |

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
  tests/application/test_real_camera_alignment_probe.py \
  tests/webapp/test_precheck_api.py::test_real_camera_alignment_live_probe_api_returns_hardware_probe_payload -q
```

Result: `4 passed`.

```bash
../_local/yyt1771_starter/.conda-desktop-x86/bin/python3.11 -m pytest \
  tests/application/test_real_camera_alignment_probe.py -q
```

Result: `5 passed`.

```bash
../_local/yyt1771_starter/.conda-desktop-x86/bin/python3.11 -m pytest \
  tests/application/test_real_camera_alignment_probe.py \
  tests/webapp/test_precheck_api.py::test_real_camera_alignment_live_probe_api_returns_hardware_probe_payload -q
```

Result: `7 passed`.

```bash
../_local/yyt1771_starter/.conda-desktop-x86/bin/python3.11 -m pytest \
  tests/application/test_real_camera_alignment_probe.py \
  tests/webapp/test_precheck_api.py::test_real_camera_alignment_live_probe_api_returns_hardware_probe_payload \
  tests/application/test_real_offline_alignment.py \
  tests/workflow/test_precheck.py -q
```

Result: `23 passed`.

```bash
../_local/yyt1771_starter/.conda-desktop-x86/bin/python3.11 -m pytest \
  tests/application/test_real_offline_alignment_guard.py \
  tests/workflow/test_precheck.py \
  tests/webapp/test_live_run_api.py::test_auto_detect_definition_blocks_locked_profile_when_alignment_contract_drifts \
  tests/webapp/test_live_run_api.py::test_start_live_run_blocks_locked_profile_when_alignment_contract_drifts -q
```

Result: `16 passed`.

```bash
../_local/yyt1771_starter/.conda-desktop-x86/bin/python3.11 -m pytest \
  tests/application/test_real_offline_alignment_guard.py \
  tests/workflow/test_precheck.py \
  tests/webapp/test_live_run_api.py::test_auto_detect_definition_blocks_locked_profile_when_alignment_contract_drifts \
  tests/webapp/test_live_run_api.py::test_auto_detect_definition_blocks_locked_profile_request_contour_drift \
  tests/webapp/test_live_run_api.py::test_save_definition_blocks_locked_profile_request_contour_drift \
  tests/webapp/test_live_run_api.py::test_locked_profile_auto_detect_uses_only_offline_truth_contour_candidate \
  tests/webapp/test_live_run_api.py::test_start_live_run_blocks_locked_profile_when_alignment_contract_drifts \
  tests/webapp/test_live_run_api.py::test_start_live_run_blocks_locked_profile_saved_definition_contour_drift -q
```

Result: `22 passed`.

```bash
../_local/yyt1771_starter/.conda-desktop-x86/bin/python3.11 -m pytest \
  tests/application/test_real_offline_alignment.py \
  tests/webapp/test_ui_shell.py::test_ui_shell_route_returns_html_with_expected_hooks -q
```

Result: `6 passed`.

```bash
../_local/yyt1771_starter/.conda-desktop-x86/bin/python3.11 -m pytest \
  tests/application/test_real_offline_alignment_guard.py \
  tests/application/test_real_camera_alignment_probe.py \
  tests/application/test_real_offline_alignment.py \
  tests/workflow/test_precheck.py \
  tests/webapp/test_precheck_api.py \
  tests/webapp/test_live_run_api.py -q
```

Result: `119 passed, 1 warning`.

```bash
../_local/yyt1771_starter/.conda-desktop-x86/bin/python3.11 -m pytest \
  tests/webapp/test_live_run_api.py::test_auto_detect_definition_returns_suggested_points_for_mock_preview \
  tests/webapp/test_live_run_api.py::test_auto_detect_definition_uses_directional_contour_when_direction_angle_is_provided \
  tests/webapp/test_live_run_api.py::test_start_live_run_completes_and_persists_result_bundle \
  tests/webapp/test_live_run_api.py::test_start_live_run_uses_measurement_camera_profile \
  tests/webapp/test_live_run_api.py::test_start_live_run_reduces_measurement_camera_roi_for_real_camera_profile \
  tests/webapp/test_live_run_api.py::test_failed_live_run_normalizes_hik_access_denied_error -q
```

Result: `6 passed`.

```bash
../_local/yyt1771_starter/.conda-desktop-x86/bin/python3.11 \
  -m src.application.real_camera_alignment_probe \
  --profile dev_lab_camera_mock_temp
```

Result: exited `1` because no camera is connected. The JSON response was
structured as `status=fail`, `hardware_access=attempted`, expected source size
`2048 x 1364`, expected device ROI `x=512, y=342, width=2048, height=1364`,
and detail `No Hik cameras were discovered by the MVS SDK`. Before attempting
hardware, the same JSON included `alignment_contract.status=ok`,
`alignment_contract.pixel_contract.source_size_px=2048 x 1364`,
`alignment_contract.algorithm_contract.vision=dark_on_light/adaptive`, and
`alignment_contract.algorithm_contract.ab_selection.formal_point_source=target_contour_boundary`.

```bash
../_local/yyt1771_starter/.conda-desktop-x86/bin/python3.11 -m pytest \
  tests/application/test_real_camera_alignment_probe.py \
  tests/application/test_real_offline_alignment.py \
  tests/application/test_device_factory.py \
  tests/application/test_live_preview_service.py \
  tests/application/test_live_run_service.py \
  tests/application/test_camera_errors.py \
  tests/webapp/test_live_run_api.py \
  tests/webapp/test_config_loader.py \
  tests/webapp/test_precheck_api.py \
  tests/workflow/test_precheck.py -q
```

Result: `184 passed, 1 warning`.

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
- `http://127.0.0.1:8012/docs`
- `http://127.0.0.1:8013/docs`
- `http://127.0.0.1:8014/`

Observed in the real browser:

- precheck alignment item was `ok`
- detail included `source pixels and algorithm settings match`
- detail included `origin=(512, 342), size=(2048, 1364)`
- detail included `preview_display=816x544`
- detail included `acquisition=mono8/50000us/12.0dB`
- detail included `vision=dark_on_light/adaptive`
- detail included `tracking=continue_on_invalid`
- detail included `ab_points=formal target-contour point_a_px/point_b_px`
- detail included `direction_projection_mode=max_chord`
- alignment audit returned `hardware_access=not_attempted`
- alignment audit returned `algorithm_contract.ab_selection`
- Swagger UI execution of `POST /api/system/real-offline-alignment/live-probe`
  returned HTTP `200` with response body `status=fail`,
  `hardware_access=attempted`, `profile=dev_lab_camera_mock_temp`,
  expected size `2048 x 1364`, expected device ROI
  `x=512, y=342, width=2048, height=1364`, and detail
  `No Hik cameras were discovered by the MVS SDK`
- the same browser response included `alignment_contract.pixel_contract`,
  `alignment_contract.algorithm_contract.vision`, and
  `alignment_contract.algorithm_contract.ab_selection`; visible values included
  `dark_on_light`, `adaptive`, `target_contour_boundary`, `point_a_px`, and
  `point_b_px`
- on `http://127.0.0.1:8013/docs`, a locked-profile request drift
  (`foreground_polarity=light_on_dark`) returned HTTP `409` from
  `/api/runs/{run_id}/definition/auto` before hardware access, with detail
  stating that request contour settings must match offline truth contour
  settings
- on the same browser session, `POST
  /api/system/real-offline-alignment/live-probe` returned HTTP `200` with
  `status=fail`, `hardware_access=attempted`, and the expected no-camera detail
  `No Hik cameras were discovered by the MVS SDK`, while still exposing the
  locked offline alignment contract
- on `http://127.0.0.1:8014/` with `dev_offline_capture`, the live preview
  viewport showed source frame `2048x1364` and display frame `816x543`; the
  detection controls showed `dark_on_light`, `adaptive`, minimum area `200`,
  and the `忽略内部纹理` checkbox visually unchecked
- on the same offline browser session, `/api/system/precheck` returned
  `real_offline_pixel_alignment=ok` with detail confirming
  `origin=(0, 0), size=(2048, 1364)`, `preview_display=816x544`,
  `acquisition=mono8/50000us/12.0dB`,
  `vision=dark_on_light/adaptive`, `internal_texture=False`, and
  formal target-contour `point_a_px/point_b_px`
- screenshot saved to
  `/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/_local/browser_checks/live_probe_no_hardware_swagger_20260526.png`
- updated screenshot saved to
  `/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/_local/browser_checks/live_probe_alignment_contract_20260526.png`
- offline browser screenshots saved by Playwright as
  `offline_truth_ui_defaults_20260526.png` and
  `offline_truth_ignore_texture_unchecked_20260526.png`

## Remaining Hardware Validation

The goal is not fully complete until real devices are connected and the
following are validated on actual hardware:

1. `dev_lab` startup opens the camera without SDK/device-access error.
2. Either `python -m src.application.real_camera_alignment_probe --profile
   dev_lab` or `POST /api/system/real-offline-alignment/live-probe` passes
   against the connected camera, proving real `setup_preview` and `measurement`
   frames both match `2048 x 1364` plus the configured device ROI metadata.
3. Real live run uses the same local source pixel size and acquisition contract
   as setup preview.
4. Real preset A/B points visually sit on the target contour for representative
   ROI angles.
5. Real live-run A/B points stay on the target contour and do not diverge from
   the offline-validated behavior.
6. LU92XX temperature controller behavior is verified separately with connected
   hardware.
