# Current Requirement Implementation Audit v1

Date: 2026-04-02

Status: AUDIT_SNAPSHOT

## Purpose

This document consolidates the current requirement files under `docs/requirements/` into one implementation-facing audit and checks the current codebase against them.

It answers three practical questions:

1. Which requirement files are still the current source of truth.
2. Which requirement areas are already reflected in code.
3. Which requirement areas are still missing, partially landed, or cannot be honestly verified from the current bench state.

## Scope

Included:

- all files currently under `docs/requirements/`
- current repository code under `src/`
- current repository tests under `tests/`

Excluded from direct status scoring:

- `docs/plan_eng_review/`

Reason:

- `docs/plan_eng_review/` is still authoritative for execution sequencing, but those files are plan/review artifacts rather than requirement files.

## Audit Method

The audit was produced by:

- reading `docs/requirements/requirements_overview.md` to identify the canonical set
- reading the corresponding requirement documents
- inspecting matching implementation files under `src/`
- inspecting matching tests under `tests/`
- running targeted verification commands

Verification commands run during this audit:

```bash
pytest tests/architecture/test_repository_layout.py tests/architecture/test_import_rules.py
pytest tests/webapp/test_ui_shell.py tests/webapp/test_live_run_api.py tests/webapp/test_workspace_ui.py tests/webapp/test_session_api.py tests/curve/test_afas_preprocessing.py tests/curve/test_afas_postprocessing_analysis.py tests/curve/test_afas_postprocessing_export.py tests/temp/test_lu92xx_modbus_rtu_controller.py tests/application/test_live_preview_service.py tests/desktop_app/test_controller.py
```

Observed outcomes:

- feature-oriented suite: `99 passed, 1 failed`
- structure/import guardrail suite: `4 failed, 2 passed`

## Status Legend

- `Meta / Reference`: entrypoint, synthesis, or planning document; not scored as a direct feature implementation contract
- `Historical / Superseded`: kept for lineage, but no longer the live requirement baseline
- `Implemented`: current code and targeted checks support the requirement with no known requirement-level gap found in this audit
- `Partially Implemented`: substantial implementation exists, but one or more requirement-level gaps remain
- `Not Implemented / Drifted`: the current codebase clearly does not conform to the document
- `Undetermined`: code/contracts may exist, but the requirement explicitly needs runtime, bench, or acceptance validation that was not available in this audit

## Executive Summary

Current practical conclusion:

- the active home/setup/workspace/AFAS product line is largely implemented in the current codebase
- LU92XX Modbus RTU support is implemented at config/adapter/test level, but hardware acceptance is still blocked
- desktop migration is clearly underway and usable in mock mode, but not fully closed
- temporal-sampling and web-preview performance requirements cannot be honestly marked done without bench validation
- the biggest clear non-conformance is not the feature lane; it is the older structure freeze. `architecture_lock.md` and `module_map.md` no longer match the current repository shape

Most useful current implementation-facing requirement set:

- `requirements_overview.md`
- `home_worker_minimal_cockpit_requirement_v1.md`
- `home_worker_minimal_cockpit_state_handoff_requirement_v1.md`
- `live_setup_freeze_roi_tracking_requirement_v1.md`
- `home_workspace_shell_requirement_v1.md`
- `home_workspace_information_hierarchy_requirement_v1.md`
- `analysis_studio_afas_alignment_requirement_v1.md`
- `analysis_studio_afas_alignment_state_fallback_requirement_v1.md`
- `afas_full_postprocessing_migration_requirement_v1.md`
- `lu92xx_modbus_rtu_requirement_v1.md`
- `desktop_workstation_migration_requirement_v1.md`

## Consolidated Requirement Audit

### 1. Meta / Reference Documents

#### `docs/requirements/README.md`

- Status: `Meta / Reference`
- Why:
  - directory-level orientation only
- Audit note:
  - not a code-facing product contract

#### `docs/requirements/requirements_overview.md`

- Status: `Meta / Reference`
- Why:
  - canonical entrypoint and authority map
- Audit note:
  - this should remain the first file to read, but it is not scored as a feature requirement itself

#### `docs/requirements/master_control_plan.md`

- Status: `Meta / Reference`
- Why:
  - phase-order planning baseline rather than a direct feature acceptance contract
- Audit note:
  - useful for program history and sequencing, but it is not the best file to decide whether a feature is shipped

