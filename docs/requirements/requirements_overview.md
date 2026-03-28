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

Build a YY/T 1771 visual-analysis workstation that:

- starts from an offline minimum chain
- keeps module boundaries stable
- has already proven a browser-based workstation baseline
- keeps a desktop-migration path active, but now explicitly re-evaluates whether a tuned Web shell can remain the final delivery path when the preview target is narrowed to `18 fps`
- runs with Mac-based development and Windows-based production profiles

The fixed system direction is:

```text
Delivery Shell (desktop_app | webapp) -> Application Layer -> Workflow / Storage / Report
```

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
- the current desktop-delivery migration direction
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
- [live_setup_freeze_roi_tracking_requirement_v1.md](./live_setup_freeze_roi_tracking_requirement_v1.md)
- [live_setup_roi_ab_window_requirement_v1.md](./live_setup_roi_ab_window_requirement_v1.md)
- [web_preview_18fps_requirement_v1.md](./web_preview_18fps_requirement_v1.md)
- [desktop_workstation_migration_requirement_v1.md](./desktop_workstation_migration_requirement_v1.md)
- [afas_full_postprocessing_migration_requirement_v1.md](./afas_full_postprocessing_migration_requirement_v1.md)
- [lu92xx_modbus_rtu_requirement_v1.md](./lu92xx_modbus_rtu_requirement_v1.md)
- [live_capture_temporal_sampling_requirement_v1.md](./live_capture_temporal_sampling_requirement_v1.md)

Use this when you need:

- the locked home/workspace shell split between `Launch & Control Cockpit` and `Analysis Studio`
- the deterministic selection rule for `Compact Result -> Open Workspace`
- the locked rule that `observation_window` is not part of the current home cockpit operator path
- the locked escalation rule for when `Point A / Point B` must become prominent for manual review
- the first-pass DOM / API / test-anchor guardrails for home/workspace shell refactors
- the current operator-facing live setup workflow after the shift to `auto-live-preview -> Freeze -> rotated ROI -> ROI-local A-B -> live ROI tracking`
- the locked decision that the old `Create Live Run / Fetch Preview / Start Live Preview` buttons are no longer part of the operator workflow
- the locked decision that `Draw Window / Rotate Window` are removed from the current operator setup flow
- the locked rule that ROI is now both the setup search region and the live deformation capture region
- the locked rule that auto-detected `A-B` must be found along the ROI-local horizontal axis, not world-axis horizontal/vertical and not arbitrary diagonals
- the locked rule that any ROI geometry or sensitivity change must trigger recapture plus point recomputation
- the locked requirement for a rotation handle on ROI, a visible ROI angle field, a current-temperature display, a target-temperature confirm action, and live A/B refresh during test
- the locked rule that `ROI` is the primary search region for auto detect
- the locked rule that `A-B` must be defined before `observation_window` becomes semantically meaningful
- the locked rule that `Auto Detect Points` must search inside ROI and return a horizontal-or-vertical dominant point pair, not a pre-window axis guess or an arbitrary diagonal diameter
- the locked rule that `observation_window` is a post-A/B live-run observation aperture rather than an auto-detect prerequisite
- the locked rule that downstream observation direction is constrained to the window's `long_axis` or `short_axis`
- the locked decision gate for whether Web may remain the final delivery shell under an `18 fps` preview target
- the locked interpretation of “bigger and brighter Web preview” as a requirement rather than an implementation suggestion
- the locked rule that desktop migration is now conditional on whether the narrowed Web gate passes
- the locked decision to keep the same workflow while migrating final delivery to a desktop workstation
- the locked decision to keep the migration inside the current repository
- the locked acceptance gate for desktop preview display performance on Windows
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
- [desktop_workstation_migration_plan_lock_v1.md](../plan_eng_review/desktop_workstation_migration_plan_lock_v1.md)
- [desktop_workstation_migration_status_v1.md](../plan_eng_review/desktop_workstation_migration_status_v1.md)
- [live_capture_temporal_sampling_plan_lock_v1.md](../plan_eng_review/live_capture_temporal_sampling_plan_lock_v1.md)
- [live_run_plan_lock_v1.md](../plan_eng_review/live_run_plan_lock_v1.md)
- [live_run_execution_plan_v1.md](../plan_eng_review/live_run_execution_plan_v1.md)
- [live_run_implementation_breakdown_v1.md](../plan_eng_review/live_run_implementation_breakdown_v1.md)
- [live_run_task_status_v1.md](../plan_eng_review/live_run_task_status_v1.md)
- [live_run_test_plan_v1.md](../plan_eng_review/live_run_test_plan_v1.md)
- [live_run_bench_validation_v1.md](../plan_eng_review/live_run_bench_validation_v1.md)

