"""Thin Qt shell for the desktop workstation bootstrap."""

from __future__ import annotations

import json
import time

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.application import compute_preview_interval_ms
from src.application.preview_render import build_preview_bitmap
from src.core.models import MeasurementDefinition, MetricBox, PixelPoint, RectRegion
from src.desktop_app.controller import DesktopWorkbenchController
from src.desktop_app.overlay_math import ensure_definition_geometry
from src.desktop_app.preview_canvas import PreviewCanvasWidget


class DesktopMainWindow(QMainWindow):
    """Minimal desktop shell that exercises the shared workflow controller."""

    def __init__(self, *, controller: DesktopWorkbenchController) -> None:
        super().__init__()
        self.controller = controller
        self.current_run_id = ""
        self._preview_timer = QTimer(self)
        self._preview_timer.setInterval(
            compute_preview_interval_ms(
                target_fps=self.controller.context.runtime_config.live.run.preview_target_fps,
                fallback_ms=self.controller.context.runtime_config.live.run.preview_poll_ms,
            )
        )
        self._preview_timer.timeout.connect(self._handle_preview_tick)
        self._last_preview_frame_id: int | None = None
        self._stream_presented_frames = 0
        self._stream_started_at_monotonic: float | None = None
        self._stream_last_presented_at_monotonic: float | None = None
        self._stream_first_frame_id: int | None = None
        self._stream_last_frame_id: int | None = None
        self._syncing_definition_form = False
        self.setWindowTitle("YYT1771 Desktop Workstation")
        self.resize(1180, 760)

        self.profile_label = QLabel(f"Profile: {controller.context.profile}")
        self.run_label = QLabel("Run: none")
        self.status_label = QLabel("Status: idle")
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.preview_canvas = PreviewCanvasWidget(
            on_definition_changed=self._handle_overlay_definition_changed,
            on_status_message=self._handle_overlay_status_message,
        )
        self.preview_meta_label = QLabel("Preview: waiting for frame")
        self.target_temp_spin = QDoubleSpinBox()
        self.target_temp_spin.setRange(0.0, 1500.0)
        self.target_temp_spin.setDecimals(1)
        self.target_temp_spin.setValue(80.0)

        self.analysis_roi_x = _int_spinbox(0, 10000, 0)
        self.analysis_roi_y = _int_spinbox(0, 10000, 0)
        self.analysis_roi_w = _int_spinbox(1, 10000, 96)
        self.analysis_roi_h = _int_spinbox(1, 10000, 64)
        self.metric_center_x = _int_spinbox(0, 10000, 48)
        self.metric_center_y = _int_spinbox(0, 10000, 32)
        self.metric_width = _int_spinbox(1, 10000, 80)
        self.metric_height = _int_spinbox(1, 10000, 24)
        self.metric_angle = QDoubleSpinBox()
        self.metric_angle.setRange(-180.0, 180.0)
        self.metric_angle.setDecimals(1)
        self.metric_angle.setValue(0.0)
        self.point_a_x = _int_spinbox(0, 10000, 12)
        self.point_a_y = _int_spinbox(0, 10000, 32)
        self.point_b_x = _int_spinbox(0, 10000, 83)
        self.point_b_y = _int_spinbox(0, 10000, 32)
        self.min_target_area = _int_spinbox(1, 100000, 150)
        self.foreground_polarity = QComboBox()
        self.foreground_polarity.addItems(["dark_on_light", "light_on_dark"])
        self.threshold_mode = QComboBox()
        self.threshold_mode.addItems(["adaptive", "fixed"])
        self.ignore_internal_texture = QCheckBox("Ignore Internal Texture")
        self.ignore_internal_texture.setChecked(True)

        self.precheck_button = QPushButton("Precheck")
        self.probe_button = QPushButton("Probe Camera")
        self.create_run_button = QPushButton("Create Run")
        self.fetch_preview_button = QPushButton("Fetch Preview")
        self.start_preview_button = QPushButton("Start Preview")
        self.stop_preview_button = QPushButton("Stop Preview")
        self.draw_roi_button = QPushButton("Draw ROI")
        self.draw_window_button = QPushButton("Draw Window")
        self.rotate_window_button = QPushButton("Rotate Window")
        self.point_a_button = QPushButton("Point A")
        self.point_b_button = QPushButton("Point B")
        self.save_definition_button = QPushButton("Save Definition")
        self.start_run_button = QPushButton("Start Live Run")
        self.refresh_result_button = QPushButton("Refresh Result")

        self.precheck_button.clicked.connect(lambda: self._wrap(self._handle_precheck))
        self.probe_button.clicked.connect(lambda: self._wrap(self._handle_probe))
        self.create_run_button.clicked.connect(lambda: self._wrap(self._handle_create_run))
        self.fetch_preview_button.clicked.connect(lambda: self._wrap(self._handle_fetch_preview))
        self.start_preview_button.clicked.connect(lambda: self._wrap(self._handle_start_preview))
        self.stop_preview_button.clicked.connect(lambda: self._wrap(self._handle_stop_preview))
        self.draw_roi_button.clicked.connect(lambda: self._set_overlay_tool("draw-roi"))
        self.draw_window_button.clicked.connect(lambda: self._set_overlay_tool("draw-box"))
        self.rotate_window_button.clicked.connect(lambda: self._set_overlay_tool("rotate-box"))
        self.point_a_button.clicked.connect(lambda: self._set_overlay_tool("point-a"))
        self.point_b_button.clicked.connect(lambda: self._set_overlay_tool("point-b"))
        self.save_definition_button.clicked.connect(lambda: self._wrap(self._handle_save_definition))
        self.start_run_button.clicked.connect(lambda: self._wrap(self._handle_start_run))
        self.refresh_result_button.clicked.connect(lambda: self._wrap(self._handle_refresh_result))

        controls = QHBoxLayout()
        for button in (
            self.precheck_button,
            self.probe_button,
            self.create_run_button,
            self.fetch_preview_button,
            self.start_preview_button,
            self.stop_preview_button,
            self.draw_roi_button,
            self.draw_window_button,
            self.rotate_window_button,
            self.point_a_button,
            self.point_b_button,
            self.save_definition_button,
            self.start_run_button,
            self.refresh_result_button,
        ):
            controls.addWidget(button)

        info_bar = QHBoxLayout()
        info_bar.addWidget(self.profile_label)
        info_bar.addWidget(self.run_label)
        info_bar.addWidget(self.status_label)
        info_bar.addStretch(1)

        definition_group = QGroupBox("Measurement Definition")
        definition_layout = QGridLayout()
        definition_layout.addWidget(_build_group_box("Analysis ROI", [
            ("X", self.analysis_roi_x),
            ("Y", self.analysis_roi_y),
            ("Width", self.analysis_roi_w),
            ("Height", self.analysis_roi_h),
        ]), 0, 0)
        definition_layout.addWidget(_build_group_box("Metric Box", [
            ("Center X", self.metric_center_x),
            ("Center Y", self.metric_center_y),
            ("Width", self.metric_width),
            ("Height", self.metric_height),
            ("Angle", self.metric_angle),
        ]), 0, 1)
        definition_layout.addWidget(_build_group_box("Point A", [
            ("X", self.point_a_x),
            ("Y", self.point_a_y),
        ]), 1, 0)
        definition_layout.addWidget(_build_group_box("Point B", [
            ("X", self.point_b_x),
            ("Y", self.point_b_y),
        ]), 1, 1)
        meta_form = QFormLayout()
        meta_form.addRow("Foreground", self.foreground_polarity)
        meta_form.addRow("Threshold", self.threshold_mode)
        meta_form.addRow("Min Target Area", self.min_target_area)
        meta_form.addRow("Target Temp (C)", self.target_temp_spin)
        meta_form.addRow("", self.ignore_internal_texture)
        meta_group = QGroupBox("Run / Vision")
        meta_group.setLayout(meta_form)
        definition_layout.addWidget(meta_group, 2, 0, 1, 2)
        definition_group.setLayout(definition_layout)

        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout()
        preview_layout.addWidget(self.preview_canvas)
        preview_layout.addWidget(self.preview_meta_label)
        preview_group.setLayout(preview_layout)

        workspace_layout = QGridLayout()
        workspace_layout.addWidget(preview_group, 0, 0)
        workspace_layout.addWidget(definition_group, 0, 1)

        root_layout = QVBoxLayout()
        root_layout.addLayout(info_bar)
        root_layout.addLayout(controls)
        root_layout.addLayout(workspace_layout)
        root_layout.addWidget(self.log_view)

        root = QWidget()
        root.setLayout(root_layout)
        self.setCentralWidget(root)

        self._connect_definition_inputs()
        self._sync_canvas_definition()
        self._update_overlay_edit_state(editable=False)

        self._append_log("Desktop bootstrap ready. Use Create Run, then Save Definition to drive the workflow.")

    def _handle_precheck(self) -> None:
        self._append_json("precheck", self.controller.get_precheck())

    def _handle_probe(self) -> None:
        self._append_json("probe", self.controller.probe_camera())

    def _handle_create_run(self) -> None:
        record = self.controller.create_run(preset="balloon")
        self.current_run_id = record.run_id
        self._preview_timer.stop()
        self._clear_preview()
        self._reset_stream_metrics()
        self._update_overlay_edit_state(editable=False)
        self.run_label.setText(f"Run: {record.run_id}")
        self.status_label.setText(f"Status: {record.status.value}")
        self._append_json("create_run", {"run_id": record.run_id, "status": record.status.value})

    def _handle_fetch_preview(self) -> None:
        run_id = self._require_run_id()
        self._preview_timer.stop()
        frame = self.controller.fetch_preview_frame(run_id)
        self.status_label.setText("Status: preview frozen")
        self._display_frame(frame, mode="frozen")
        self._update_overlay_edit_state(editable=True)
        self._append_json(
            "fetch_preview",
            {"frame_id": frame.frame_id, "timestamp_ms": frame.timestamp_ms, "source": frame.source},
        )

    def _handle_start_preview(self) -> None:
        run_id = self._require_run_id()
        frame = self.controller.start_preview(run_id)
        self._reset_stream_metrics()
        self.status_label.setText("Status: preview streaming")
        self._display_frame(frame, mode="streaming")
        self._preview_timer.start()
        self._update_overlay_edit_state(editable=False)
        self._append_json(
            "start_preview",
            {"frame_id": frame.frame_id, "timestamp_ms": frame.timestamp_ms, "source": frame.source},
        )

    def _handle_stop_preview(self) -> None:
        run_id = self._require_run_id()
        self._preview_timer.stop()
        snapshot = self.controller.stop_preview(run_id)
        self.status_label.setText("Status: preview stopped")
        frame = self.controller.get_cached_preview_frame(run_id)
        if frame is not None:
            self._display_frame(frame, mode="frozen", preview_fps=snapshot.preview_display_fps)
            self._update_overlay_edit_state(editable=True)
        else:
            self.preview_meta_label.setText("Preview: stream stopped with no cached frame")
            self._update_overlay_edit_state(editable=False)
        self._append_json(
            "stop_preview",
            {
                "stream_active": snapshot.stream_active,
                "frozen_frame_available": snapshot.frozen_frame_available,
                "last_frame_id": snapshot.last_frame_id,
                "preview_display_fps": snapshot.preview_display_fps,
            },
        )

    def _handle_save_definition(self) -> None:
        run_id = self._require_run_id()
        record = self.controller.save_definition(run_id, self._definition_from_form())
        self.status_label.setText(f"Status: {record.status.value}")
        self._append_json(
            "save_definition",
            {
                "run_id": record.run_id,
                "status": record.status.value,
                "definition_complete": bool(record.definition and record.definition.is_complete()),
            },
        )

    def _handle_start_run(self) -> None:
        run_id = self._require_run_id()
        self.controller.start_live_run(run_id, target_temperature_celsius=float(self.target_temp_spin.value()))
        self.status_label.setText("Status: live run started")
        self._append_json(
            "start_live_run",
            {"run_id": run_id, "target_temperature_celsius": float(self.target_temp_spin.value())},
        )

    def _handle_refresh_result(self) -> None:
        run_id = self._require_run_id()
        self._append_json(
            "refresh_result",
            {
                "result": self.controller.get_result(run_id),
                "detail": self.controller.get_detail(run_id),
                "telemetry": self.controller.get_telemetry(run_id),
            },
        )

    def _handle_preview_tick(self) -> None:
        try:
            self._refresh_preview_frame()
        except Exception as exc:  # pragma: no cover - timer path
            self._preview_timer.stop()
            self._show_error(exc)

    def _refresh_preview_frame(self) -> None:
        if not self.current_run_id:
            self._preview_timer.stop()
            return
        snapshot = self.controller.get_preview_state(self.current_run_id)
        if not snapshot.stream_active:
            self._preview_timer.stop()
            return
        frame = self.controller.get_cached_preview_frame(self.current_run_id)
        if frame is None or frame.frame_id == self._last_preview_frame_id:
            if snapshot.preview_display_fps is not None:
                self.preview_meta_label.setText(
                    f"Preview: waiting for next frame | ~{snapshot.preview_display_fps:.2f} fps"
                )
            return
        self._display_frame(frame, mode="streaming", preview_fps=snapshot.preview_display_fps)

    def _display_frame(
        self,
        frame,
        *,
        mode: str,
        preview_fps: float | None = None,
    ) -> None:
        previous_frame_id = self._last_preview_frame_id
        bitmap = build_preview_bitmap(frame.image, max_width=640, max_height=480)
        self.preview_canvas.set_preview_bitmap(bitmap)
        if self.current_run_id:
            self.controller.mark_preview_frame_presented(self.current_run_id, frame)
        self._record_presented_stream_frame(mode=mode, frame_id=frame.frame_id, previous_frame_id=previous_frame_id)
        self._sync_canvas_definition()
        fps_text = "" if preview_fps is None else f" | ~{preview_fps:.2f} fps"
        self.preview_meta_label.setText(
            "Preview: "
            f"{mode} | frame_id={frame.frame_id or 0} | source={frame.source} | "
            f"{bitmap.width}x{bitmap.height}{fps_text}"
        )
        self._last_preview_frame_id = frame.frame_id

    def _clear_preview(self) -> None:
        self._last_preview_frame_id = None
        self.preview_canvas.set_preview_bitmap(None)
        self.preview_canvas.set_edit_mode("")
        self.preview_meta_label.setText("Preview: waiting for frame")

    def preview_benchmark_summary(self) -> dict[str, object]:
        snapshot = None
        if self.current_run_id:
            snapshot = self.controller.get_preview_state(self.current_run_id)
        elapsed_s = 0.0
        if (
            self._stream_started_at_monotonic is not None
            and self._stream_last_presented_at_monotonic is not None
        ):
            elapsed_s = max(0.0, self._stream_last_presented_at_monotonic - self._stream_started_at_monotonic)
        measured_presented_fps = None
        if elapsed_s > 0 and self._stream_presented_frames > 1:
            measured_presented_fps = round((self._stream_presented_frames - 1) / elapsed_s, 3)
        return {
            "run_id": self.current_run_id,
            "timer_interval_ms": self._preview_timer.interval(),
            "target_preview_fps": self.controller.context.runtime_config.live.run.preview_target_fps,
            "preview_poll_ms": self.controller.context.runtime_config.live.run.preview_poll_ms,
            "stream_presented_frames": self._stream_presented_frames,
            "stream_first_frame_id": self._stream_first_frame_id,
            "stream_last_frame_id": self._stream_last_frame_id,
            "measured_presented_fps": measured_presented_fps,
            "preview_display_fps": None
            if snapshot is None or snapshot.preview_display_fps is None
            else round(snapshot.preview_display_fps, 3),
            "has_bitmap": self.preview_canvas.has_preview_bitmap(),
            "preview_meta": self.preview_meta_label.text(),
        }

    def _require_run_id(self) -> str:
        if not self.current_run_id:
            raise RuntimeError("No active run. Use Create Run first.")
        return self.current_run_id

    def _definition_from_form(self) -> MeasurementDefinition:
        return MeasurementDefinition(
            analysis_roi=RectRegion(
                x=int(self.analysis_roi_x.value()),
                y=int(self.analysis_roi_y.value()),
                width=int(self.analysis_roi_w.value()),
                height=int(self.analysis_roi_h.value()),
            ),
            metric_box=MetricBox(
                center_x=int(self.metric_center_x.value()),
                center_y=int(self.metric_center_y.value()),
                width=int(self.metric_width.value()),
                height=int(self.metric_height.value()),
                angle_deg=float(self.metric_angle.value()),
            ),
            point_a_px=PixelPoint(x=int(self.point_a_x.value()), y=int(self.point_a_y.value())),
            point_b_px=PixelPoint(x=int(self.point_b_x.value()), y=int(self.point_b_y.value())),
            foreground_polarity=self.foreground_polarity.currentText(),
            threshold_mode=self.threshold_mode.currentText(),
            ignore_internal_texture=self.ignore_internal_texture.isChecked(),
            min_target_area_px=int(self.min_target_area.value()),
        )

    def _append_json(self, label: str, payload: object) -> None:
        self._append_log(f"[{label}] {json.dumps(payload, ensure_ascii=False, indent=2, default=str)}")

    def _append_log(self, message: str) -> None:
        self.log_view.appendPlainText(message)

    def _show_error(self, exc: Exception) -> None:
        QMessageBox.critical(self, "YYT1771 Desktop Workstation", str(exc))

    def _wrap(self, fn) -> None:
        try:
            fn()
        except Exception as exc:  # pragma: no cover - Qt signal wrapper
            self._show_error(exc)

    def _set_overlay_tool(self, mode: str) -> None:
        if not self.draw_roi_button.isEnabled():
            return
        self.preview_canvas.set_edit_mode(mode)
        labels = {
            "draw-roi": "Drag on the preview to draw the analysis ROI.",
            "draw-box": "Drag on the preview to draw the observation window.",
            "rotate-box": "Drag around the observation window center to rotate it.",
            "point-a": "Click on the preview to place Point A.",
            "point-b": "Click on the preview to place Point B.",
        }
        self.status_label.setText(f"Status: {mode}")
        self._append_log(labels.get(mode, f"Overlay tool active: {mode}"))

    def _handle_overlay_definition_changed(self, definition: MeasurementDefinition) -> None:
        self._apply_definition_to_form(definition)
        self.status_label.setText("Status: overlay updated")

    def _handle_overlay_status_message(self, message: str) -> None:
        self._append_log(message)

    def _connect_definition_inputs(self) -> None:
        for widget, signal_name in self._definition_input_signals():
            getattr(widget, signal_name).connect(self._on_definition_form_changed)

    def _definition_input_signals(self) -> list[tuple[QWidget, str]]:
        return [
            (self.analysis_roi_x, "valueChanged"),
            (self.analysis_roi_y, "valueChanged"),
            (self.analysis_roi_w, "valueChanged"),
            (self.analysis_roi_h, "valueChanged"),
            (self.metric_center_x, "valueChanged"),
            (self.metric_center_y, "valueChanged"),
            (self.metric_width, "valueChanged"),
            (self.metric_height, "valueChanged"),
            (self.metric_angle, "valueChanged"),
            (self.point_a_x, "valueChanged"),
            (self.point_a_y, "valueChanged"),
            (self.point_b_x, "valueChanged"),
            (self.point_b_y, "valueChanged"),
            (self.min_target_area, "valueChanged"),
            (self.foreground_polarity, "currentTextChanged"),
            (self.threshold_mode, "currentTextChanged"),
            (self.ignore_internal_texture, "checkStateChanged"),
        ]

    def _on_definition_form_changed(self, *_args) -> None:
        if self._syncing_definition_form:
            return
        self._sync_canvas_definition()

    def _sync_canvas_definition(self) -> None:
        self.preview_canvas.set_definition(ensure_definition_geometry(self._definition_from_form()))

    def _apply_definition_to_form(self, definition: MeasurementDefinition) -> None:
        self._syncing_definition_form = True
        try:
            self.analysis_roi_x.setValue(definition.analysis_roi.x)
            self.analysis_roi_y.setValue(definition.analysis_roi.y)
            self.analysis_roi_w.setValue(definition.analysis_roi.width)
            self.analysis_roi_h.setValue(definition.analysis_roi.height)
            self.metric_center_x.setValue(definition.metric_box.center_x)
            self.metric_center_y.setValue(definition.metric_box.center_y)
            self.metric_width.setValue(definition.metric_box.width)
            self.metric_height.setValue(definition.metric_box.height)
            self.metric_angle.setValue(float(definition.metric_box.angle_deg))
            self.point_a_x.setValue(definition.point_a_px.x)
            self.point_a_y.setValue(definition.point_a_px.y)
            self.point_b_x.setValue(definition.point_b_px.x)
            self.point_b_y.setValue(definition.point_b_px.y)
            self.foreground_polarity.setCurrentText(definition.foreground_polarity)
            self.threshold_mode.setCurrentText(definition.threshold_mode)
            self.ignore_internal_texture.setChecked(definition.ignore_internal_texture)
            self.min_target_area.setValue(definition.min_target_area_px)
        finally:
            self._syncing_definition_form = False
        self.preview_canvas.set_definition(definition)

    def _update_overlay_edit_state(self, *, editable: bool) -> None:
        for button in (
            self.draw_roi_button,
            self.draw_window_button,
            self.rotate_window_button,
            self.point_a_button,
            self.point_b_button,
        ):
            button.setEnabled(editable)
        if not editable:
            self.preview_canvas.set_edit_mode("")

    def _reset_stream_metrics(self) -> None:
        self._stream_presented_frames = 0
        self._stream_started_at_monotonic = None
        self._stream_last_presented_at_monotonic = None
        self._stream_first_frame_id = None
        self._stream_last_frame_id = None

    def _record_presented_stream_frame(
        self,
        *,
        mode: str,
        frame_id: int | None,
        previous_frame_id: int | None,
    ) -> None:
        if mode != "streaming":
            return
        if frame_id is None:
            return
        if previous_frame_id == frame_id:
            return
        now = time.monotonic()
        if self._stream_started_at_monotonic is None:
            self._stream_started_at_monotonic = now
        self._stream_last_presented_at_monotonic = now
        self._stream_presented_frames += 1
        if self._stream_first_frame_id is None:
            self._stream_first_frame_id = frame_id
        self._stream_last_frame_id = frame_id

def _int_spinbox(minimum: int, maximum: int, value: int) -> QSpinBox:
    spinbox = QSpinBox()
    spinbox.setRange(minimum, maximum)
    spinbox.setValue(value)
    return spinbox


def _build_group_box(title: str, rows: list[tuple[str, QWidget]]) -> QGroupBox:
    group = QGroupBox(title)
    layout = QFormLayout()
    for label, widget in rows:
        layout.addRow(label, widget)
    group.setLayout(layout)
    return group