#### `docs/requirements/office_hours_requirement_baseline_v1.md`

- Status: `Meta / Reference`
- Why:
  - synthesis baseline that is intentionally refined by later addenda
- Audit note:
  - keep for decision lineage, but use the later requirement addenda to judge implementation status

### 2. Historical / Superseded Documents

#### `docs/requirements/live_setup_roi_ab_window_requirement_v1.md`

- Status: `Historical / Superseded`
- Why:
  - the current operator flow has moved to `live_setup_freeze_roi_tracking_requirement_v1.md`
  - this older split still assumes manual `A/B` and observation-window-first semantics that are no longer current
- Audit note:
  - do not use this file to judge the present home/setup implementation

### 3. Structural / Architecture Baseline

#### `docs/requirements/architecture_lock.md`

- Status: `Not Implemented / Drifted`
- Evidence:
  - `tests/architecture/test_repository_layout.py` currently fails
  - current repo has top-level directories `MvSdkLog` and `测试数据`, which the frozen test does not allow
  - current repo has `src/application` and `src/desktop_app`, which the frozen `ALLOWED_SRC_MODULES` does not allow
- Audit note:
  - this is a real drift, not a guess
  - the codebase has intentionally evolved beyond the older frozen layout

#### `docs/requirements/module_map.md`

- Status: `Not Implemented / Drifted`
- Evidence:
  - `tests/architecture/test_import_rules.py` currently fails
  - `src/curve/mock_afas_curve_playback.py` imports `src.application`, which the frozen dependency map does not allow
  - the current codebase now has a real `application` layer and a `desktop_app` shell, neither of which are modeled in the old map
- Audit note:
  - the document is behind the codebase and should be updated before being used as a guardrail again

### 4. Home / Setup / Handoff Requirements

#### `docs/requirements/home_worker_minimal_cockpit_requirement_v1.md`

- Status: `Partially Implemented`
- Evidence:
  - home shell hooks and copy are validated by `tests/webapp/test_ui_shell.py`
  - current UI exposes freeze, ROI, recompute, current temperature, target temperature, power, save, and workspace handoff
  - old operator-path clutter such as create-run/save-definition/manual point buttons is explicitly absent in the same test
  - corresponding implementation lives in `src/webapp/templates/index.html` and `src/webapp/static/app.js`
- Remaining gaps:
  - this audit did not do a browser-first visual check of the actual first-screen viewport hierarchy
  - diagnostics content may still need design-level validation, even though the DOM/test hooks exist

#### `docs/requirements/home_worker_minimal_cockpit_state_handoff_requirement_v1.md`

- Status: `Partially Implemented`
- Evidence:
  - run state, completion dock, save/analyze actions, and temperature-setting state are exercised by `tests/webapp/test_live_run_api.py`
  - aborted runs now persist partial result/detail/summary artifacts and remain available for save/analyze
  - corresponding logic lives in `src/application/live_run_service.py`, `src/workflow/live_run.py`, and `src/webapp/routes/live_run.py`
- Remaining gaps:
  - this audit verified semantics and persistence, not final UX polish

#### `docs/requirements/live_setup_freeze_roi_tracking_requirement_v1.md`

- Status: `Partially Implemented`
- Evidence:
  - freeze/start/stop preview actions, ROI editing hooks, fresh-frame recompute language, sensitivity semantics, temperature bundle confirmation, and live-run API flow are covered by `tests/webapp/test_ui_shell.py` and `tests/webapp/test_live_run_api.py`
  - fresh-capture behavior is supported by `tests/application/test_live_preview_service.py`
  - implementation is centered in `src/webapp/static/app.js`, `src/webapp/templates/index.html`, `src/webapp/routes/live_run.py`, and `src/application/live_preview_service.py`
- Remaining gaps:
  - current audit only verified the web/mock path
  - no real camera or real controller was attached on this bench during the audit

### 5. Home / Workspace Information and Shell Requirements

#### `docs/requirements/home_workspace_shell_requirement_v1.md`

- Status: `Partially Implemented`
- Evidence:
  - separate home and workspace routes exist
  - deterministic workspace linking and result handoff are exercised in `tests/webapp/test_ui_shell.py`, `tests/webapp/test_workspace_ui.py`, and `tests/webapp/test_session_api.py`
  - workspace route and session-targeted navigation exist in `src/webapp/routes/ui.py`, `src/webapp/routes/session.py`, and `src/webapp/templates/workspace.html`
