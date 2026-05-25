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
| Connected real camera must prove contour/A-B behavior with an operator ROI | `POST /api/system/real-offline-alignment/live-probe` and `python -m src.application.real_camera_alignment_probe --profile dev_lab --definition-file <definition.json>` can now accept the current `MeasurementDefinition` payload. When provided, the probe first guards the definition against the offline-truth contour/A-B contract, then runs the same formal `DirectionalContourMetricExtractor` with `direction_projection_mode=max_chord` on both the real setup-preview frame and the real measurement frame, returning per-profile `ab_detection` with `selection_mode`, `direction_projection_mode`, quality, metric, and formal `point_a_px / point_b_px`. | Implemented; hardware pass pending |
| Offline material live-probe must not be mistaken for hardware validation | `probe_real_camera_alignment()` now exposes `frame_source_mode` and `frame_access` separately from `hardware_access`. When the active profile is `dev_offline_capture`, the probe may read setup/measurement offline frames and validate formal A/B, but reports `frame_source_mode=offline_capture`, `frame_access=attempted`, and `hardware_access=not_attempted`. | No-hardware boundary verified |
| One live probe response must expose pixel, contour, and A/B rule status together | `live-probe` and the CLI now include `alignment_contract.pixel_contract`, `alignment_contract.algorithm_contract.vision`, and `alignment_contract.algorithm_contract.ab_selection` before hardware frame results. If the offline-truth contract fails, the probe returns `hardware_access=not_attempted` and does not open the camera. | No-hardware contract verified |
| Runtime preset and live-run paths must not bypass the alignment contract | `src.application.real_offline_alignment_guard.assert_real_offline_alignment_ready()` gates locked profiles before `definition/auto` and before `LiveRunService.start_run()`. If source pixels, contour settings, or live A/B tracking policy drift from the offline truth, preset auto-detect returns `409` before fetching a frame and live run start returns `409` before opening the camera. | No-hardware runtime guard verified |
| Operator/request contour settings must not bypass the offline truth | Locked profiles now validate the request or saved `MeasurementDefinition` contour fields before save-definition, preset auto-detect, and live-run start. The locked auto-detect path uses only the offline-truth contour candidate (`dark_on_light`, `adaptive`, `ignore_internal_texture=false`, `min_target_area_px=200`) instead of searching alternate threshold/polarity combinations. | No-hardware runtime guard verified |
| Operator/request A/B selection mode must not bypass the offline truth | Locked profiles now reject `direction_projection_mode=auto` and `direction_projection_mode=mask_projection` before preset auto-detect, save-definition, live-run start, Web live-probe, and CLI definition probe frame access. The Web default now sends `max_chord`, the precheck detail exposes `direction_projection_mode=max_chord`, and the standard offline-material sample audit overrides the historical reference definition's old `mask_projection` value to verify the current formal A/B rule. | No-hardware runtime guard verified |
| Desktop migration entry points must not reintroduce stale A/B semantics | `DesktopWorkbenchController.save_definition()` now uses the same real/offline alignment and definition guards as the Web save-definition path. Locked desktop profiles reject stale `MeasurementDefinition` values such as `direction_projection_mode=mask_projection` before the draft can be saved. | No-hardware runtime guard verified |
| Metric source creation must not bypass the offline truth | `src.application.device_factory.build_metric_source()` now applies the same locked-profile alignment and definition guards before creating `PriorTrackingMetricSource` or `LockedDefinitionMetricSource`. A direct factory call with stale contour settings or `direction_projection_mode=mask_projection` is rejected before live tracking can start. | No-hardware runtime guard verified |
| New operator definitions must default to the offline-truth A/B mode | `MeasurementDefinition`, Web request/response schemas, Web preset default resolution, real/offline probe payload loading, and desktop bootstrap smoke definitions now default to `direction_projection_mode=max_chord`. Legacy `auto` and `mask_projection` values remain recognized so locked-profile guards can reject stale requests explicitly, but omitted current fields no longer re-enter the old A/B semantics. | No-hardware runtime guard verified |
| Low-level contour extraction defaults must not reintroduce stale behavior | `DirectionalContourConfig` now defaults to the offline-truth contour/A-B contract: `threshold_mode=adaptive`, `foreground_polarity=dark_on_light`, `ignore_internal_texture=false`, `min_target_area_px=200`, and `projection_mode=max_chord`. Explicit `auto` / `mask_projection` remains available only as an explicit legacy/test path. | No-hardware vision guard verified |
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
  tests/application/test_device_factory.py::test_build_metric_source_blocks_locked_profile_stale_definition_before_source_creation -q