Use these when you need:

- the locked implementation plan for full AFAS postprocessing parity beyond the current lightweight live `afas.py` path
- the locked implementation plan for the new operator workflow after the shift to `auto-live-preview -> Freeze -> rotated ROI -> ROI-local A-B -> live ROI tracking`
- the engineering decision to keep the existing run/session backend but demote the old preview buttons to internal implementation detail
- the phased implementation order for ROI angle, sensitivity, current-temperature display, target-temperature confirmation, and live A/B updates
- the locked implementation plan for `ROI -> A-B -> observation window -> observation_axis`
- the engineering decision to split ROI-first point detection from post-A/B window-bounded tracking
- the locked implementation decision for whether Web can remain the final delivery shell under the narrowed `18 fps` preview target
- the locked desktop-transition plan for staying in the current repo and extracting an application layer before adding a desktop shell
- the current D1-D7 desktop migration progress board
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
4. [live_setup_freeze_roi_tracking_requirement_v1.md](./live_setup_freeze_roi_tracking_requirement_v1.md) if touching launch flow, Freeze, ROI editing, ROI rotation, ROI-local point detection, sensitivity, current temperature display, target-temperature confirmation, or live A/B tracking
5. [live_setup_roi_ab_window_requirement_v1.md](./live_setup_roi_ab_window_requirement_v1.md) only when you need the older `ROI -> A-B -> observation window` split for historical context or for identifying what the newer live setup requirement superseded
6. [web_preview_18fps_requirement_v1.md](./web_preview_18fps_requirement_v1.md) if touching final delivery choice, Web preview target, display size, or brightness usability
7. [desktop_workstation_migration_requirement_v1.md](./desktop_workstation_migration_requirement_v1.md) if touching desktop transition, same-workflow migration, or the contingency path when Web does not pass the narrowed gate
8. [architecture_lock.md](./architecture_lock.md)
9. [module_map.md](./module_map.md)
10. [lu92xx_modbus_rtu_requirement_v1.md](./lu92xx_modbus_rtu_requirement_v1.md) if touching real controller work
11. [afas_full_postprocessing_migration_requirement_v1.md](./afas_full_postprocessing_migration_requirement_v1.md) if touching post-run curve analysis parity, smoothing/outlier handling, AFAS-style charting, artifact persistence, or export/report equivalence
12. [live_capture_temporal_sampling_requirement_v1.md](./live_capture_temporal_sampling_requirement_v1.md) if touching preview cadence, measurement rate, or 50/100 Hz discussions
13. [afas_full_postprocessing_migration_plan_lock_v1.md](../plan_eng_review/afas_full_postprocessing_migration_plan_lock_v1.md) if touching AFAS parity, preprocessing migration, analysis chart parity, or export/report migration
14. [live_setup_freeze_roi_tracking_plan_lock_v1.md](../plan_eng_review/live_setup_freeze_roi_tracking_plan_lock_v1.md)
15. [live_setup_roi_ab_window_plan_lock_v1.md](../plan_eng_review/live_setup_roi_ab_window_plan_lock_v1.md)
16. [web_preview_18fps_plan_lock_v1.md](../plan_eng_review/web_preview_18fps_plan_lock_v1.md)
17. [desktop_workstation_migration_plan_lock_v1.md](../plan_eng_review/desktop_workstation_migration_plan_lock_v1.md)
18. [desktop_workstation_migration_status_v1.md](../plan_eng_review/desktop_workstation_migration_status_v1.md)
19. [live_run_plan_lock_v1.md](../plan_eng_review/live_run_plan_lock_v1.md)
20. [live_run_task_status_v1.md](../plan_eng_review/live_run_task_status_v1.md)
21. [live_run_execution_plan_v1.md](../plan_eng_review/live_run_execution_plan_v1.md)
22. [live_run_implementation_breakdown_v1.md](../plan_eng_review/live_run_implementation_breakdown_v1.md)
23. [live_run_test_plan_v1.md](../plan_eng_review/live_run_test_plan_v1.md)

## 7. Practical Directory Notes

- Runtime output for dev profiles lives under `examples/runtime/`.
- Replay sample data lives under `examples/replay/`.
- Web static assets and templates live under `src/webapp/static/` and
  `src/webapp/templates/`.
- Adjustment JSON artifacts live under `<artifact_dir>/adjustments/`.
