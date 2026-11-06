"""Interactive Qt rendering of samples produced by marksfuncs."""

from __future__ import annotations

import math

import numpy as np
from PyQt6.QtCore import (
    QEasingCurve,
    QPointF,
    QPropertyAnimation,
    QRectF,
    Qt,
    pyqtProperty,
    pyqtSignal,
)
from PyQt6.QtGui import QColor, QFont, QLinearGradient, QMouseEvent, QPainter, QPainterPath, QPen, QWheelEvent
from PyQt6.QtWidgets import QWidget


PALETTE = ("#087f8c", "#ce8240", "#8b6ac2", "#cc6876", "#537fb4", "#6e9357")
VALUE_PALETTE = ("#440154", "#3b528b", "#21918c", "#5ec962", "#fde725")


def _tick_step(span: float, target: int) -> float:
    raw = span / max(2, target)
    if raw == 0:
        return span
    magnitude = 10 ** max(-307, math.floor(math.log10(raw)))
    normalized = raw / magnitude
    return next(step for step in (1, 2, 2.5, 5, 10) if step >= normalized) * magnitude


def _number(value: float) -> str:
    if value == 0:
        return "0"
    return f"{value:.4g}"


class PlotWidget(QWidget):
    """Pan, zoom and inspect multiple curves without recalculating their data.

    ``set_view`` also records the view restored by ``reset_view``. Changes to
    curves preserve the camera, so adjusting a parameter does not undo a zoom.
    Nonfinite samples and large jumps across the entire viewport break paths.
    """

    viewChanged = pyqtSignal(tuple)
    cursorChanged = pyqtSignal(float, float)
    cursorLeft = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setMinimumSize(240, 220)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName("Gráfica interactiva de funciones")
        self.setAccessibleDescription(
            "Arrastra para desplazar, usa la rueda para ampliar y doble clic para restablecer."
        )
        self._curves: list[dict] = []
        self._path_cache: list[QPainterPath | None] | None = None
        self._value_bounds: tuple[float, float] | None = None
        self._axis_labels = ("x", "y")
        self._view = (-6.0, 6.0, -4.0, 4.0)
        self._default_view = self._view
        self._hover: QPointF | None = None
        self._drag_origin: QPointF | None = None
        self._drag_view = self._view
        self._reveal = 1.0
        self._animations_enabled = True
        self._animation = QPropertyAnimation(self, b"reveal", self)
        self._animation.setDuration(380)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.setCursor(Qt.CursorShape.CrossCursor)

    @property
    def view(self) -> tuple[float, float, float, float]:
        return self._view

    def _get_reveal(self) -> float:
        return self._reveal

    def _set_reveal(self, value: float) -> None:
        self._reveal = value
        self.update()

    reveal = pyqtProperty(float, _get_reveal, _set_reveal)

    def set_animations_enabled(self, enabled: bool) -> None:
        self._animations_enabled = bool(enabled)
        if not enabled:
            self.finish_animation()

    def finish_animation(self) -> None:
        """Reveal all samples before saving a static image."""
        self._animation.stop()
        self._set_reveal(1.0)

    def set_curves(self, curves: list[dict]) -> None:
        prepared = []
        for index, curve in enumerate(curves):
            x = np.asarray(curve["x"], dtype=float).reshape(-1).copy()
            y = np.asarray(curve["y"], dtype=float).reshape(-1).copy()
            if x.shape != y.shape:
                raise ValueError("Las coordenadas x e y deben tener la misma longitud.")
            values = curve.get("values")
            if values is not None:
                values = np.asarray(values, dtype=float).reshape(-1).copy()
                if values.shape != x.shape:
                    raise ValueError("Cada punto debe tener un valor de color.")
            prepared.append({
                "x": x,
                "y": y,
                "label": str(curve.get("label", f"f{index + 1}(x)")),
                "color": str(curve.get("color", PALETTE[index % len(PALETTE)])),
                "scatter": bool(curve.get("scatter", False)),
                "values": values,
            })
        self._animation.stop()
        self._curves = prepared
        self._path_cache = None
        scalar_values = [curve["values"][np.isfinite(curve["values"])]
                         for curve in prepared if curve["values"] is not None]
        scalar_values = [values for values in scalar_values if len(values)]
        self._value_bounds = (
            (min(float(values.min()) for values in scalar_values),
             max(float(values.max()) for values in scalar_values))
            if scalar_values else None
        )
        if prepared and self._animations_enabled and self.isVisible():
            self._animation.setStartValue(0.0)
            self._animation.setEndValue(1.0)
            self._animation.start()
        else:
            self._set_reveal(1.0)
        self.update()

    def set_view(self, xmin: float, xmax: float, ymin: float, ymax: float) -> None:
        bounds = tuple(float(value) for value in (xmin, xmax, ymin, ymax))
        if not all(math.isfinite(value) for value in bounds):
            raise ValueError("Los límites deben ser números finitos.")
        spans = (bounds[1] - bounds[0], bounds[3] - bounds[2])
        if not all(math.isfinite(span) and span > 0 for span in spans):
            raise ValueError("El límite superior debe ser mayor que el inferior.")
        self._default_view = bounds
        self._change_view(bounds)

    def _change_view(self, bounds: tuple) -> None:
        if not all(math.isfinite(value) for value in bounds):
            return
        if not all(math.isfinite(span) and span > 0 for span in (bounds[1] - bounds[0], bounds[3] - bounds[2])):
            return
        self._view = bounds
        self._path_cache = None
        self.viewChanged.emit(bounds)
        self.update()

    def reset_view(self) -> None:
        self._change_view(self._default_view)

    def set_axis_labels(self, horizontal: str, vertical: str) -> None:
        self._axis_labels = (str(horizontal), str(vertical))
        self.update()

    def fit_curves(self) -> None:
        samples = [
            (curve["x"][valid], curve["y"][valid])
            for curve in self._curves
            if (valid := np.isfinite(curve["x"]) & np.isfinite(curve["y"])).any()
        ]
        if not samples:
            return
        x = np.concatenate([sample[0] for sample in samples])
        y = np.concatenate([sample[1] for sample in samples])
        xmin, xmax = float(x.min()), float(x.max())
        ymin, ymax = float(y.min()), float(y.max())
        xpad = max((xmax - xmin) * 0.07, math.ulp(max(abs(xmin), abs(xmax))) * 8,
                   max(0.5, abs(xmin) * 0.05) if xmin == xmax else 0)
        ypad = max((ymax - ymin) * 0.12, math.ulp(max(abs(ymin), abs(ymax))) * 8,
                   max(0.5, abs(ymin) * 0.05) if ymin == ymax else 0)
        bounds = (xmin - xpad, xmax + xpad, ymin - ypad, ymax + ypad)
        spans = (bounds[1] - bounds[0], bounds[3] - bounds[2])
        if all(math.isfinite(value) for value in (*bounds, *spans)) and all(span > 0 for span in spans):
            self.set_view(*bounds)

    def _value_color(self, value: float) -> QColor:
        if self._value_bounds is None or not math.isfinite(value):
            return QColor("#89978f")
        low, high = self._value_bounds
        fraction = (value - low) / (high - low) if high > low else 0.5
        position = min(1.0, max(0.0, fraction)) * (len(VALUE_PALETTE) - 1)
        index = min(int(position), len(VALUE_PALETTE) - 2)
        weight = position - index
        first, second = QColor(VALUE_PALETTE[index]), QColor(VALUE_PALETTE[index + 1])
        return QColor(*(round(a + (b - a) * weight) for a, b in zip(first.getRgb()[:3], second.getRgb()[:3])))

    def _plot_rect(self) -> QRectF:
        return QRectF(62, 28, max(1, self.width() - 88), max(1, self.height() - 76))

    def _to_screen(self, x: float, y: float) -> QPointF:
        rect = self._plot_rect()
        xmin, xmax, ymin, ymax = self._view
        return QPointF(
            rect.left() + (x - xmin) / (xmax - xmin) * rect.width(),
            rect.bottom() - (y - ymin) / (ymax - ymin) * rect.height(),
        )

    def _to_data(self, point: QPointF) -> tuple[float, float]:
        rect = self._plot_rect()
        xmin, xmax, ymin, ymax = self._view
        return (
            xmin + (point.x() - rect.left()) / rect.width() * (xmax - xmin),
            ymax - (point.y() - rect.top()) / rect.height() * (ymax - ymin),
        )

    def _curve_path(self, curve: dict) -> QPainterPath:
        path = QPainterPath()
        xmin, xmax, ymin, ymax = self._view
        xspan, yspan = xmax - xmin, ymax - ymin
        previous: tuple[float, float] | None = None
        for x, y in zip(curve["x"], curve["y"]):
            if not math.isfinite(x) or not math.isfinite(y):
                previous = None
                continue
            # Keep coordinates within a safe rasterization range. This affects
            # off-canvas pixels only and never changes the library samples.
            point = self._to_screen(
                min(max(float(x), xmin - xspan), xmax + xspan),
                min(max(float(y), ymin - yspan), ymax + yspan),
            )
            discontinuity = previous is not None and (
                abs(y - previous[1]) > 2 * yspan
                and min(y, previous[1]) < ymin
                and max(y, previous[1]) > ymax
            )
            if previous is None or discontinuity:
                path.moveTo(point)
            else:
                path.lineTo(point)
            previous = (x, y)
        return path

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#fcfdfb"))
        rect = self._plot_rect()
        self._paint_grid(painter, rect)
        if self._path_cache is None:
            self._path_cache = [
                None if curve["scatter"] else self._curve_path(curve)
                for curve in self._curves
            ]
        painter.save()
        painter.setClipRect(QRectF(rect.left(), rect.top(), rect.width() * self._reveal, rect.height()))
        for index, curve in enumerate(self._curves):
            color = QColor(curve["color"])
            painter.setPen(QPen(color, 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            if curve["scatter"]:
                painter.setBrush(color)
                for sample_index, (x, y) in enumerate(zip(curve["x"], curve["y"])):
                    if math.isfinite(x) and math.isfinite(y) and self._view[0] <= x <= self._view[1] and self._view[2] <= y <= self._view[3]:
                        colored = curve["values"] is not None
                        if colored:
                            painter.setBrush(self._value_color(curve["values"][sample_index]))
                            painter.setPen(QPen(QColor("white"), 1))
                        painter.drawEllipse(self._to_screen(x, y), 6 if colored else 3.5, 6 if colored else 3.5)
            else:
                path = self._path_cache[index]
                glow = QColor(color)
                glow.setAlpha(15)
                painter.setPen(QPen(glow, 8))
                painter.drawPath(path)
                painter.setPen(QPen(color, 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
                painter.drawPath(path)
        painter.restore()
        self._paint_legend(painter, rect)
        if self._value_bounds is not None:
            self._paint_value_scale(painter, rect)
        if not self._curves:
            painter.setPen(QColor("#7e8c87"))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "Tu próxima idea empieza con una función.")
        if self._hover is not None and rect.contains(self._hover) and self._drag_origin is None:
            self._paint_hover(painter, rect)
        painter.end()

    def resizeEvent(self, event) -> None:
        self._path_cache = None
        super().resizeEvent(event)

    def _paint_grid(self, painter: QPainter, rect: QRectF) -> None:
        xmin, xmax, ymin, ymax = self._view
        xstep = _tick_step(xmax - xmin, max(3, int(rect.width() / 85)))
        ystep = _tick_step(ymax - ymin, max(3, int(rect.height() / 65)))
        font = QFont(self.font())
        font.setPointSizeF(max(8, self.font().pointSizeF() - 1))
        painter.setFont(font)
        for axis, low, high, step in (("x", xmin, xmax, xstep), ("y", ymin, ymax, ystep)):
            # A bounded tick count keeps painting predictable at any zoom level.
            minor = step / 5
            start = math.ceil(low / minor)
            end = min(math.floor(high / minor), start + 200)
            for tick_index in range(start, end + 1):
                value = tick_index * minor
                major = tick_index % 5 == 0
                zero = tick_index == 0
                painter.setPen(QPen(QColor("#b9c9c4" if zero else "#e1e9e5" if major else "#f0f4f1"), 1))
                point = self._to_screen(value, 0) if axis == "x" else self._to_screen(0, value)
                if axis == "x":
                    painter.drawLine(QPointF(point.x(), rect.top()), QPointF(point.x(), rect.bottom()))
                    label_rect = QRectF(point.x() - 34, rect.bottom() + 10, 68, 20)
                    alignment = Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop
                else:
                    painter.drawLine(QPointF(rect.left(), point.y()), QPointF(rect.right(), point.y()))
                    label_rect = QRectF(0, point.y() - 10, rect.left() - 12, 20)
                    alignment = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                if major:
                    painter.setPen(QColor("#82928b"))
                    painter.drawText(label_rect, alignment, _number(value))
        painter.setPen(QColor("#60796e"))
        painter.drawText(QRectF(rect.right() + 9, rect.bottom() - 23, 15, 20), Qt.AlignmentFlag.AlignCenter, self._axis_labels[0])
        painter.drawText(QRectF(rect.left() - 26, 2, 20, 20), Qt.AlignmentFlag.AlignCenter, self._axis_labels[1])

    def _paint_legend(self, painter: QPainter, rect: QRectF) -> None:
        if not self._curves:
            return
        columns = max(1, min(3, int(rect.width() / 170)))
        slots = columns * 2
        curves = self._curves[-slots:]
        omitted = len(self._curves) - len(curves)
        if omitted:
            curves = [{"label": f"+{omitted + 1} series", "color": "#83968b"}] + curves[1:]
        cell_width = min(250, (rect.width() - 20) / columns)
        rows = math.ceil(len(curves) / columns)
        box = QRectF(rect.left() + 8, rect.top() + 7,
                     min(columns, len(curves)) * cell_width, rows * 24 + 8)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(252, 253, 251, 230))
        painter.drawRoundedRect(box, 4, 4)
        for index, curve in enumerate(curves):
            left = box.left() + (index % columns) * cell_width + 8
            top = box.top() + (index // columns) * 24 + 4
            painter.setPen(QPen(QColor(curve["color"]), 2.5))
            painter.drawLine(QPointF(left, top + 10), QPointF(left + 13, top + 10))
            painter.setPen(QColor("#61786d"))
            text = painter.fontMetrics().elidedText(curve["label"], Qt.TextElideMode.ElideRight, max(20, int(cell_width - 35)))
            painter.drawText(QRectF(left + 20, top, cell_width - 30, 20), Qt.AlignmentFlag.AlignVCenter, text)

    def _paint_value_scale(self, painter: QPainter, rect: QRectF) -> None:
        width = min(170, rect.width() - 24)
        box = QRectF(rect.right() - width - 10, rect.bottom() - 55, width, 47)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(252, 253, 251, 235))
        painter.drawRoundedRect(box, 4, 4)
        bar = QRectF(box.left() + 8, box.top() + 6, width - 16, 8)
        gradient = QLinearGradient(bar.topLeft(), bar.topRight())
        for index, color in enumerate(VALUE_PALETTE):
            gradient.setColorAt(index / (len(VALUE_PALETTE) - 1), QColor(color))
        painter.fillRect(bar, gradient)
        low, high = self._value_bounds
        painter.setPen(QColor("#61786d"))
        text = f"Valor  {_number(low)} — {_number(high)}"
        painter.drawText(QRectF(box.left() + 8, box.top() + 20, width - 16, 20), Qt.AlignmentFlag.AlignHCenter, text)

    def _paint_hover(self, painter: QPainter, rect: QRectF) -> None:
        point = self._hover
        x, y = self._to_data(point)
        painter.save()
        painter.setClipRect(rect)
        painter.setPen(QPen(QColor("#9ab2a7"), 1, Qt.PenStyle.DashLine))
        painter.drawLine(QPointF(point.x(), rect.top()), QPointF(point.x(), rect.bottom()))
        painter.drawLine(QPointF(rect.left(), point.y()), QPointF(rect.right(), point.y()))
        for curve in self._curves:
            valid = np.isfinite(curve["x"]) & np.isfinite(curve["y"])
            if not valid.any():
                continue
            indices = np.flatnonzero(valid)
            if curve["scatter"]:
                xmin, xmax, ymin, ymax = self._view
                distances = ((curve["x"][valid] - x) * rect.width() / (xmax - xmin)) ** 2 + ((curve["y"][valid] - y) * rect.height() / (ymax - ymin)) ** 2
                index = indices[np.argmin(distances)]
            else:
                index = indices[np.argmin(np.abs(curve["x"][valid] - x))]
            sample = self._to_screen(curve["x"][index], curve["y"][index])
            if rect.contains(sample):
                painter.setPen(QPen(QColor("white"), 2))
                painter.setBrush(QColor(curve["color"]))
                painter.drawEllipse(sample, 4.5, 4.5)
        painter.restore()
        text = f"{self._axis_labels[0]}  {_number(x)}    {self._axis_labels[1]}  {_number(y)}"
        nearest_distance = 18 ** 2
        for curve in self._curves:
            if curve["values"] is None or not len(curve["x"]):
                continue
            xmin, xmax, ymin, ymax = self._view
            distances = ((curve["x"] - x) * rect.width() / (xmax - xmin)) ** 2 + ((curve["y"] - y) * rect.height() / (ymax - ymin)) ** 2
            finite = np.isfinite(distances) & np.isfinite(curve["values"])
            indices = np.flatnonzero(finite)
            if len(indices):
                nearest = indices[np.argmin(distances[finite])]
                if distances[nearest] < nearest_distance:
                    nearest_distance = distances[nearest]
                    text = (f"{self._axis_labels[0]}  {_number(curve['x'][nearest])}    "
                            f"{self._axis_labels[1]}  {_number(curve['y'][nearest])}    "
                            f"valor  {_number(curve['values'][nearest])}")
        width = painter.fontMetrics().horizontalAdvance(text) + 24
        left = max(rect.left(), min(point.x() + 15, rect.right() - width))
        top = max(rect.top(), min(point.y() - 40, rect.bottom() - 30))
        box = QRectF(left, top, width, 29)
        painter.setPen(QPen(QColor("#dce6df"), 1))
        painter.setBrush(QColor("white"))
        painter.drawRoundedRect(box, 5, 5)
        painter.setPen(QColor("#33554a"))
        painter.drawText(box, Qt.AlignmentFlag.AlignCenter, text)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._plot_rect().contains(event.position()):
            self._drag_origin = event.position()
            self._drag_view = self._view
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        self._hover = event.position()
        if self._drag_origin is not None:
            delta = event.position() - self._drag_origin
            rect = self._plot_rect()
            xmin, xmax, ymin, ymax = self._drag_view
            dx = delta.x() / rect.width() * (xmax - xmin)
            dy = delta.y() / rect.height() * (ymax - ymin)
            self._change_view((xmin - dx, xmax - dx, ymin + dy, ymax + dy))
        elif self._plot_rect().contains(event.position()):
            self.cursorChanged.emit(*self._to_data(event.position()))
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_origin = None
            self.setCursor(Qt.CursorShape.CrossCursor)
            self.update()
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_origin = None
            self.reset_view()
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:
        if not self._plot_rect().contains(event.position()):
            event.ignore()
            return
        delta = event.angleDelta().y()
        if delta == 0:
            event.ignore()
            return
        anchor_x, anchor_y = self._to_data(event.position())
        factor = 0.82 ** max(-5, min(5, delta / 120))
        xmin, xmax, ymin, ymax = self._view
        bounds = (
            anchor_x + (xmin - anchor_x) * factor,
            anchor_x + (xmax - anchor_x) * factor,
            anchor_y + (ymin - anchor_y) * factor,
            anchor_y + (ymax - anchor_y) * factor,
        )
        spans = (bounds[1] - bounds[0], bounds[3] - bounds[2])
        if not all(math.isfinite(value) for value in (*bounds, *spans)) or not all(span > 0 for span in spans):
            event.ignore()
            return
        minimum_spans = (
            max(math.ulp(xmin) * 4, math.ulp(xmax) * 4, 1e-300),
            max(math.ulp(ymin) * 4, math.ulp(ymax) * 4, 1e-300),
        )
        if spans[0] > 1e12 or factor < 1 and any(span <= minimum for span, minimum in zip(spans, minimum_spans)):
            event.ignore()
            return
        self._change_view(bounds)
        event.accept()

    def leaveEvent(self, event) -> None:
        self._hover = None
        self.cursorLeft.emit()
        self.update()
        super().leaveEvent(event)

    def hideEvent(self, event) -> None:
        self._animation.stop()
        self._set_reveal(1.0)
        super().hideEvent(event)

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key.Key_Home, Qt.Key.Key_0):
            self.reset_view()
            event.accept()
        else:
            super().keyPressEvent(event)
