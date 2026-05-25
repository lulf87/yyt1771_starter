# Real/Offline Prod Win Alignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep the Windows production Web profile aligned with the accepted offline material so preset pixels, live-run pixels, contour detection, and formal A/B point selection cannot drift from the offline truth source.

**Architecture:** The offline material remains the truth source. `prod_win` shares the same local source size and runtime pixel guard as `dev_lab`, while precheck and audit commands prove alignment without opening camera or temperature hardware.

**Tech Stack:** Python 3.11, FastAPI Web workstation, pytest, Hik GigE/MVS profile configuration, offline grayscale `.npy` material replay.

---

### Task 1: Lock `prod_win` Source Pixels And Run Guards

**Files:**
- Modify: `configs/prod_win.yaml`
- Modify: `src/application/frame_pixel_contract.py`
- Modify: `src/application/real_offline_alignment.py`
- Modify: `src/workflow/precheck.py`
- Modify: `src/webapp/routes/profile.py`

- [x] **Step 1: Configure matching preset/live source pixels**

Set both `camera.setup_preview.device_roi` and `camera.measurement.device_roi` to:

```yaml
x: 512
y: 342
width: 2048
height: 1364
```

- [x] **Step 2: Configure matching display and run guards**

Set:

```yaml
preview_display_max_width: 816
preview_display_max_height: 544
manual_stop_max_samples: 0
stop_on_invalid_tracking: false
invalid_tracking_grace_samples: 5
```

- [x] **Step 3: Include `prod_win` in runtime pixel guard profiles**

`validate_frame_pixel_contract()` must reject any `prod_win` preset/live frame whose actual image size is not `2048 x 1364`.

If a frame includes applied `device_roi` metadata, the runtime guard must also
reject any preset/live frame whose applied ROI origin or size differs from the
locked profile ROI.

- [x] **Step 4: Include `prod_win` in no-device precheck alignment**

`real_offline_pixel_alignment` must report `ok` only when `prod_win` setup/live pixels and preview display bounds match the offline truth contract.

- [x] **Step 5: Make the browser audit endpoint profile-aware**

When the Web service is running under `prod_win`, `GET /api/system/real-offline-alignment` must audit `prod_win` against `dev_offline_capture`, not silently report the default `dev_lab` audit.

- [x] **Step 6: Add all-profile no-hardware audit helper**

`run_all_alignment_audits()` must check `dev_lab`, `dev_lab_camera_mock_temp`, and `prod_win` against the accepted offline material in one command-level call.

### Task 2: Add Regression Coverage

**Files:**
- Modify: `tests/webapp/test_config_loader.py`
- Modify: `tests/workflow/test_precheck.py`
- Modify: `tests/webapp/test_precheck_api.py`
- Modify: `tests/application/test_real_offline_alignment.py`

- [x] **Step 1: Verify RED**

Run:

```bash
../_local/yyt1771_starter/.conda-desktop-x86/bin/python3.11 -m pytest tests/webapp/test_config_loader.py::test_load_runtime_config_reads_prod_camera_contract -q
```

Expected before test update: FAIL because the test still expects the old `prod_win` 640 x 480 / 5 Hz / 10000-sample contract.

- [x] **Step 2: Update config-loader assertions**

Assert `prod_win` uses `2048 x 1364` setup/live ROI, `816 x 544` display bounds, 20 Hz profile cadence, no fixed manual-stop sample cap, and `stop_on_invalid_tracking: false`.

- [x] **Step 3: Update precheck assertions**

Assert `prod_win` reports `real_offline_pixel_alignment: ok` without live device access when its ROI/display contract matches the offline truth source.

- [x] **Step 4: Update audit assertions**

Assert `run_alignment_audit(real_profile="prod_win")` returns `ok`, checks all 12 angles, and reports `hardware_access: not_attempted`.

- [x] **Step 5: Update browser API assertions**

Assert the real/offline alignment API uses the current `prod_win` service profile and still returns `hardware_access: not_attempted`.

- [x] **Step 6: Update all-profile audit assertions**

Assert the all-profile helper returns `ok`, covers all locked real profiles, and checks all 12 ROI angles per profile.

### Task 3: Update Operator Documentation

**Files:**
- Modify: `docs/plan_eng_review/current_run_modes_20260524.md`
- Modify: `docs/plan_eng_review/web_on_windows_migration_status_20260525.md`
- Modify: `docs/plan_eng_review/real_offline_alignment_status_20260525.md`

- [x] **Step 1: Remove stale `prod_win` skeleton wording**

Document `prod_win` as a tracked Windows production baseline that is source-pixel aligned with the offline truth material, while still not hardware-verified.

- [x] **Step 2: Preserve validation boundary**

State that no real camera or LU92XX validation is proven while hardware is disconnected.

### Task 4: Verify And Commit

**Files:**
- Verify changed source, tests, and docs

- [x] **Step 1: Run targeted tests**

```bash
../_local/yyt1771_starter/.conda-desktop-x86/bin/python3.11 -m pytest tests/webapp/test_config_loader.py tests/workflow/test_precheck.py tests/webapp/test_precheck_api.py tests/application/test_real_offline_alignment.py -q
```

- [x] **Step 2: Run broader checks**

```bash
../_local/yyt1771_starter/.conda-desktop-x86/bin/python3.11 -m compileall src tests
node --check src/webapp/static/app.js
git diff --check
```

- [x] **Step 3: Run browser/API precheck**

Start:

```bash
../_local/yyt1771_starter/.conda-desktop-x86/bin/python3.11 -m src.webapp.serve --profile prod_win --port 8013
```

Open:

```text
http://127.0.0.1:8013/api/system/precheck
```

Expected: `real_offline_pixel_alignment` is `ok`; hardware access is not attempted; camera identity may still fail until local hardware identity is configured.

- [x] **Step 4: Commit**

```bash
git add configs/prod_win.yaml src/application/frame_pixel_contract.py src/application/real_offline_alignment.py src/workflow/precheck.py src/webapp/routes/profile.py tests/webapp/test_config_loader.py tests/workflow/test_precheck.py tests/webapp/test_precheck_api.py tests/application/test_real_offline_alignment.py docs/plan_eng_review/current_run_modes_20260524.md docs/plan_eng_review/web_on_windows_migration_status_20260525.md docs/plan_eng_review/real_offline_alignment_status_20260525.md docs/plan_eng_review/real_offline_prod_win_alignment_plan_20260526.md
git commit -m "Lock prod win to offline pixel contract"
```
