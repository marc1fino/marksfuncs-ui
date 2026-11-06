"""Accessible, linked controls for assigning marksfuncs constructor values."""

from __future__ import annotations

import math

from PyQt6.QtCore import QSignalBlocker, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractSpinBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


def _label(text: str, name: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName(name)
    return label


def _format_number(value: float) -> str:
    return f"{value:g}"


class _DecimalSpinBox(QDoubleSpinBox):
    def textFromValue(self, value: float) -> str:
        text = super().textFromValue(value)
        decimal = self.locale().decimalPoint()
        return text.rstrip(self.locale().zeroDigit()).rstrip(decimal) if decimal in text else text


def _number_input(integer: bool = False) -> QSpinBox | QDoubleSpinBox:
    control = QSpinBox() if integer else _DecimalSpinBox()
    if isinstance(control, QDoubleSpinBox):
        control.setDecimals(8)
    control.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.UpDownArrows)
    control.setAlignment(Qt.AlignmentFlag.AlignRight)
    control.setKeyboardTracking(False)
    # Long decimal ranges must not force the inspector wider than its column.
    control.setMinimumWidth(0)
    control.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
    return control


def _committed_value(control: QSpinBox | QDoubleSpinBox) -> int | float:
    # A shortcut can read a focused editor before Qt receives editingFinished.
    # Commit its text silently so taking a snapshot cannot reenter calculation.
    with QSignalBlocker(control):
        control.interpretText()
    return control.value()


def _sync_slider(slider: QSlider, number: int | float, parameter) -> None:
    span = parameter.maximum - parameter.minimum
    position = round((number - parameter.minimum) / span * slider.maximum()) if span else 0
    with QSignalBlocker(slider):
        slider.setValue(position)


class ParameterPanel(QWidget):
    """One visual row per parameter; read exact edited values with ``values``."""

    valueChanged = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.controls: dict[str, QSpinBox | QDoubleSpinBox | QLineEdit] = {}
        self.sliders: dict[str, QSlider] = {}
        self._spec = None
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(18)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

    def set_spec(self, spec, values: dict | None = None) -> None:
        """Build controls without emitting an edit signal or altering ``spec``."""
        self._spec = spec
        self.controls.clear()
        self.sliders.clear()
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget() is not None:
                item.widget().hide()
                item.widget().deleteLater()
        assigned = spec.defaults()
        if values is not None:
            assigned.update(values)
        for parameter in spec.parameters:
            row = self._parameter_row(parameter, assigned[parameter.key])
            self._layout.addWidget(row)
        if not spec.parameters:
            note = _label("No parameters.", "ParamHelp")
            note.setWordWrap(True)
            self._layout.addWidget(note)

    def _parameter_row(self, parameter, value) -> QWidget:
        row = QWidget()
        row.setObjectName("ParameterRow")
        layout = QVBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(7)
        heading = QHBoxLayout()
        heading.setSpacing(8)
        symbols = {"alpha": "α", "beta": "β", "mu": "μ", "sigma": "σ", "theta": "θ",
                   "lambda_param": "λ", "coefficients": "aᵢ", "polynomial_str": "p(x)",
                   "expression": "f(x)", "grade": "n", "vmax": "Vₘₐₓ"}
        symbol = _label(symbols.get(parameter.key, parameter.key), "ParamSymbol")
        symbol.setFixedWidth(35)
        symbol.setToolTip(parameter.key)
        heading.addWidget(symbol)
        title = _label(parameter.label, "ParamLabel")
        title.setWordWrap(True)
        title.setMinimumWidth(0)
        title.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        heading.addWidget(title, 1)
        kind = getattr(parameter, "kind", "number")
        if kind in ("text", "coefficients") or isinstance(parameter.default, str):
            control = QLineEdit(str(value))
            control.setObjectName("ExpressionInput")
            control.setClearButtonEnabled(True)
            control.setAccessibleName(parameter.label)
            control.setToolTip(parameter.help)
            title.setBuddy(control)
            layout.addLayout(heading)
            layout.addWidget(control)
            control.textChanged.connect(lambda _text: self.valueChanged.emit())
        else:
            control = _number_input(parameter.integer)
            if parameter.integer:
                control.setRange(math.ceil(parameter.minimum), math.floor(parameter.maximum))
                control.setSingleStep(max(1, round(parameter.step)))
                control.setValue(round(value))
            else:
                control.setRange(parameter.minimum, parameter.maximum)
                control.setSingleStep(parameter.step)
                control.setValue(value)
            control.setObjectName("ParameterValue")
            control.setFixedWidth(100)
            control.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            control.setAccessibleName(parameter.label)
            control.setToolTip(parameter.help)
            title.setBuddy(control)
            heading.addWidget(control)
            layout.addLayout(heading)
            slider_row = QHBoxLayout()
            slider_row.setSpacing(8)
            slider_row.addWidget(_label(_format_number(parameter.minimum), "ParamEndpoint"))
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setObjectName("ParameterSlider")
            slider.setAccessibleName(f"Adjust {parameter.label}")
            slider.setToolTip(parameter.help)
            span = parameter.maximum - parameter.minimum
            # Limit slider resolution; manual numeric edits retain their own precision.
            ticks = max(1, min(10000, int(math.ceil(span / parameter.step)))) if span else 1
            slider.setRange(0, ticks)

            _sync_slider(slider, control.value(), parameter)
            slider.setEnabled(span > 0)

            def numeric_changed(number):
                _sync_slider(slider, number, parameter)
                self.valueChanged.emit()

            def slider_changed(position):
                number = parameter.minimum + span * position / ticks
                if parameter.integer:
                    number = round(number)
                else:
                    # Remove binary rounding tails from slider-produced values.
                    number = round(number, 8)
                control.setValue(number)

            control.valueChanged.connect(numeric_changed)
            slider.valueChanged.connect(slider_changed)
            slider_row.addWidget(slider, 1)
            slider_row.addWidget(_label(_format_number(parameter.maximum), "ParamEndpoint"))
            layout.addLayout(slider_row)
            self.sliders[parameter.key] = slider
        if parameter.help:
            help_text = _label(parameter.help, "ParamHelp")
            help_text.setWordWrap(True)
            layout.addWidget(help_text)
        self.controls[parameter.key] = control
        return row

    def values(self) -> dict:
        """Return constructor-ready values, including raw expression text."""
        values = {}
        for parameter in self._spec.parameters if self._spec is not None else ():
            control = self.controls[parameter.key]
            if isinstance(control, QLineEdit):
                values[parameter.key] = control.text()
            else:
                values[parameter.key] = _committed_value(control)
                _sync_slider(self.sliders[parameter.key], values[parameter.key], parameter)
        return values

    def reset_defaults(self) -> None:
        if self._spec is not None:
            self.set_spec(self._spec)
            self.valueChanged.emit()


