# Source State Inventory - 2026-05-24

This file turns the current dirty worktree into reviewable buckets. It does not
authorize deletion. It exists so future cleanup can preserve the two active run
states and the current development成果.

## Snapshot

Observed tracked diff size:

```text
63 tracked files changed
about 8735 insertions and 748 deletions
```

Observed largest tracked diffs:

```text
tests/workflow/test_live_run.py
src/webapp/static/app.js
tests/webapp/test_live_run_api.py
src/workflow/live_run.py
src/vision/metric_two_point_distance.py
src/webapp/routes/live_run.py
tests/vision/test_metric_two_point_distance.py
```

This is not ordinary clutter. It is a broad feature/debug worktree and should be
split into intentional commits or checkpoints before any pruning.

## Bucket 1 - Run Mode And Config State

Files:

```text
.gitignore
README.md
configs/dev_lab.local.example.yaml
configs/dev_lab.yaml
configs/dev_lab_camera_mock_temp.yaml
configs/dev_mock.yaml
configs/dev_offline_capture.yaml
pyproject.toml
uv.lock
```

Meaning:

- preserves current startup guidance
- preserves real-device and offline replay profiles
- adds local/runtime ignore rules
- keeps dependency/lock state together with current environment assumptions

Recommended action:

- review as one "runtime profiles and local hygiene" commit
- keep `configs/dev_lab.local.yaml` untracked/local
- keep standard offline capture material on disk but ignored by git

## Bucket 2 - Canonical Requirements And Engineering Plans

Files:

```text
docs/requirements/architecture_lock.md
docs/requirements/home_worker_minimal_cockpit_requirement_v1.md
docs/requirements/home_worker_minimal_cockpit_state_handoff_requirement_v1.md
docs/requirements/live_setup_freeze_roi_tracking_requirement_v1.md
docs/requirements/module_map.md
docs/requirements/requirements_overview.md
docs/plan_eng_review/README.md
docs/plan_eng_review/live_run_plan_lock_v1.md
docs/plan_eng_review/live_setup_contour_direction_migration_plan_v1.md
docs/plan_eng_review/offline_ab_jitter_validation_plan_20260522.md
docs/plan_eng_review/current_run_modes_20260524.md
docs/plan_eng_review/current_validation_state_20260524.md
docs/plan_eng_review/cleanup_inventory_20260524.md
docs/plan_eng_review/source_state_inventory_20260524.md
```

Meaning:

- records the frozen operator flow
- records the real-contour A/B rule
- records offline jitter validation plans
- records current cleanup/run-mode freeze state

Recommended action:

- review as one "requirements and engineering-state freeze" commit
- do not mix future algorithm fixes into this commit

## Bucket 3 - Hardware And Offline Adapters

Files:

```text
src/application/container.py
src/application/device_factory.py
src/application/capture_camera_frames.py
src/camera/__init__.py
src/camera/hik_gige_mvs.py
src/camera/mock_camera.py
src/camera/camera_frame_capture.py
src/camera/offline_capture_camera.py
src/temp/__init__.py
src/temp/lu92xx_modbus_rtu_controller.py
src/temp/mock_temp.py
src/temp/offline_capture_temp.py
tests/application/test_device_factory.py
tests/application/test_capture_camera_frames.py
tests/application/test_container.py
tests/camera/test_hik_gige_mvs.py
tests/camera/test_camera_frame_capture.py
tests/camera/test_offline_capture_camera.py
tests/temp/test_lu92xx_modbus_rtu_controller.py
tests/temp/test_offline_capture_temp.py
```

Meaning:

- adds/extends real camera, real temperature, offline camera, and offline
  temperature paths
- supports recording camera frames into offline material
- supports replaying the current material in the Web workstation

Recommended action:

- review as one adapter-focused commit if tests pass
- hardware claims must stay marked unverified unless tested with connected
  devices in the current environment

## Bucket 4 - Vision And A/B Detection

Files:

```text
src/vision/__init__.py
src/vision/contour_width.py
src/vision/metric_two_point_distance.py
src/vision/contour_direction.py
tests/vision/test_metric_two_point_distance.py
tests/vision/test_contour_direction.py
```

