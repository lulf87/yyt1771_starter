# Envelope Max Width Implementation Plan

Goal: Add an explicit `envelope_max_width` directional A/B selection mode for sparse line bundles and porous mesh/lattice targets without changing existing `max_chord` or `mask_projection` behavior.

Architecture:

- `src.vision.contour_direction` owns the new envelope target-mask construction and lateral-bin measurement.
- `src.core.models`, `src.webapp.schemas`, and Web/live-run adapters only pass the selected geometry mode and envelope parameters through.
- `src.workflow.live_run` keeps prior-gated tracking for existing modes, but accepts global envelope observations for `envelope_max_width` while retaining quality and gross-outlier checks.

## Files

- `docs/requirements/live_setup_freeze_roi_tracking_requirement_v1.md`: formal product semantics.
- `src/vision/contour_direction.py`: `envelope_max_width`, `line_bundle`, `mesh_lattice`, debug metadata.
- `src/core/models.py`: `MeasurementDefinition` pass-through fields.
- `src/webapp/schemas.py`: API validation for new mode and fields.
- `src/webapp/routes/live_run.py`: preset/save wiring.
- `src/workflow/live_run.py`: live-run global envelope tracking path and telemetry fields.
- `src/application/device_factory.py`: preserve fields during real/offline ROI coordinate transforms.
- `src/application/live_run_service.py`: persist new definition fields.
- `src/application/real_camera_alignment_probe.py`: preserve fields in definition JSON probe path.
- `src/application/real_offline_alignment_guard.py`: allow the explicit envelope formal mode on locked profiles while keeping `auto`/`mask_projection` blocked.
- `tests/vision/test_contour_direction.py`: synthetic line-bundle, mesh-lattice, rotated ROI, side-guard tests.
- `tests/workflow/test_live_run_state_machine.py`: live relocation test.
- `tests/webapp/test_live_run_api.py`: schema/API request coverage.
- `tests/application/test_device_factory.py`: coordinate-transform preservation.

## Tasks

1. Add failing vision tests for `line_bundle` and `mesh_lattice` envelope masks.
2. Implement envelope target-mask construction:
   - `line_bundle`: union all components above fragment floor.
   - `mesh_lattice`: union relevant components, modest close/fill small holes.
   - side guards report foreground area and exclude guard-dominated candidates.
3. Implement lateral-bin envelope measurement:
   - rotate points by `direction_angle_deg`.
   - per bin, robustly select low/high along endpoints using quantiles.
   - require enough support pixels.
   - choose the candidate with largest span, then support, then center proximity.
4. Pass `target_geometry_mode` and envelope parameters through models, schemas, routes, device transforms, artifacts, and probe helpers.
5. Add live-run envelope tracking:
   - do not pass endpoint/axis prior to the envelope extractor.
   - accept current-frame global envelope candidates as `accepted_global_envelope` or `envelope_relocated`.
   - reject gross outliers with zero quality, missing metric, ROI-edge/side-guard domination, or obviously impossible span.
6. Expose debug fields in metric meta and telemetry:
   - `target_geometry_mode`
   - `projection_point_mode`
   - `selected_component_count`
   - `envelope_candidate_count`
   - `side_guard_foreground_area`
   - `envelope_support_px`
   - `axis_offset_px`
   - `tracking_state`
7. Run targeted verification:
   - `.venv/bin/python -m pytest tests/vision/test_contour_direction.py -q`
   - `.venv/bin/python -m pytest tests/workflow/test_live_run_state_machine.py -q`
   - `.venv/bin/python -m pytest tests/webapp/test_live_run_api.py -q`
   - `.venv/bin/python -m pytest tests/application/test_device_factory.py -q`
   - `.venv/bin/python -m pytest tests/architecture -q`
   - browser check for the local Web setup flow if UI-visible behavior changes.
