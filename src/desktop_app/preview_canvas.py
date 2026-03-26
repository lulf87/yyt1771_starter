"""Native preview canvas with overlay editing for the desktop shell."""

from __future__ import annotations

from collections.abc import Callable
import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QMouseEvent, QPainter, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import QWidget

from src.application.preview_render import PreviewBitmap
from src.core.models import MeasurementDefinition, MetricBox, PixelPoint, RectRegion
from src.desktop_app.overlay_math import ensure_definition_geometry, metric_box_corners, seed_points_for_metric_box


class PreviewCanvasWidget(QWidget):
    """Display preview frames and allow basic overlay-based editing."""

    def __init__(
        self,
        *,
        on_definition_changed: Callable[[MeasurementDefinition], None] | None = None,
        on_status_message: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__()
        self._bitmap: PreviewBitmap | None = None
        self._pixmap: QPixmap | None = None
        self._definition: MeasurementDefinition | None = None
        self._content_rect = QRectF()
        self._drag_start: tuple[int, int] | None = None
        self._drag_mode = ""
        self._on_definition_changed = on_definition_changed
        self._on_status_message = on_status_message
        self._edit_mode = ""
        self.setMinimumSize(640, 426)
        self.setMouseTracking(True)

    def set_preview_bitmap(self, bitmap: PreviewBitmap | None) -> None:
        self._bitmap = bitmap
        if bitmap is None:
            self._pixmap = None
        else:
            image = QImage(bitmap.pixels, bitmap.width, bitmap.height, bitmap.width, QImage.Format.Format_Grayscale8)
            self._pixmap = QPixmap.fromImage(image.copy())
        self.update()

    def has_preview_bitmap(self) -> bool:
        return self._pixmap is not None and not self._pixmap.isNull()

    def set_definition(self, definition: MeasurementDefinition | None) -> None:
        self._definition = None if definition is None else ensure_definition_geometry(definition)
        self.update()

    def set_edit_mode(self, mode: str) -> None:
        self._edit_mode = mode
        self._drag_mode = ""
        self._drag_start = None
        self.update()

    def paintEvent(self, event) -> None:  # pragma: no cover - Qt paint path
        del event
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#101418"))
        self._content_rect = self._compute_content_rect()
        if self._pixmap is None or self._pixmap.isNull():
            painter.setPen(QColor("#d7dde4"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No preview frame yet")
            return
        scaled = self._pixmap.scaled(
            self._content_rect.size().toSize(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )
        image_rect = QRectF(
            self._content_rect.x() + (self._content_rect.width() - scaled.width()) / 2,
            self._content_rect.y() + (self._content_rect.height() - scaled.height()) / 2,
            scaled.width(),
            scaled.height(),
        )
        self._content_rect = image_rect
        painter.drawPixmap(image_rect.topLeft(), scaled)
        if self._definition is not None:
            self._paint_overlay(painter, self._definition)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # pragma: no cover - Qt event path
        point = self._event_to_image_point(event)
        if point is None or self._definition is None or not self._edit_mode:
            return
        if self._edit_mode == "point-a":
            self._apply_definition(
                MeasurementDefinition(
                    analysis_roi=self._definition.analysis_roi,
                    metric_box=self._definition.metric_box,
                    point_a_px=PixelPoint(x=point[0], y=point[1]),
                    point_b_px=self._definition.point_b_px,
                    foreground_polarity=self._definition.foreground_polarity,
                    threshold_mode=self._definition.threshold_mode,
                    ignore_internal_texture=self._definition.ignore_internal_texture,
                    min_target_area_px=self._definition.min_target_area_px,
                ),
                message=f"Point A placed at ({point[0]}, {point[1]}).",
                clear_mode=True,
            )
            return
        if self._edit_mode == "point-b":
            self._apply_definition(
                MeasurementDefinition(
                    analysis_roi=self._definition.analysis_roi,
                    metric_box=self._definition.metric_box,
                    point_a_px=self._definition.point_a_px,
                    point_b_px=PixelPoint(x=point[0], y=point[1]),
                    foreground_polarity=self._definition.foreground_polarity,
                    threshold_mode=self._definition.threshold_mode,
                    ignore_internal_texture=self._definition.ignore_internal_texture,
                    min_target_area_px=self._definition.min_target_area_px,
                ),
                message=f"Point B placed at ({point[0]}, {point[1]}).",
                clear_mode=True,
            )
            return
        self._drag_mode = self._edit_mode
        self._drag_start = point

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # pragma: no cover - Qt event path
        if not self._drag_mode or self._drag_start is None or self._definition is None:
            return
        point = self._event_to_image_point(event)
        if point is None:
            return
        start_x, start_y = self._drag_start
        if self._drag_mode == "draw-roi":
            x = min(start_x, point[0])
            y = min(start_y, point[1])
            width = max(1, abs(point[0] - start_x))
            height = max(1, abs(point[1] - start_y))
            next_definition = MeasurementDefinition(
                analysis_roi=RectRegion(x=x, y=y, width=width, height=height),
                metric_box=self._definition.metric_box,
                point_a_px=self._definition.point_a_px,
                point_b_px=self._definition.point_b_px,
                foreground_polarity=self._definition.foreground_polarity,
                threshold_mode=self._definition.threshold_mode,
                ignore_internal_texture=self._definition.ignore_internal_texture,
                min_target_area_px=self._definition.min_target_area_px,
            )
            self._apply_definition(next_definition, clear_mode=False)
            return
        if self._drag_mode == "draw-box":
            x = min(start_x, point[0])
            y = min(start_y, point[1])
            width = max(1, abs(point[0] - start_x))
            height = max(1, abs(point[1] - start_y))
            box = MetricBox(
                center_x=round(x + width / 2),
                center_y=round(y + height / 2),
                width=width,
                height=height,
                angle_deg=0.0,
            )
            point_a, point_b = seed_points_for_metric_box(box)
            next_definition = MeasurementDefinition(
                analysis_roi=self._definition.analysis_roi,
                metric_box=box,
                point_a_px=point_a,
                point_b_px=point_b,
                foreground_polarity=self._definition.foreground_polarity,
                threshold_mode=self._definition.threshold_mode,
                ignore_internal_texture=self._definition.ignore_internal_texture,
                min_target_area_px=self._definition.min_target_area_px,
            )
            self._apply_definition(next_definition, clear_mode=False)
            return
        if self._drag_mode == "rotate-box":
            box = self._definition.metric_box
            angle_deg = math.degrees(math.atan2(point[1] - box.center_y, point[0] - box.center_x))
            next_definition = MeasurementDefinition(
                analysis_roi=self._definition.analysis_roi,
                metric_box=MetricBox(
                    center_x=box.center_x,
                    center_y=box.center_y,
                    width=box.width,
                    height=box.height,
                    angle_deg=angle_deg,
                ),
                point_a_px=self._definition.point_a_px,
                point_b_px=self._definition.point_b_px,
                foreground_polarity=self._definition.foreground_polarity,
                threshold_mode=self._definition.threshold_mode,
                ignore_internal_texture=self._definition.ignore_internal_texture,
                min_target_area_px=self._definition.min_target_area_px,
            )
            self._apply_definition(next_definition, clear_mode=False)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # pragma: no cover - Qt event path
        del event
        if not self._drag_mode:
            return
        completed_mode = self._drag_mode
        self._drag_mode = ""
        self._drag_start = None
        messages = {
            "draw-roi": "Analysis ROI updated from the preview overlay.",
            "draw-box": "Observation window updated from the preview overlay.",
            "rotate-box": "Observation window angle updated from the preview overlay.",
        }
        if self._on_status_message is not None and completed_mode in messages:
            self._on_status_message(messages[completed_mode])
        self._edit_mode = ""
        self.update()

    def _apply_definition(
        self,
        definition: MeasurementDefinition,
        *,
        message: str | None = None,
        clear_mode: bool,
    ) -> None:
        self._definition = ensure_definition_geometry(definition)
        if self._on_definition_changed is not None:
            self._on_definition_changed(self._definition)
        if message and self._on_status_message is not None:
            self._on_status_message(message)
        if clear_mode:
            self._edit_mode = ""
        self.update()

    def _paint_overlay(self, painter: QPainter, definition: MeasurementDefinition) -> None:
        roi_pen = QPen(QColor("#19c37d"), 2)
        box_pen = QPen(QColor("#ffd166"), 2)
        point_pen = QPen(QColor("#ff6b6b"), 2)
        centerline_pen = QPen(QColor("#f4f1de"), 1)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        roi = definition.analysis_roi
        roi_rect = QRectF(*self._image_rect_to_widget(roi))
        painter.setPen(roi_pen)
        painter.drawRect(roi_rect)

        box_points = [QPointF(*self._image_point_to_widget(x, y)) for x, y in metric_box_corners(definition.metric_box)]
        painter.setPen(box_pen)
        painter.drawPolygon(QPolygonF(box_points))

        angle_rad = math.radians(float(definition.metric_box.angle_deg))
        centerline_x = math.cos(angle_rad) * (float(definition.metric_box.width) / 2)
        centerline_y = math.sin(angle_rad) * (float(definition.metric_box.width) / 2)
        painter.setPen(centerline_pen)
        painter.drawLine(
            QPointF(
                *self._image_point_to_widget(
                    definition.metric_box.center_x - centerline_x,
                    definition.metric_box.center_y - centerline_y,
                )
            ),
            QPointF(
                *self._image_point_to_widget(
                    definition.metric_box.center_x + centerline_x,
                    definition.metric_box.center_y + centerline_y,
                )
            ),
        )

        painter.setPen(point_pen)
        for label, point in (("A", definition.point_a_px), ("B", definition.point_b_px)):
            x, y = self._image_point_to_widget(point.x, point.y)
            painter.setBrush(QColor("#ff6b6b"))
            painter.drawEllipse(QPointF(x, y), 5, 5)
            painter.drawText(QPointF(x + 8, y - 8), label)

    def _compute_content_rect(self) -> QRectF:
        margin = 12
        return QRectF(margin, margin, max(1, self.width() - margin * 2), max(1, self.height() - margin * 2))

    def _event_to_image_point(self, event: QMouseEvent) -> tuple[int, int] | None:
        if self._bitmap is None or self._content_rect.width() <= 0 or self._content_rect.height() <= 0:
            return None
        x = float(event.position().x())
        y = float(event.position().y())
        if not self._content_rect.contains(QPointF(x, y)):
            return None
        image_x = round((x - self._content_rect.x()) * (self._bitmap.width / self._content_rect.width()))
        image_y = round((y - self._content_rect.y()) * (self._bitmap.height / self._content_rect.height()))
        image_x = max(0, min(self._bitmap.width - 1, image_x))
        image_y = max(0, min(self._bitmap.height - 1, image_y))
        return image_x, image_y

    def _image_point_to_widget(self, x: float, y: float) -> tuple[float, float]:
        if self._bitmap is None:
            return x, y
        width_scale = self._content_rect.width() / max(1, self._bitmap.width)
        height_scale = self._content_rect.height() / max(1, self._bitmap.height)
        return (
            self._content_rect.x() + x * width_scale,
            self._content_rect.y() + y * height_scale,
        )

    def _image_rect_to_widget(self, roi: RectRegion) -> tuple[float, float, float, float]:
        x1, y1 = self._image_point_to_widget(roi.x, roi.y)
        x2, y2 = self._image_point_to_widget(roi.x + roi.width, roi.y + roi.height)
        return x1, y1, x2 - x1, y2 - y1