Meaning:

- contains the current ROI-local A/B and direction-aware contour work
- contains the active rule that operator-facing A/B should be real contour
  points, not separate projected/source pairs

Recommended action:

- review as one vision-algorithm commit
- before claiming completion, validate in browser against the standard offline
  material, not only unit tests
- current performance risk remains: contour extraction can make offline live
  replay run at about `3-5 Hz` instead of the configured `10 Hz`

## Bucket 5 - Live Run Workflow And Artifacts

Files:

```text
src/core/contracts.py
src/core/models.py
src/workflow/live_run.py
src/application/live_preview_service.py
src/application/live_run_service.py
src/application/preview_render.py
src/storage/session_artifacts.py
tests/application/test_live_preview_service.py
tests/application/test_live_run_service.py
tests/application/test_preview_render.py
tests/storage/test_live_run_artifacts.py
tests/workflow/test_live_run.py
```

Meaning:

- owns live sampling, telemetry, tracking preview, stop/failure persistence,
  and run artifacts
- preserves the fixed chain `Frame -> ShapeMetric -> SyncPoint -> Curve ->
  Result`

Recommended action:

- review as one live-run workflow commit
- be cautious because this bucket touches shared contracts and persistence

## Bucket 6 - Web Operator UI And API

Files:

```text
src/webapp/app.py
src/webapp/routes/live_run.py
src/webapp/routes/debug.py
src/webapp/schemas.py
src/webapp/static/app.css
src/webapp/static/app.js
src/webapp/templates/index.html
src/webapp/templates/workspace.html
tests/webapp/test_config_loader.py
tests/webapp/test_live_run_api.py
tests/webapp/test_ui_shell.py
tests/webapp/test_workspace_ui.py
```

Meaning:

- owns the browser operator experience
- includes ROI interaction, A/B display, live run controls, real/offline
  endpoints, and analysis navigation behavior

Recommended action:

- review as one Web UI/API commit
- after any future UI-visible edit, use the real browser for visual validation
  before delivery

## Bucket 7 - AFAS / Curve / Analysis Support

Files:

```text
src/curve/afas_postprocessing_dataset.py
src/curve/afas_postprocessing_export.py
src/curve/afas_preprocessing.py
src/curve/mock_afas_curve_playback.py
tests/curve/test_afas_postprocessing_dataset.py
tests/curve/test_afas_preprocessing.py
```

Meaning:

- supports analysis-page and AFAS-style output behavior

Recommended action:

- review separately if behavior changed beyond live-run plumbing
- do not claim full AFAS parity unless all required artifacts and exports are
  verified

## Bucket 8 - Architecture And Desktop Tests

Files:

```text
tests/architecture/test_import_rules.py
tests/architecture/test_model_contracts.py
tests/architecture/test_repository_layout.py
tests/desktop_app/test_controller.py
```

Meaning:

- keeps boundaries and delivery shell expectations aligned with changed source

Recommended action:

- keep near the source buckets they validate, or review as part of a final
  integration commit

## Runtime Data To Preserve But Not Commit

Current large/generated runtime data:

```text
examples/runtime/camera_captures/20260522-183158-dev_lab  about 15G
examples/runtime/artifacts/                                  about 161M
examples/runtime/diagnostics/                                about 202M
examples/runtime/dev_lab_server.log
examples/runtime/dev_offline_capture_server.log
```

Policy:

- preserve current standard offline material on disk
- keep it ignored by git
- do not delete generated run artifacts or diagnostics until the user explicitly
  confirms which evidence is no longer needed

## Suggested Commit Order

When ready to turn this worktree into commits, use this order:

1. requirements and engineering-state freeze
2. runtime profiles and ignore hygiene
3. hardware/offline adapters and capture tool
4. vision A/B contour detection
5. live run workflow/artifact persistence
6. Web operator UI/API
7. AFAS/curve support and architecture follow-through

Stop before committing if any bucket contains unrelated user edits that cannot
be separated safely.
