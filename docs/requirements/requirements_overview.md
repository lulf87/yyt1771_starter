# Requirements Overview

This file is the single canonical entry point for project requirements,
structure rules, and implementation references.

## 1. Authority Rule

From this point forward, all project changes and requirement updates must use
only the authoritative files under these two directories:

- `docs/requirements/`
- `docs/plan_eng_review/`

The `docs/` root should stay minimal, with current authoritative material
living only in those two directories.

That means:

- if a new feature needs a new requirement, land it in `docs/requirements/`
  first
- if a new implementation plan or status board is needed, land it in
  `docs/plan_eng_review/` first

## 2. Project Goal

### 2026-05-25 `mac-finish` Delivery Refreeze

As of the `mac-finish` checkpoint, the current operator-facing delivery shell is
the Web workstation.

Windows migration means validating this Web workstation on Windows first. The
older PySide6 / Qt `desktop_app` route remains in the repository only as paused
historical / fallback material, and must not be treated as the active migration
path unless the user explicitly reactivates it.

For the current Windows migration state, read:

- [current_run_modes_20260524.md](../plan_eng_review/current_run_modes_20260524.md)
- [web_on_windows_migration_status_20260525.md](../plan_eng_review/web_on_windows_migration_status_20260525.md)

Build a YY/T 1771 visual-analysis workstation that:

- starts from an offline minimum chain
- keeps module boundaries stable
- has already proven a browser-based workstation baseline
- uses the Web workstation as the current `mac-finish` delivery baseline
- runs with Mac-based development and Windows-based production validation needs

The fixed system direction is:

```text
webapp -> Application Layer -> Workflow / Storage / Report
```

`desktop_app` is retained as a paused legacy adapter, not as the current
operator-facing shell.

The fixed analysis chain is:

```text
Frame -> ShapeMetric -> SyncPoint -> Curve -> Result
```

Primary goal reference:

- [master_control_plan.md](./master_control_plan.md)
- [office_hours_requirement_baseline_v1.md](./office_hours_requirement_baseline_v1.md)

## 3. Structural Requirements

These files define the project structure and must be treated as the baseline
before any feature work:

- [architecture_lock.md](./architecture_lock.md)
- [module_map.md](./module_map.md)

Current top-level structure:

```text
yyt1771_starter/
  configs/
  docs/
  examples/
  src/
  tests/
```

Top-level explanation:

- `configs/`: runtime profile and example configuration files
- `docs/`: canonical requirement docs and eng-review docs
- `examples/`: replay samples, offline demos, and dev runtime outputs
- `src/`: application source code
- `tests/`: mirrored test layout by module

## 4. Canonical Requirement Set

### A. Product / Program Baseline

- [master_control_plan.md](./master_control_plan.md)
- [office_hours_requirement_baseline_v1.md](./office_hours_requirement_baseline_v1.md)

Use these first when you need:

- overall project direction
- phase order
- current forbidden work
- the original browser workstation product framing
- the current Web workstation delivery direction
- the paused legacy status of the desktop-delivery migration direction
- frozen live-setup interaction semantics
- the current screen-role split between `Launch & Control Cockpit` on home and `Analysis Studio` in workspace
- the current visual-system convergence direction for home and workspace

### B. Architecture / Boundary Baseline

- [architecture_lock.md](./architecture_lock.md)
- [module_map.md](./module_map.md)

Use these when you need:

- directory rules
- module ownership
- import boundaries
- test layout constraints

### C. Device / Requirement Baseline

