"""Thin Qt shell for the desktop workstation bootstrap."""

from __future__ import annotations

import json

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

from src.core.models import MeasurementDefinition, MetricBox, PixelPoint, RectRegion
from src.desktop_app.controller import DesktopWorkbenchController


class DesktopMainWindow(QMainWindow):
    """Minimal desktop shell that exercises the shared workflow controller."""

    def __init__(self, *, controller: DesktopWorkbenchController) -> None:
        super().__init__()
        self.controller = controller
        self.current_run_id = ""
        self.setWindowTitle("YYT1771 Desktop Workstation")
        self.resize(960, 640)

        self.profile_label = QLabel(f"Profile: {controller.context.profile}")
        self.run_label = QLabel("Run: none")
        self.status_label = QLabel("Status: idle")
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
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
        self.save_definition_button = QPushButton("Save Definition")
        self.start_run_button = QPushButton("Start Live Run")
        self.refresh_result_button = QPushButton("Refresh Result")

        self.precheck_button.clicked.connect(lambda: self._wrap(self._handle_precheck))
        self.probe_button.clicked.connect(lambda: self._wrap(self._handle_probe))
        self.create_run_button.clicked.connect(lambda: self._wrap(self._handle_create_run))
        self.fetch_preview_button.clicked.connect(lambda: self._wrap(self._handle_fetch_preview))
        self.start_preview_button.clicked.connect(lambda: self._wrap(self._handle_start_preview))
        self.stop_preview_button.clicked.connect(lambda: self._wrap(self._handle_stop_preview))
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

        root_layout = QVBoxLayout()
        root_layout.addLayout(info_bar)
        root_layout.addLayout(controls)
        root_layout.addWidget(definition_group)
        root_layout.addWidget(self.log_view)

        root = QWidget()
        root.setLayout(root_layout)
        self.setCentralWidget(root)

        self._append_log("Desktop bootstrap ready. Use Create Run, then Save Definition to drive the workflow.")

    def _handle_precheck(self) -> None:
        self._append_json("precheck", self.controller.get_precheck())

    def _handle_probe(self) -> None:
        self._append_json("probe", self.controller.probe_camera())

    def _handle_create_run(self) -> None:
        record = self.controller.create_run(preset="balloon")
        self.current_run_id = record.run_id
        self.run_label.setText(f"Run: {record.run_id}")
        self.status_label.setText(f"Status: {record.status.value}")
        self._append_json("create_run", {"run_id": record.run_id, "status": record.status.value})

    def _handle_fetch_preview(self) -> None:
        run_id = self._require_run_id()
        frame = self.controller.fetch_preview_frame(run_id)
        self.status_label.setText("Status: preview frozen")
        self._append_json(
            "fetch_preview",
            {"frame_id": frame.frame_id, "timestamp_ms": frame.timestamp_ms, "source": frame.source},
        )

    def _handle_start_preview(self) -> None:
        run_id = self._require_run_id()
        frame = self.controller.start_preview(run_id)
        self.status_label.setText("Status: preview streaming")
        self._append_json(
            "start_preview",
            {"frame_id": frame.frame_id, "timestamp_ms": frame.timestamp_ms, "source": frame.source},
        )

    def _handle_stop_preview(self) -> None:
        run_id = self._require_run_id()
        snapshot = self.controller.stop_preview(run_id)
        self.status_label.setText("Status: preview stopped")
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
