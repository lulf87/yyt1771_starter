# Plan Eng Review Directory

This directory is the canonical home for files owned by the
`gstack-plan-eng-review` role.

Use the files here when you need:

- the locked implementation plan for migrating full AFAS post-data capability parity, not just lightweight live `As / Af / AF95`
- the shipped status of persisted AFAS analysis / plot / report artifacts after full parity landed
- the locked engineering decision that `mac-finish` currently uses the Web workstation as the delivery shell
- the Windows migration status for Web-on-Windows
- the primary locked implementation decision after requirement refreeze
- the current execution plan
- implementation breakdown and task dependency order
- live status and validation boundaries
- the latest engineering-review framing for what is done vs. still drifting

Current authority set:

- [current_run_modes_20260524.md](./current_run_modes_20260524.md)
- [web_on_windows_migration_status_20260525.md](./web_on_windows_migration_status_20260525.md)
- [current_validation_state_20260524.md](./current_validation_state_20260524.md)
- [cleanup_inventory_20260524.md](./cleanup_inventory_20260524.md)
- [source_state_inventory_20260524.md](./source_state_inventory_20260524.md)
- [afas_full_postprocessing_migration_plan_lock_v1.md](./afas_full_postprocessing_migration_plan_lock_v1.md)
- [live_setup_freeze_roi_tracking_plan_lock_v1.md](./live_setup_freeze_roi_tracking_plan_lock_v1.md)
- [live_setup_roi_ab_window_plan_lock_v1.md](./live_setup_roi_ab_window_plan_lock_v1.md)
- [web_preview_18fps_plan_lock_v1.md](./web_preview_18fps_plan_lock_v1.md)
- [desktop_workstation_migration_plan_lock_v1.md](./desktop_workstation_migration_plan_lock_v1.md) paused legacy / fallback reference only
- [desktop_workstation_migration_status_v1.md](./desktop_workstation_migration_status_v1.md) paused legacy / fallback reference only
- [live_capture_temporal_sampling_plan_lock_v1.md](./live_capture_temporal_sampling_plan_lock_v1.md)
- [live_capture_temporal_sampling_bench_v1.md](./live_capture_temporal_sampling_bench_v1.md)
- [live_run_plan_lock_v1.md](./live_run_plan_lock_v1.md)
- [live_run_execution_plan_v1.md](./live_run_execution_plan_v1.md)
- [live_run_implementation_breakdown_v1.md](./live_run_implementation_breakdown_v1.md)
- [live_run_task_status_v1.md](./live_run_task_status_v1.md)
- [live_run_test_plan_v1.md](./live_run_test_plan_v1.md)
- [live_run_bench_validation_v1.md](./live_run_bench_validation_v1.md)

Rule:

- future engineering-plan changes must be updated here, not in duplicate docs
- future implementation work must read this directory together with
  `docs/requirements/`