- Remaining gaps:
  - this audit verified route/DOM/state behavior, not a full visual shell review

#### `docs/requirements/home_workspace_information_hierarchy_requirement_v1.md`

- Status: `Partially Implemented`
- Evidence:
  - workspace first-screen AFAS/result/analysis structure is strongly reflected in `tests/webapp/test_workspace_ui.py`
  - session import, replay detail, AFAS analysis, export, and adjustment flows exist in `tests/webapp/test_session_api.py` and `tests/webapp/test_adjustment_api.py`
- Remaining gaps:
  - first-screen hierarchy and drawer-level emphasis were not browser-audited in this pass

### 6. Analysis Studio / AFAS Requirements

#### `docs/requirements/analysis_studio_afas_alignment_requirement_v1.md`

- Status: `Partially Implemented`
- Evidence:
  - AFAS-style analysis panel, grouped parameters, result surface, export buttons, channel selection, and replay context hooks are validated in `tests/webapp/test_workspace_ui.py`
  - analysis route behavior exists in `tests/webapp/test_session_api.py`
  - current implementation lives in `src/webapp/templates/workspace.html`, `src/webapp/static/app.js`, and `src/webapp/routes/session.py`
- Remaining gaps:
  - this audit did not perform a visual design review against the desired AFAS hierarchy

#### `docs/requirements/analysis_studio_afas_alignment_state_fallback_requirement_v1.md`

- Status: `Partially Implemented`
- Evidence:
  - explicit fallback behavior for `afas_available=0`, missing detail, and imported AFAS sessions is covered by `tests/webapp/test_workspace_ui.py`
  - AFAS analysis route supports auto-load style analysis and fallback error responses in `tests/webapp/test_session_api.py`
- Remaining gaps:
  - degradation behavior is covered at route/DOM level, but not yet fully audited as a polished UX state machine

#### `docs/requirements/afas_full_postprocessing_migration_requirement_v1.md`

- Status: `Partially Implemented`
- Evidence:
  - AFAS preprocessing exists and is tested in `tests/curve/test_afas_preprocessing.py`
  - tangent analysis exists and is tested in `tests/curve/test_afas_postprocessing_analysis.py`
  - dataset contract exists and is tested in `tests/curve/test_afas_postprocessing_dataset.py`
  - export PNG/XLSX exists and is tested in `tests/curve/test_afas_postprocessing_export.py`
  - representative legacy parity fixture coverage exists in `tests/curve/test_afas_fixture_parity.py`
  - workspace/API integration exists in `tests/webapp/test_session_api.py` and `tests/webapp/test_workspace_ui.py`
- Remaining gaps:
  - the repo shows strong AFAS capability, but this audit did not certify full product-level parity across every legacy workflow or every dataset family

### 7. Temperature Controller Requirement

#### `docs/requirements/lu92xx_modbus_rtu_requirement_v1.md`

- Status: `Partially Implemented`
- Evidence:
  - LU92XX adapter exists in `src/temp/lu92xx_modbus_rtu_controller.py`
  - runtime config supports LU92XX backend, serial config, and register maps in `src/application/runtime_config.py` and `tests/webapp/test_config_loader.py`
  - adapter behavior is tested in `tests/temp/test_lu92xx_modbus_rtu_controller.py`
  - read target, write target, start output, stop output, CRC validation, exception handling, and `258/264` process-value address handling are all covered in tests
- Remaining gaps:
  - requirement-level hardware acceptance is not closed
  - there was no real LU92XX device attached during this audit
  - the document itself still contains remaining-unknown and hardware-phase done criteria that cannot be marked complete yet

### 8. Preview / Temporal-Sampling / Bench Performance Requirements

#### `docs/requirements/web_preview_18fps_requirement_v1.md`

- Status: `Undetermined`
- Evidence:
  - preview pipeline code exists in `src/application/live_preview_service.py` and `src/application/preview_render.py`
  - preview rendering and preview-state tracking are tested in `tests/application/test_preview_render.py` and `tests/application/test_live_preview_service.py`
- Why still undetermined:
  - the requirement is an acceptance gate about actual web preview viability
  - this audit did not measure real browser preview FPS on the intended final environment

#### `docs/requirements/live_capture_temporal_sampling_requirement_v1.md`