class RangePanel(QWidget):
    """Editable sampling interval and resolution, validated by the engine."""

    changed = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(9)
        bounds = QHBoxLayout()
        bounds.setSpacing(10)
        self.x_min = _number_input()
        self.x_max = _number_input()
        for text, control in (("x min", self.x_min), ("x max", self.x_max)):
            column = QVBoxLayout()
            column.setSpacing(5)
            label = _label(text, "ParamHelp")
            label.setBuddy(control)
            column.addWidget(label)
            control.setRange(-1_000_000, 1_000_000)
            control.setSingleStep(1)
            control.setAccessibleName(text)
            column.addWidget(control)
            bounds.addLayout(column, 1)
        layout.addLayout(bounds)
        sampling = QHBoxLayout()
        label = _label("Samples", "ParamLabel")
        sampling.addWidget(label, 1)
        self.points = _number_input(integer=True)
        self.points.setRange(2, 4000)
        self.points.setSingleStep(50)
        self.points.setFixedWidth(100)
        self.points.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.points.setAccessibleName("Sample count")
        self.points.setToolTip("Number of samples calculated by marksfuncs within the interval.")
        label.setBuddy(self.points)
        sampling.addWidget(self.points)
        layout.addLayout(sampling)
        self.set_values((-10, 10), 401)
        for control in (self.x_min, self.x_max, self.points):
            control.valueChanged.connect(lambda _value: self.changed.emit())

    def values(self) -> tuple[tuple[float, float], int]:
        return (_committed_value(self.x_min), _committed_value(self.x_max)), _committed_value(self.points)

    def set_values(self, x_range: tuple[float, float], points: int) -> None:
        """Restore controls without queuing a new calculation."""
        for control, value in zip((self.x_min, self.x_max, self.points), (*x_range, points)):
            previous = control.blockSignals(True)
            control.setValue(value)
            control.blockSignals(previous)