```

Result: `1 passed`.

```bash
../_local/yyt1771_starter/.conda-desktop-x86/bin/python3.11 -m pytest \
  tests/application/test_device_factory.py -q
```

Result: `27 passed`.

```bash
../_local/yyt1771_starter/.conda-desktop-x86/bin/python3.11 -m pytest \
  tests/architecture/test_model_contracts.py \
  tests/curve/test_afas_postprocessing_dataset.py \
  tests/webapp/test_live_run_api.py \
  tests/webapp/test_ui_shell.py \
  tests/application/test_real_camera_alignment_probe.py \
  tests/application/test_real_offline_alignment.py \
  tests/application/test_real_offline_alignment_guard.py \
  tests/application/test_device_factory.py \
  tests/desktop_app/test_controller.py -q
```

Result: `151 passed, 1 warning`.

```bash
../_local/yyt1771_starter/.conda-desktop-x86/bin/python3.11 -m pytest \
  tests/vision/test_contour_direction.py \
  tests/workflow/test_live_run.py -q
```

Result: `77 passed`.

```bash
../_local/yyt1771_starter/.conda-desktop-x86/bin/python3.11 -m pytest \
  tests/vision/test_contour_direction.py \
  tests/workflow/test_live_run.py \
  tests/application/test_device_factory.py \
  tests/application/test_real_offline_alignment.py \
  tests/application/test_real_camera_alignment_probe.py \
  tests/webapp/test_live_run_api.py \
  tests/webapp/test_ui_shell.py \
  tests/desktop_app/test_controller.py -q
```

Result: `210 passed, 1 warning`.

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
- live-probe can now accept a saved/current measurement definition and return
  per-profile `ab_detection` for setup-preview and measurement frames
- the terminal probe can now load the same Web setup `MeasurementDefinition`
  JSON, or a run artifact directory containing `definition_original.json`, with
  `--definition-file`, so connected-device validation does not depend on
  Swagger or browser-only manual calls
- CLI smoke against `dev_offline_capture` with a current offline-truth
  definition derived from `examples/runtime/artifacts/run-ffe5a57585b5` but
  updated to the locked contour settings (`threshold_mode=adaptive`,
  `ignore_internal_texture=false`) returned `status=ok`,
  `hardware_access=not_attempted`, `frame_source_mode=offline_capture`, and
  both setup-preview and measurement profiles reported `2048x1364` plus
  `ab_detection.status=ok` / `direction_projection_mode=max_chord`
- CLI smoke against the older accepted reference directory
  `examples/runtime/artifacts/run-9953bd601113` correctly failed because its
  historical `definition_original.json` still requests stale contour/A-B
  settings (`ignore_internal_texture=true`, `direction_projection_mode=mask_projection`).
  The failure now returns `frame_access=not_attempted` and
  `hardware_access=not_attempted`, proving the connected-device probe rejects
  stale definitions before reading frames instead of silently reusing old
  semantics
- the operator home page `探测相机` action now attaches the current source-space
  measurement definition to `/api/system/real-offline-alignment/live-probe`
  whenever ROI-local A/B is complete, so the browser-visible probe reports
  pixel, contour, and formal A/B status together
- local Web verification against `dev_offline_capture` posted a current
  measurement definition to `/api/system/real-offline-alignment/live-probe`;
  both setup-preview and measurement profiles returned
  `ab_detection.status=ok`, `selection_mode=directional_contour_max_chord`,
  `direction_projection_mode=max_chord`, and quality about `0.971`
- updated local Web verification against `dev_offline_capture` on
  `http://127.0.0.1:8016/?v=ui-probe-alignment` used the real operator flow:
  freeze preview, draw ROI, wait for automatic A/B, open diagnostics, click
  `探测相机`. The visible page showed source frame `2048x1364`, display frame
  `816x543`, and A/B points on the target contour. The combined probe payload
  included `real_offline_alignment_definition_attached=true` and
  `real_offline_alignment_live_probe.status=ok`; both setup-preview and
  measurement profiles reported `ab_detection.status=ok`,
  `selection_mode=directional_contour_max_chord`,
  `direction_projection_mode=max_chord`, and formal source-space A/B
  `A=(674, 727)`, `B=(1686, 727)`.
- after separating frame source from hardware access, the same operator flow
  returned `frame_source_mode=offline_capture`, `frame_access=attempted`, and
  `hardware_access=not_attempted`, confirming that offline A/B probe success is
  no longer represented as hardware validation.
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
- on `http://127.0.0.1:8017/docs` with `dev_offline_capture`, Swagger UI
  execution of `POST /api/system/real-offline-alignment/live-probe` using stale
  `examples/runtime/artifacts/run-9953bd601113/definition_original.json`
  returned HTTP `200` with response body `status=fail`,
  `hardware_access=not_attempted`, `frame_access=not_attempted`, `profiles=[]`,
  and the real/offline alignment guard detail before any frame access
