# Offline A/B Jitter Validation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:verification-before-completion before claiming the jitter issue is fixed or acceptable. Browser checks should use the Browser skill against `http://127.0.0.1:8002/`.

**Goal:** Prove, with measurable evidence, whether offline simulated material still shows abnormal A/B jumping in the actual Web live-test path.

**Architecture:** Validate three layers separately so a pass in one layer cannot hide a failure in another: user-recording pixel evidence, accelerated offline algorithm replay, and Web live-run/browser overlay replay. Treat the offline capture directory as immutable input and write only derived diagnostics under `examples/runtime/diagnostics/`.

**Tech Stack:** Python 3.11, NumPy, OpenCV/Pillow where available, FastAPI live-run API, Browser skill / Playwright surface.

---

### Task 1: Quantify User Recording At 10Hz

**Files:**
- Read only: `/Users/lulingfeng/Desktop/录屏2026-05-22 11.08.01.mov`
- Write derived output: `examples/runtime/diagnostics/ab_jitter_20260522_user_recording_10hz.json`

- [ ] Extract or reuse 10Hz frames from the recording:

```bash
mkdir -p examples/runtime/diagnostics/screen_20260522_110801_10hz
ffmpeg -hide_banner -loglevel error -y \
  -i "/Users/lulingfeng/Desktop/录屏2026-05-22 11.08.01.mov" \
  -vf fps=10 \
  examples/runtime/diagnostics/screen_20260522_110801_10hz/frame_%04d.png
```

- [ ] Detect visible A/B overlay circles in each frame and report `Ax/Ay/Bx/By/span/max_step` ranges.

**Pass/Fail interpretation:** This task is diagnostic only. It must identify the original visible symptom and provide a baseline for comparison.

### Task 2: Create A Fresh Web Definition From Offline Material

**Files:**
- Read only: `configs/dev_offline_capture.yaml`
- Read only: `examples/runtime/camera_captures/20260522-183158-dev_lab/`
- Runtime artifacts: `examples/runtime/artifacts/run-*/`

- [ ] Confirm the offline Web service is healthy:

```bash
curl -s http://127.0.0.1:8002/health
```

- [ ] Create a fresh run through the Web API, freeze a frame, auto-detect A/B, save the definition, confirm temperature, start a short live run, and stop it.

**Pass criteria:** The run must use `profile=dev_offline_capture`; the auto-detected source A/B must be produced by the current app, not manually typed; the short live run must produce telemetry and persist a partial artifact bundle.

### Task 3: Accelerated Full Offline Replay

**Files:**
- Read only: `examples/runtime/camera_captures/20260522-183158-dev_lab/manifest.json`
- Read only: `examples/runtime/camera_captures/20260522-183158-dev_lab/frames/*.npy`
- Read only: fresh run artifact `definition_effective_local.json`
- Read only: fresh run artifact `measurement_capture_plan.json`
- Write derived output: `examples/runtime/diagnostics/ab_jitter_20260522_full_offline_replay.json`

- [ ] Replay every offline frame through `PriorTrackingMetricSource` using the fresh Web-created definition and the actual measurement crop.

**Pass criteria:**
- `bad_quality_ratio <= 0.01`
- `hold_ratio <= 0.01`
- `max_y_step_px <= 1`
- `point_a_y_range_px <= 1`
- `point_b_y_range_px <= 1`
- No `invalidated` tracking state.

### Task 4: Browser Visible Overlay Sampling

**Files:**
- Write derived output: `examples/runtime/diagnostics/ab_jitter_20260522_browser_overlay_samples.json`
- Optional screenshot: `examples/runtime/diagnostics/ab_jitter_20260522_browser_overlay.png`

- [ ] Open `http://127.0.0.1:8002/` in the in-app browser.
- [ ] Drive the visible app into a live run using offline material, or attach to the fresh short live run from Task 2.
- [ ] Sample at about 10Hz for at least 10 seconds:
  - latest telemetry A/B preview coordinates
  - visible SVG overlay A/B coordinates
  - current displayed temperature

**Pass criteria:**
- `sample_count >= 80`
- telemetry preview `max_y_step_px <= 1`
- visible SVG overlay `max_y_step_px <= 1`
- no sample has `tracking_quality < 0.75`

### Task 5: Report Only Evidence

- [ ] Re-run targeted tests:

```bash
python -m pytest tests/vision/test_metric_two_point_distance.py -q
python -m pytest tests/workflow/test_live_run.py -q
python -m pytest tests/application/test_live_run_service.py -q
```

- [ ] Report exact command outputs, measured ranges, generated diagnostic files, and any remaining gaps. Do not claim the issue is fixed unless Tasks 2-5 meet the pass criteria.