- Status: `Undetermined`
- Evidence:
  - rate concepts are present in core models and tested in `tests/architecture/test_model_contracts.py`
  - runtime config exposes `preview_target_fps`, `measurement_target_hz`, and `artifact_capture_hz`, as shown by `tests/webapp/test_config_loader.py`
  - preview service exposes `preview_display_fps` in `src/application/live_preview_service.py`
- Why still undetermined:
  - the requirement explicitly demands real-bench validation for setup preview, 50 Hz measurement, and 100 Hz stretch behavior
  - no real device chain was attached during this audit

### 9. Desktop Migration Requirement

#### `docs/requirements/desktop_workstation_migration_requirement_v1.md`

- Status: `Partially Implemented`
- Evidence:
  - desktop controller, preview canvas, main window, and CLI entrypoint exist under `src/desktop_app/`
  - desktop smoke and preview benchmark tests exist in `tests/desktop_app/test_main.py`, `tests/desktop_app/test_controller.py`, and `tests/desktop_app/test_window.py`
  - shared application layer exists in `src/application/container.py`, matching the document’s direction
- Current concrete gap:
  - the targeted audit run found a failing test in `tests/desktop_app/test_controller.py::test_desktop_workbench_controller_runs_minimum_mock_flow`
  - the failure shows the desktop controller still assumes `save_definition()` alone reaches `run_ready`, while the current web flow now requires bundled temperature confirmation first
- Audit note:
  - this is clear evidence that desktop migration is real, but not yet fully aligned with the newest live-run/home setup semantics

## Consolidated Buckets

### Implemented

No requirement file was marked fully `Implemented` in this audit.

Reason:

- the active product lanes are mostly present, but each still has either a bench-validation gap, a UX/audit gap, or a document/code drift gap that prevents an honest full-complete mark

### Partially Implemented

- `home_worker_minimal_cockpit_requirement_v1.md`
- `home_worker_minimal_cockpit_state_handoff_requirement_v1.md`
- `live_setup_freeze_roi_tracking_requirement_v1.md`
- `home_workspace_shell_requirement_v1.md`
- `home_workspace_information_hierarchy_requirement_v1.md`
- `analysis_studio_afas_alignment_requirement_v1.md`
- `analysis_studio_afas_alignment_state_fallback_requirement_v1.md`
- `afas_full_postprocessing_migration_requirement_v1.md`
- `lu92xx_modbus_rtu_requirement_v1.md`
- `desktop_workstation_migration_requirement_v1.md`

### Not Implemented / Drifted

- `architecture_lock.md`
- `module_map.md`

### Undetermined

- `web_preview_18fps_requirement_v1.md`
- `live_capture_temporal_sampling_requirement_v1.md`

### Historical / Superseded

- `live_setup_roi_ab_window_requirement_v1.md`

### Meta / Reference

- `README.md`
- `requirements_overview.md`
- `master_control_plan.md`
- `office_hours_requirement_baseline_v1.md`

## Practical Reading Order After This Audit

If the next goal is ongoing implementation rather than historical review, read in this order:

1. `docs/requirements/requirements_overview.md`
2. `docs/requirements/live_setup_freeze_roi_tracking_requirement_v1.md`
3. `docs/requirements/home_worker_minimal_cockpit_requirement_v1.md`
4. `docs/requirements/home_worker_minimal_cockpit_state_handoff_requirement_v1.md`
5. `docs/requirements/home_workspace_shell_requirement_v1.md`
6. `docs/requirements/home_workspace_information_hierarchy_requirement_v1.md`
7. `docs/requirements/analysis_studio_afas_alignment_requirement_v1.md`
8. `docs/requirements/analysis_studio_afas_alignment_state_fallback_requirement_v1.md`
9. `docs/requirements/afas_full_postprocessing_migration_requirement_v1.md`
10. `docs/requirements/lu92xx_modbus_rtu_requirement_v1.md`
11. `docs/requirements/desktop_workstation_migration_requirement_v1.md`

## Recommended Next Maintenance Action

The next document-maintenance priority should be:

1. update `architecture_lock.md` and `module_map.md` to match the now-real `application` and `desktop_app` layers
2. reconcile desktop live-run gating with the newer temperature-confirmation requirement
3. keep preview/temporal-sampling requirements marked bench-gated until real devices are attached
