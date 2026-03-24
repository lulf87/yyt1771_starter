# Plan Eng Review Directory

This directory is the canonical home for files owned by the
`gstack-plan-eng-review` role.

Use the files here when you need:

- the primary locked implementation decision after requirement refreeze
- the current execution plan
- implementation breakdown and task dependency order
- live status and validation boundaries
- the latest engineering-review framing for what is done vs. still drifting

Current authority set:

- [live_capture_temporal_sampling_plan_lock_v1.md](./live_capture_temporal_sampling_plan_lock_v1.md)
- [live_capture_temporal_sampling_bench_v1.md](./live_capture_temporal_sampling_bench_v1.md)
- [live_run_plan_lock_v1.md](./live_run_plan_lock_v1.md)
- [live_run_execution_plan_v1.md](./live_run_execution_plan_v1.md)
- [live_run_implementation_breakdown_v1.md](./live_run_implementation_breakdown_v1.md)
- [live_run_task_status_v1.md](./live_run_task_status_v1.md)
- [live_run_test_plan_v1.md](./live_run_test_plan_v1.md)
- [live_run_bench_validation_v1.md](./live_run_bench_validation_v1.md)

Rule:

- future engineering-plan changes must be updated here, not in legacy
  root-level docs
- future implementation work must read this directory together with
  `docs/requirements/`