- [home_workspace_shell_requirement_v1.md](./home_workspace_shell_requirement_v1.md)
- [home_workspace_information_hierarchy_requirement_v1.md](./home_workspace_information_hierarchy_requirement_v1.md)
- [analysis_studio_afas_alignment_requirement_v1.md](./analysis_studio_afas_alignment_requirement_v1.md)
- [analysis_studio_afas_alignment_state_fallback_requirement_v1.md](./analysis_studio_afas_alignment_state_fallback_requirement_v1.md)
- [home_worker_minimal_cockpit_requirement_v1.md](./home_worker_minimal_cockpit_requirement_v1.md)
- [home_worker_minimal_cockpit_state_handoff_requirement_v1.md](./home_worker_minimal_cockpit_state_handoff_requirement_v1.md)
- [live_setup_freeze_roi_tracking_requirement_v1.md](./live_setup_freeze_roi_tracking_requirement_v1.md)
- [live_setup_roi_ab_window_requirement_v1.md](./live_setup_roi_ab_window_requirement_v1.md)
- [web_preview_18fps_requirement_v1.md](./web_preview_18fps_requirement_v1.md)
- [desktop_workstation_migration_requirement_v1.md](./desktop_workstation_migration_requirement_v1.md) paused legacy / fallback reference only
- [afas_full_postprocessing_migration_requirement_v1.md](./afas_full_postprocessing_migration_requirement_v1.md)
- [lu92xx_modbus_rtu_requirement_v1.md](./lu92xx_modbus_rtu_requirement_v1.md)
- [live_capture_temporal_sampling_requirement_v1.md](./live_capture_temporal_sampling_requirement_v1.md)

Use this when you need:

- the locked home/workspace shell split between `Launch & Control Cockpit` and `Analysis Studio`
- the locked distinction between `default visible`, `on-demand reveal`, and `engineering mode` for home/workspace content
- the locked rule that workspace default-visible analysis content should align to AFAS’s `channel -> parameters -> overview -> single-channel analysis -> results -> export` model
- the locked AFAS-style trigger semantics that workspace analysis should auto-load and auto-refresh on committed channel / parameter changes rather than require a default-primary rerun step
- the locked fallback behavior for `afas_available=0`, single-channel datasets, and summary-only / no-detail sessions
- the locked replay placement as a compact context strip / foldout above the AFAS analysis area
- the locked requirement that first-pass AFAS-style workspace refactors preserve existing DOM / JS / test anchors
- the locked rule that workspace process-heavy content such as rail, sticky summary, version, adjustment, API/provenance, and future controls must leave the default first screen
- the locked worker-facing simplification of home into a preview-led minimal operator cockpit
- the locked removal of shell hero copy, journey copy, `当前任务`, and `系统 / 配置 / 模式` cards from the default operator viewport
- the locked rule that home completion state should prefer `保存数据 / 进入分析` rather than a summary card
- the locked naming changes around `ROI 框选` and `查看ROI参数`
- the locked rule that `ROI 角度` must move into the ROI-parameter reveal
- the locked rule that manual `A/B` is no longer part of the current home operator flow
- the locked dual-button preview lifecycle of `Freeze / 解除冻结`
- the locked rule that every `A/B` recompute must first capture a fresh frame
- the locked directional meaning of `Sensitivity` (`大 = 更容易连成一体`, `小 = 更严格地区分目标与空白`)
- the locked rule that temperature confirmation now means `目标温度 + 手动方式 + 温度功率` as one bundled setting
- the locked rule that the worker-minimal home still keeps a tiny `ready` signal
- the locked rule that the completion dock must still expose the exact target session for `进入分析`
- the locked rule that `保存数据` is an operator-facing export / confirm action over already-persisted results rather than a new persistence contract
- the locked post-temperature-confirmation state machine for target/power edits, ROI / sensitivity recompute, and `Start` enablement
- the locked rule that home defaults to a single operator path rather than a feature gallery
- the locked rule that workspace first screen is AFAS-analysis-first, with replay retained only as lightweight session context rather than the default hero
- the locked cross-surface journey from device-ready through AFAS result/export
- the locked semantic upgrade of the AFAS result card into a first-screen answer surface
- the deterministic selection rule for `Compact Result -> Open Workspace`
- the locked rule that `observation_window` is not part of the current home cockpit operator path
- the locked escalation rule for when `A-B` status must become prominent for operator diagnostic review, without reintroducing manual point placement on home
- the first-pass DOM / API / test-anchor guardrails for home/workspace shell refactors
- the current operator-facing live setup workflow after the shift to `auto-live-preview -> Freeze -> rotated ROI -> ROI-local A-B -> live ROI tracking`
- the locked decision that the old `Create Live Run / Fetch Preview / Start Live Preview` buttons are no longer part of the operator workflow
- the locked decision that `Draw Window / Rotate Window` are removed from the current operator setup flow
- the locked rule that ROI is now both the setup search region and the live deformation capture region
- the locked rule that auto-detected `A-B` must be found along the ROI-local horizontal axis, not world-axis horizontal/vertical and not arbitrary diagonals
- the locked rule that formal `A-B` points are the target object's real contour/boundary points, not projected/source-vs-axis duplicate points, and that live curves, telemetry, and analysis must all derive from that same point pair
- the locked rule that accepted offline material is the truth source for real profiles: setup/live source pixels, acquisition parameters, Web display bounds, contour detection settings, live tracking policy, and formal `point_a_px / point_b_px` semantics must stay aligned before real hardware validation is claimed
- the locked rule that any committed ROI geometry or sensitivity change must trigger recapture plus point recomputation
- the locked trigger granularity that recapture + recompute fires on committed edits or explicit recompute, not on every intermediate drag sample
- the locked requirement for a rotation handle on ROI, a visible ROI angle field, a current-temperature display, a bundled temperature-settings confirm action, and live A/B refresh during test
- the locked rule that `ROI` is the primary search region for auto detect
- the locked rule that `A-B` must be defined before `observation_window` becomes semantically meaningful
- the locked rule that `Auto Detect Points` must search inside ROI and return a horizontal-or-vertical dominant point pair, not a pre-window axis guess or an arbitrary diagonal diameter
- the locked rule that `observation_window` is a post-A/B live-run observation aperture rather than an auto-detect prerequisite
- the locked rule that downstream observation direction is constrained to the window's `long_axis` or `short_axis`
- the locked decision that Web is the current `mac-finish` delivery shell
- the locked interpretation of “bigger and brighter Web preview” as a requirement rather than an implementation suggestion
- the locked rule that desktop migration is paused unless explicitly reactivated
- the locked decision to keep the same workflow while migrating the Web workstation to Windows
- the locked decision to keep the migration inside the current repository
- the historical acceptance gate for desktop preview display performance on Windows, retained only for paused desktop-reference context
- the locked requirement that “AFAS parity” means full post-data capability parity, not just lightweight `As / Af / AF95` computation
- the locked requirement to migrate AFAS preprocessing, parameterized tangent analysis, plotting, result-panel, and export capabilities if full AFAS postprocessing parity is claimed
- the locked expectation that full AFAS parity includes persisted postprocessing artifacts, not just transient API responses
- the locked LU92XX controller requirement shape
- verified Modbus RTU assumptions
- current hardware-side blockers that are allowed vs. not allowed
- the locked interpretation of preview fps vs. measurement sample rate
- the 50 Hz baseline / 100 Hz stretch requirement for synchronized measurement

### D. Engineering Review Baseline

The canonical engineering-review files now live in the sibling
`docs/plan_eng_review/` directory:

- [afas_full_postprocessing_migration_plan_lock_v1.md](../plan_eng_review/afas_full_postprocessing_migration_plan_lock_v1.md)
- [live_setup_freeze_roi_tracking_plan_lock_v1.md](../plan_eng_review/live_setup_freeze_roi_tracking_plan_lock_v1.md)
- [live_setup_roi_ab_window_plan_lock_v1.md](../plan_eng_review/live_setup_roi_ab_window_plan_lock_v1.md)
- [web_preview_18fps_plan_lock_v1.md](../plan_eng_review/web_preview_18fps_plan_lock_v1.md)
- [web_on_windows_migration_status_20260525.md](../plan_eng_review/web_on_windows_migration_status_20260525.md)
- [desktop_workstation_migration_plan_lock_v1.md](../plan_eng_review/desktop_workstation_migration_plan_lock_v1.md) paused legacy / fallback reference only
- [desktop_workstation_migration_status_v1.md](../plan_eng_review/desktop_workstation_migration_status_v1.md) paused legacy / fallback reference only
- [live_capture_temporal_sampling_plan_lock_v1.md](../plan_eng_review/live_capture_temporal_sampling_plan_lock_v1.md)
- [live_run_plan_lock_v1.md](../plan_eng_review/live_run_plan_lock_v1.md)
- [live_run_execution_plan_v1.md](../plan_eng_review/live_run_execution_plan_v1.md)
- [live_run_implementation_breakdown_v1.md](../plan_eng_review/live_run_implementation_breakdown_v1.md)
- [live_run_task_status_v1.md](../plan_eng_review/live_run_task_status_v1.md)
- [real_offline_alignment_goal_audit_20260526.md](../plan_eng_review/real_offline_alignment_goal_audit_20260526.md)
- [live_run_test_plan_v1.md](../plan_eng_review/live_run_test_plan_v1.md)
- [live_run_bench_validation_v1.md](../plan_eng_review/live_run_bench_validation_v1.md)

Use these when you need:

- the locked implementation plan for full AFAS postprocessing parity beyond the current lightweight live `afas.py` path
- the locked implementation plan for the new operator workflow after the shift to `auto-live-preview -> Freeze -> rotated ROI -> ROI-local A-B -> live ROI tracking`
- the engineering decision to keep the existing run/session backend but demote the old preview buttons to internal implementation detail
- the phased implementation order for ROI angle, sensitivity, current-temperature display, temperature-settings confirmation, and live A/B updates
- the locked implementation plan for `ROI -> A-B -> observation window -> observation_axis`
- the engineering decision to split ROI-first point detection from post-A/B window-bounded tracking
- the locked implementation decision that Web is the current `mac-finish` delivery shell
- the Web-on-Windows migration state
- the paused D1-D7 desktop migration progress board, when historical desktop context is explicitly needed
- the locked implementation plan for `50 Hz` measurement and preview / measurement split
- the current locked implementation plan
- task breakdown and dependency order
- current verified status vs. remaining drift
- test strategy and validation boundaries

## 5. Legacy Docs Policy

The `docs/` root should stay minimal and should not accumulate duplicate or
legacy task files. Current work should start from:

- `docs/requirements/`
- `docs/plan_eng_review/`

## 6. Where To Read First

Recommended reading order for current work:

