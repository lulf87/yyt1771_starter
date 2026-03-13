# Requirements Overview

This file is the single entry point for project requirements, structure rules,
and implementation references.

## 1. Project Goal

Build a YY/T 1771 visual-analysis workstation that:

- starts from an offline minimum chain
- keeps module boundaries stable
- grows into a browser-based Web application
- runs with Mac-based development and Windows-based production profiles

The fixed system direction is:

```text
Browser -> Web API -> Workflow / Storage / Report
```

The fixed analysis chain is:

```text
Frame -> ShapeMetric -> SyncPoint -> Curve -> Result
```

Primary goal reference:

- [master_control_plan.md](./master_control_plan.md)

## 2. Structural Requirements

These files define the project structure and must be treated as the baseline
before any feature work:

- [architecture_lock.md](./architecture_lock.md)
  Directory freeze, top-level rules, `src`一级模块、依赖方向
- [module_map.md](./module_map.md)
  Module responsibilities and allowed direct dependencies

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
- `docs/`: requirements, task contracts, and architecture references
- `examples/`: replay samples, offline demos, and dev runtime outputs
- `src/`: application source code
- `tests/`: mirrored test layout by module

## 3. Code Directory Explanation

Current `src/` structure:

```text
src/
  core/
  camera/
  temp/
  plc/
  vision/
  sync/
  curve/
  workflow/
  storage/
  report/
  webapp/
```

Module explanation:

- `core`: shared models, contracts, enums, errors, config models
- `camera`: frame acquisition adapters only
- `temp`: temperature acquisition adapters only
- `plc`: PLC snapshot adapters only
- `vision`: image-to-metric extraction only
- `sync`: time alignment of multi-source data
- `curve`: normalization and result-point calculation
- `workflow`: orchestration, replay/mock session flow, precheck
- `storage`: SQLite and JSON artifact persistence
- `report`: result summary/export helpers
- `webapp`: FastAPI app, schemas, routes, templates, static assets

Matching test layout:

```text
tests/
  architecture/
  camera/
  curve/
  plc/
  storage/
  sync/
  temp/
  vision/
  webapp/
  workflow/
```

## 4. Requirement Layers

The project requirements are intentionally split across four layers.

### A. Master / Program Layer

- [master_control_plan.md](./master_control_plan.md)

Use this first when you need:

- overall project direction
- phase order
- current forbidden work
- why Web is the final interaction route

### B. Architecture / Boundary Layer

- [architecture_lock.md](./architecture_lock.md)
- [module_map.md](./module_map.md)

Use these when you need:

- directory rules
- module ownership
- import boundaries
- test layout constraints

### C. Feature / Contract Layer

Use these when you need the stable contract for a specific feature area:

- [adjustment_contract_v1.md](./adjustment_contract_v1.md)
  Manual adjustment state, draft, applied versions, latest result
- [ui_information_architecture_v1.md](./ui_information_architecture_v1.md)
  Workspace shell information architecture
- [workspace_page_breakdown_v1.md](./workspace_page_breakdown_v1.md)
  Replay workspace page composition
- [workspace_stage_mapping_v1.md](./workspace_stage_mapping_v1.md)
  Stepper stage mapping
- [workspace_computation_view_v1.md](./workspace_computation_view_v1.md)
  Curve, Af95, and point-frame linkage emphasis
- [workspace_adjustment_preview_v1.md](./workspace_adjustment_preview_v1.md)
  Adjustment preview and context display baseline
- [adjustment_mvp_breakdown_v1.md](./adjustment_mvp_breakdown_v1.md)
  Editable adjustment MVP scope

### D. Task / Delivery Layer

Task files capture what each implementation round was expected to deliver.

Examples:

- [codex_task_000_scaffold_freeze.md](./codex_task_000_scaffold_freeze.md)
- [codex_task_010_session_api.md](./codex_task_010_session_api.md)
- [codex_task_021_adjustment_contract.md](./codex_task_021_adjustment_contract.md)
- [codex_wp_a_adjustment_mvp.md](./codex_wp_a_adjustment_mvp.md)

Use these when you need:

- the exact scope of one completed task
- historical acceptance boundaries
- what was intentionally deferred

## 5. Current Product Scope

The current implemented product scope is:

- offline mock session flow
- replay session flow with detail artifact
- Web home page and workspace shell
- replay detail visualization
- system precheck panel
- adjustment backend contract and Adjustment MVP workspace

Still intentionally not in scope:

- live hardware orchestration in the workspace
- parameter-level image processing editing
- ROI editing
- desktop GUI main route
- summary overwrite through manual apply

## 6. Where To Read First

Recommended reading order for a new teammate:

1. [master_control_plan.md](./master_control_plan.md)
2. [architecture_lock.md](./architecture_lock.md)
3. [module_map.md](./module_map.md)
4. [ui_information_architecture_v1.md](./ui_information_architecture_v1.md)
5. One feature contract file for the area you are touching
6. The matching `codex_task_*.md` file for the task you are implementing

## 7. Practical Directory Notes

- Runtime output for dev profiles now lives under `examples/runtime/` to avoid
  creating new top-level directories outside the frozen structure.
- Replay sample data lives under `examples/replay/`.
- Web static assets and templates live under `src/webapp/static/` and
  `src/webapp/templates/`.
- Adjustment JSON artifacts live under `<artifact_dir>/adjustments/`.

## 8. Output Contract Reference

When a coding task asks for a formal close-out format, use:

- [codex_response_contract.md](./codex_response_contract.md)
