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
- now migrates final delivery toward a Windows desktop workstation while preserving workflow semantics
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

### B. Architecture / Boundary Baseline

- [architecture_lock.md](./architecture_lock.md)
- [module_map.md](./module_map.md)

Use these when you need:

- directory rules
- module ownership
- import boundaries
- test layout constraints

### C. Device / Requirement Baseline

- [desktop_workstation_migration_requirement_v1.md](./desktop_workstation_migration_requirement_v1.md)
- [lu92xx_modbus_rtu_requirement_v1.md](./lu92xx_modbus_rtu_requirement_v1.md)
- [live_capture_temporal_sampling_requirement_v1.md](./live_capture_temporal_sampling_requirement_v1.md)

Use this when you need:

- the locked decision to keep the same workflow while migrating final delivery to a desktop workstation
- the locked decision to keep the migration inside the current repository
- the locked acceptance gate for desktop preview display performance on Windows
- the locked LU92XX controller requirement shape
- verified Modbus RTU assumptions
- current hardware-side blockers that are allowed vs. not allowed
- the locked interpretation of preview fps vs. measurement sample rate
- the 50 Hz baseline / 100 Hz stretch requirement for synchronized measurement

### D. Engineering Review Baseline

The canonical engineering-review files now live in the sibling
`docs/plan_eng_review/` directory:

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
3. [desktop_workstation_migration_requirement_v1.md](./desktop_workstation_migration_requirement_v1.md) if touching final delivery shape, desktop transition, or same-workflow migration
4. [architecture_lock.md](./architecture_lock.md)
5. [module_map.md](./module_map.md)
6. [lu92xx_modbus_rtu_requirement_v1.md](./lu92xx_modbus_rtu_requirement_v1.md) if touching real controller work
7. [live_capture_temporal_sampling_requirement_v1.md](./live_capture_temporal_sampling_requirement_v1.md) if touching preview cadence, measurement rate, or 50/100 Hz discussions
8. [desktop_workstation_migration_plan_lock_v1.md](../plan_eng_review/desktop_workstation_migration_plan_lock_v1.md)
9. [desktop_workstation_migration_status_v1.md](../plan_eng_review/desktop_workstation_migration_status_v1.md)
10. [live_run_plan_lock_v1.md](../plan_eng_review/live_run_plan_lock_v1.md)
11. [live_run_task_status_v1.md](../plan_eng_review/live_run_task_status_v1.md)
12. [live_run_execution_plan_v1.md](../plan_eng_review/live_run_execution_plan_v1.md)
13. [live_run_implementation_breakdown_v1.md](../plan_eng_review/live_run_implementation_breakdown_v1.md)
14. [live_run_test_plan_v1.md](../plan_eng_review/live_run_test_plan_v1.md)

## 7. Practical Directory Notes

- Runtime output for dev profiles lives under `examples/runtime/`.
- Replay sample data lives under `examples/replay/`.
- Web static assets and templates live under `src/webapp/static/` and
  `src/webapp/templates/`.
- Adjustment JSON artifacts live under `<artifact_dir>/adjustments/`.