- targeted desktop-controller regression now confirms
  `DesktopWorkbenchController.save_definition()` rejects a locked-profile stale
  `direction_projection_mode=mask_projection` definition with
  `desktop_save_definition` guard detail
- on the same offline browser session, `/api/system/precheck` returned
  `real_offline_pixel_alignment=ok` with detail confirming
  `origin=(0, 0), size=(2048, 1364)`, `preview_display=816x544`,
  `acquisition=mono8/50000us/12.0dB`,
  `vision=dark_on_light/adaptive`, `internal_texture=False`, and
  formal target-contour `point_a_px/point_b_px`
- on `http://127.0.0.1:8019/` with `dev_offline_capture`, the browser
  viewport showed source frame `2048x1364`, display frame `816x543`, preview
  cadence about `4.6 fps`, and measurement target `10.0 Hz`. After freezing,
  drawing an ROI over the target, and confirming offline temperature settings,
  A/B auto-detection produced visible contour points and a live run started
  successfully; the process curve showed temperature as the x-axis and the run
  was then manually stopped with `采样数=288`.
- on `http://127.0.0.1:8020/` with `dev_offline_capture`, the browser
  viewport again showed source frame `2048x1364`, display frame `816x543`,
  preview cadence about `4.7 fps`, and measurement target `10.0 Hz`. A real
  browser `fetch()` call to `/api/runs/{run_id}/definition/auto` intentionally
  omitted `direction_projection_mode`; the response returned
  `direction_projection_mode=max_chord`,
  `selection_mode=directional_contour_max_chord`, quality about `0.976`, and
  formal A/B source points on the offline target contour. This verifies the
  browser/API default no longer falls back to old `auto/mask_projection`
  semantics.
- on `http://127.0.0.1:8022/` with `dev_offline_capture`, after aligning
  low-level `DirectionalContourConfig` defaults to the offline truth, the
  browser viewport showed source frame `2048x1364`, display frame `816x543`,
  preview cadence about `4.0 fps`, and measurement target `10.0 Hz`. A browser
  `fetch()` call to `/api/runs/{run_id}/definition/auto` returned
  `direction_projection_mode=max_chord`,
  `selection_mode=directional_contour_max_chord`, quality about `0.976`, and
  source A/B points on the target contour.
- screenshot saved to
  `/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/_local/browser_checks/live_probe_no_hardware_swagger_20260526.png`
- updated screenshot saved to
  `/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/_local/browser_checks/live_probe_alignment_contract_20260526.png`
- offline browser screenshots saved by Playwright as
  `offline_truth_ui_defaults_20260526.png` and
  `offline_truth_ignore_texture_unchecked_20260526.png`
- updated stale live-probe guard screenshot saved to
  `/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/_local/browser_checks/live_probe_guard_swagger_20260526.png`
- metric-source guard browser screenshots saved to
  `/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/_local/browser_checks/offline_metric_source_guard_smoke_20260526.png`
  and
  `/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/_local/browser_checks/offline_ab_roi_after_metric_source_guard_20260526.png`
- max-chord default browser screenshot saved to
  `/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/_local/browser_checks/offline_default_max_chord_smoke_20260526.png`
- low-level contour default browser screenshot saved to
  `/Users/lulingfeng/Documents/工作/开发/奥氏体变换/1771/_local/browser_checks/offline_low_level_contour_defaults_20260526.png`

## Remaining Hardware Validation

The goal is not fully complete until real devices are connected and the
following are validated on actual hardware:

1. `dev_lab` startup opens the camera without SDK/device-access error.
2. Either `python -m src.application.real_camera_alignment_probe --profile
   dev_lab --definition-file <definition.json-or-run-artifact-dir>` or
   `POST /api/system/real-offline-alignment/live-probe` passes against the
   connected camera, proving real `setup_preview` and `measurement` frames both
   match `2048 x 1364` plus the configured device ROI metadata and formal A/B
   contour detection.
3. Real live run uses the same local source pixel size and acquisition contract
   as setup preview.
4. Real preset A/B points visually sit on the target contour for representative
   ROI angles.
5. Real live-run A/B points stay on the target contour and do not diverge from
   the offline-validated behavior.
6. LU92XX temperature controller behavior is verified separately with connected
   hardware.