1. [master_control_plan.md](./master_control_plan.md)
2. [office_hours_requirement_baseline_v1.md](./office_hours_requirement_baseline_v1.md)
3. [home_workspace_shell_requirement_v1.md](./home_workspace_shell_requirement_v1.md) if touching home/workspace role split, `Compact Result` routing, homepage A/B prominence rules, or first-pass shell refactor guardrails
4. [home_workspace_information_hierarchy_requirement_v1.md](./home_workspace_information_hierarchy_requirement_v1.md) if touching default-visible vs. on-demand vs. engineering content, current-task home layout, workspace first-screen focus, cross-surface journey, or AFAS result-card semantics
5. [analysis_studio_afas_alignment_requirement_v1.md](./analysis_studio_afas_alignment_requirement_v1.md) if touching workspace default-visible analysis content, AFAS-style parameter/result/export organization, replay demotion, or the removal of process-heavy information from the default first screen
6. [analysis_studio_afas_alignment_state_fallback_requirement_v1.md](./analysis_studio_afas_alignment_state_fallback_requirement_v1.md) if touching AFAS auto-analysis trigger semantics, `afas_available=0` / single-channel / summary-only fallback behavior, replay context placement, or workspace compatibility guardrails during the AFAS-style refactor
7. [home_worker_minimal_cockpit_requirement_v1.md](./home_worker_minimal_cockpit_requirement_v1.md) if touching worker-facing home simplification, shell text removal, hidden diagnostics, `保存数据 / 进入分析` completion actions, `Save Definition` removal, `ROI 框选 / 查看ROI参数` naming, removal of manual `A/B`, or the visible temperature-setting bundle
8. [home_worker_minimal_cockpit_state_handoff_requirement_v1.md](./home_worker_minimal_cockpit_state_handoff_requirement_v1.md) if touching the tiny `ready` cue, completion-dock target visibility, `保存数据` semantics, or the post-temperature-confirmation start-enable state machine
9. [live_setup_freeze_roi_tracking_requirement_v1.md](./live_setup_freeze_roi_tracking_requirement_v1.md) if touching launch flow, `Freeze / 解除冻结`, ROI editing, ROI rotation, ROI-local point detection, fresh-frame `A/B` recompute, sensitivity meaning, current temperature display, bundled temperature confirmation, or live A/B tracking
10. [live_setup_roi_ab_window_requirement_v1.md](./live_setup_roi_ab_window_requirement_v1.md) only when you need the older `ROI -> A-B -> observation window` split for historical context or for identifying what the newer live setup requirement superseded
11. [web_preview_18fps_requirement_v1.md](./web_preview_18fps_requirement_v1.md) if touching Web preview target, display size, or brightness usability
12. [web_on_windows_migration_status_20260525.md](../plan_eng_review/web_on_windows_migration_status_20260525.md) if touching Windows migration or delivery-shell choice
13. [desktop_workstation_migration_requirement_v1.md](./desktop_workstation_migration_requirement_v1.md) only if the user explicitly reactivates desktop transition work
14. [architecture_lock.md](./architecture_lock.md)
15. [module_map.md](./module_map.md)
16. [lu92xx_modbus_rtu_requirement_v1.md](./lu92xx_modbus_rtu_requirement_v1.md) if touching real controller work
17. [afas_full_postprocessing_migration_requirement_v1.md](./afas_full_postprocessing_migration_requirement_v1.md) if touching post-run curve analysis parity, smoothing/outlier handling, AFAS-style charting, artifact persistence, or export/report equivalence
18. [live_capture_temporal_sampling_requirement_v1.md](./live_capture_temporal_sampling_requirement_v1.md) if touching preview cadence, measurement rate, or 50/100 Hz discussions
19. [afas_full_postprocessing_migration_plan_lock_v1.md](../plan_eng_review/afas_full_postprocessing_migration_plan_lock_v1.md) if touching AFAS parity, preprocessing migration, analysis chart parity, or export/report migration
20. [live_setup_freeze_roi_tracking_plan_lock_v1.md](../plan_eng_review/live_setup_freeze_roi_tracking_plan_lock_v1.md)
21. [live_setup_roi_ab_window_plan_lock_v1.md](../plan_eng_review/live_setup_roi_ab_window_plan_lock_v1.md)
22. [web_preview_18fps_plan_lock_v1.md](../plan_eng_review/web_preview_18fps_plan_lock_v1.md)
23. [desktop_workstation_migration_plan_lock_v1.md](../plan_eng_review/desktop_workstation_migration_plan_lock_v1.md) only for paused desktop-reference context
24. [desktop_workstation_migration_status_v1.md](../plan_eng_review/desktop_workstation_migration_status_v1.md) only for paused desktop-reference context
25. [live_run_plan_lock_v1.md](../plan_eng_review/live_run_plan_lock_v1.md)
26. [live_run_execution_plan_v1.md](../plan_eng_review/live_run_execution_plan_v1.md)
27. [live_run_implementation_breakdown_v1.md](../plan_eng_review/live_run_implementation_breakdown_v1.md)
28. [live_run_task_status_v1.md](../plan_eng_review/live_run_task_status_v1.md)
29. [live_run_test_plan_v1.md](../plan_eng_review/live_run_test_plan_v1.md)
30. [live_run_bench_validation_v1.md](../plan_eng_review/live_run_bench_validation_v1.md)

## 7. Practical Directory Notes

- Runtime output for dev profiles lives under `examples/runtime/`.
- Replay sample data lives under `examples/replay/`.
- Web static assets and templates live under `src/webapp/static/` and
  `src/webapp/templates/`.
- Adjustment JSON artifacts live under `<artifact_dir>/adjustments/`.
