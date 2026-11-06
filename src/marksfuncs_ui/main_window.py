"""Desktop workspace: function discovery, visual assignment and comparison."""

import copy
import csv
from importlib.metadata import version
from pathlib import Path

import numpy as np
from PyQt6.QtCore import QSize, Qt, QSettings, QTimer
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QFileDialog, QFrame, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMessageBox,
    QPushButton, QScrollArea, QSplitter, QVBoxLayout, QWidget,
)

from .catalog import BY_KEY, CATALOG
from .controls import ParameterPanel, RangePanel
from .details import DetailsPanel
from .engine import compute_curve, generate_code, unavailable_reason
from .plot_widget import PlotWidget
from .session import load_session, save_session
from .theme import app_icon


COLORS = ("#ce9240", "#9371b2", "#498fb2", "#cb7383")


def label(text="", name="", wrap=False):
    widget = QLabel(text)
    widget.setObjectName(name)
    widget.setWordWrap(wrap)
    if wrap:
        widget.setMinimumWidth(0)
    return widget


def button(text, callback, name=""):
    widget = QPushButton(text)
    widget.setObjectName(name)
    widget.setCursor(Qt.CursorShape.PointingHandCursor)
    widget.clicked.connect(callback)
    return widget


def divider():
    widget = QFrame()
    widget.setObjectName("Divider")
    widget.setFixedHeight(1)
    return widget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("marksfuncs Studio · Laboratorio de funciones")
        self.setWindowIcon(app_icon())
        self.resize(1480, 920)
        self.setMinimumSize(1080, 720)
        self.settings = QSettings()
        self.spec = None
        self.function_states = {}
        self.comparisons = []
        self.current_curve = None
        self._curve_state = None
        self.code_valid = False
        self.comparison_curves = []
        self.dirty = False
        self.session_path = None
        self._selecting = False
        self._fit_next = True
        self.debounce = QTimer(self)
        self.debounce.setSingleShot(True)
        self.debounce.setInterval(180)
        self.debounce.timeout.connect(self.calculate)
        self._build_ui()
        self._shortcuts()
        self._populate_catalog()
        self._select_key("Trigonometric")
        self.statusBar().showMessage(f"marksfuncs {version('marksfuncs')} · Cálculos de tu librería · Todo en tu equipo")

    def _build_ui(self):
        workspace = QWidget()
        outer = QVBoxLayout(workspace)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        header = QFrame()
        header.setObjectName("Header")
        row = QHBoxLayout(header)
        row.setContentsMargins(22, 17, 24, 17)
        row.setSpacing(12)
        icon = QLabel()
        icon.setPixmap(app_icon().pixmap(QSize(34, 34)))
        row.addWidget(icon)
        row.addWidget(label("marksfuncs", "Brand"))
        row.addWidget(label("/  STUDIO", "Eyebrow"))
        row.addStretch()
        row.addWidget(label("UN ESPACIO PARA ENTENDER FUNCIONES", "Eyebrow"))
        row.addSpacing(22)
        row.addWidget(button("Abrir sesión", self.open_project, "Ghost"))
        row.addWidget(button("Guardar sesión", self.save_project))
        outer.addWidget(header)

        body = QSplitter(Qt.Orientation.Horizontal)
        body.setChildrenCollapsible(False)
        body.setHandleWidth(1)
        body.addWidget(self._build_sidebar())
        body.addWidget(self._build_center())
        body.addWidget(self._build_inspector())
        body.setStretchFactor(0, 0)
        body.setStretchFactor(1, 1)
        body.setStretchFactor(2, 0)
        body.setSizes([235, 930, 315])
        outer.addWidget(body, 1)
        self.setCentralWidget(workspace)

    def _build_sidebar(self):
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setMinimumWidth(205)
        sidebar.setMaximumWidth(310)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(8, 24, 8, 16)
        layout.setSpacing(10)
        top = QHBoxLayout()
        top.setContentsMargins(14, 0, 12, 4)
        top.addWidget(label("EXPLORAR", "Section"))
        top.addStretch()
        top.addWidget(label(str(len(CATALOG)), "Badge"))
        layout.addLayout(top)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Buscar una función…")
        self.search.setAccessibleName("Buscar funciones")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._populate_catalog)
        layout.addWidget(self.search)
        self.catalog_list = QListWidget()
        self.catalog_list.setAccessibleName("Catálogo de funciones")
        self.catalog_list.currentItemChanged.connect(self._catalog_changed)
        layout.addWidget(self.catalog_list, 1)
        self.search_empty = label("No hay funciones con ese nombre.", "Subtitle", True)
        self.search_empty.hide()
        layout.addWidget(self.search_empty)
        layout.addWidget(divider())
        layout.addWidget(label("De una idea\na una curva.", "Formula"))
        layout.addWidget(label("Explora · ajusta · comprende", "Subtitle"))
        layout.addWidget(button("Guía y atajos   ↗", self.show_guide, "Ghost"))
        return sidebar

    def _build_center(self):
        center = QWidget()
        center.setMinimumWidth(475)
        layout = QVBoxLayout(center)
        layout.setContentsMargins(26, 23, 26, 20)
        layout.setSpacing(13)
        title_row = QHBoxLayout()
        title_row.addWidget(label("LABORATORIO DE FUNCIONES", "Eyebrow"))
        title_row.addStretch()
        self.category = label("", "Badge")
        title_row.addWidget(self.category)
        layout.addLayout(title_row)
        self.title = label("", "Title")
        layout.addWidget(self.title)
        self.subtitle = label("", "Subtitle", True)
        layout.addWidget(self.subtitle)
        self.error_label = label("", "Error", True)
        self.error_label.hide()
        layout.addWidget(self.error_label)

        vertical = QSplitter(Qt.Orientation.Vertical)
        vertical.setChildrenCollapsible(False)
        vertical.setHandleWidth(8)
        plot_card = QFrame()
        plot_card.setObjectName("PlotCard")
        plot_layout = QVBoxLayout(plot_card)
        plot_layout.setContentsMargins(14, 12, 14, 10)
        plot_layout.setSpacing(4)
        plot_top = QHBoxLayout()
        self.formula = label("", "Formula")
        self.formula.setWordWrap(True)
        plot_top.addWidget(self.formula, 1)
        plot_top.addWidget(button("Centrar", self.fit_view, "Ghost"))
        export = button("Exportar…", self.export_menu)
        export.setAccessibleName("Exportar gráfica, datos o código")
        plot_top.addWidget(export)
        plot_layout.addLayout(plot_top)
        self.plot = PlotWidget()
        self.plot.setMinimumHeight(180)
        plot_layout.addWidget(self.plot, 1)
        plot_bottom = QHBoxLayout()
        self.graph_info = label("", "Subtitle")
        plot_bottom.addWidget(self.graph_info)
        plot_bottom.addStretch()
        plot_bottom.addWidget(label("Arrastra para mover · rueda para ampliar", "Subtitle"))
        plot_layout.addLayout(plot_bottom)
        vertical.addWidget(plot_card)
        detail_card = QFrame()
        detail_card.setObjectName("DetailCard")
        detail_layout = QVBoxLayout(detail_card)
        detail_layout.setContentsMargins(2, 0, 2, 2)
        self.details = DetailsPanel()
        self.details.copy_button.clicked.connect(self.copy_code)
        detail_layout.addWidget(self.details)
        vertical.addWidget(detail_card)
        vertical.setSizes([470, 220])
        layout.addWidget(vertical, 1)
        self.sample_info = label("", "Subtitle")
        layout.addWidget(self.sample_info)
        return center

    def _build_inspector(self):
        inspector = QFrame()
        inspector.setObjectName("Inspector")
        inspector.setMinimumWidth(270)
        inspector.setMaximumWidth(390)
        layout = QVBoxLayout(inspector)
        layout.setContentsMargins(18, 24, 18, 16)
        layout.setSpacing(12)
        top = QHBoxLayout()
        top.addWidget(label("VARIABLES", "Section"))
        top.addStretch()
        top.addWidget(button("Restablecer", self.reset_parameters, "Ghost"))
        layout.addLayout(top)
        layout.addWidget(label("Asigna valores. Observa el cambio.", "Subtitle"))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        controls_layout = QVBoxLayout(content)
        controls_layout.setContentsMargins(0, 0, 3, 8)
        controls_layout.setSpacing(15)
        self.parameters = ParameterPanel()
        self.parameters.valueChanged.connect(self._edited)
        controls_layout.addWidget(self.parameters)
        controls_layout.addWidget(divider())
        controls_layout.addWidget(label("INTERVALO Y PRECISIÓN", "Section"))
        self.range_panel = RangePanel()
        self.range_panel.changed.connect(self._range_edited)
        controls_layout.addWidget(self.range_panel)
        controls_layout.addWidget(divider())
        self.live = QCheckBox("Actualizar al cambiar valores")
        self.live.setChecked(True)
        self.live.toggled.connect(lambda checked: self._schedule() if checked else self.debounce.stop())
        controls_layout.addWidget(self.live)
        self.animations = QCheckBox("Animar las curvas")
        self.animations.setChecked(self.settings.value("animations", True, type=bool))
        self.plot.set_animations_enabled(self.animations.isChecked())
        self.animations.toggled.connect(self._set_animations)
        controls_layout.addWidget(self.animations)
        controls_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)
        self.calculate_button = button("Trazar función    ↗", self.calculate, "Primary")
        layout.addWidget(self.calculate_button)
        self.pin_button = button("+  Fijar para comparar", self.pin_curve)
        layout.addWidget(self.pin_button)
        layout.addWidget(divider())
        comparison_header = QHBoxLayout()
        comparison_header.addWidget(label("COMPARACIÓN", "Section"))
        comparison_header.addStretch()
        comparison_header.addWidget(button("Vaciar", self.clear_comparisons, "Ghost"))
        layout.addLayout(comparison_header)
        self.comparison_list = QVBoxLayout()
        self.comparison_list.setSpacing(3)
        layout.addLayout(self.comparison_list)
        self.comparison_note = label("Fija una curva y cambia sus variables\npara ver las diferencias.", "Subtitle", True)
        layout.addWidget(self.comparison_note)
        return inspector

    def _shortcuts(self):
        for shortcut, callback in (
            ("Ctrl+Return", self.calculate), ("Ctrl+R", self.reset_parameters),
            ("Ctrl+0", self.fit_view), ("Ctrl+S", self.save_project),
            ("Ctrl+O", self.open_project), ("F1", self.show_guide),
            ("Ctrl+F", self.search.setFocus),
        ):
            action = QAction(self)
            action.setShortcut(QKeySequence(shortcut))
            action.triggered.connect(callback)
            self.addAction(action)

    def _populate_catalog(self, query=""):
        selected = self.spec.key if self.spec else None
        self.catalog_list.blockSignals(True)
        self.catalog_list.clear()
        categories = {}
        for spec in CATALOG:
            if query.casefold() in f"{spec.name} {spec.key} {spec.category} {spec.description}".casefold():
                categories.setdefault(spec.category, []).append(spec)
        for category, specs in categories.items():
            heading = QListWidgetItem(category.upper())
            heading.setFlags(Qt.ItemFlag.NoItemFlags)
            self.catalog_list.addItem(heading)
            for spec in specs:
                item = QListWidgetItem(spec.name)
                item.setData(Qt.ItemDataRole.UserRole, spec.key)
                item.setToolTip(f"{spec.key} · {spec.formula}")
                self.catalog_list.addItem(item)
                if spec.key == selected:
                    self.catalog_list.setCurrentItem(item)
        self.catalog_list.blockSignals(False)
        self.search_empty.setVisible(not categories)

    def _select_key(self, key):
        self.select_function(key)
        self._populate_catalog(self.search.text())

    def _catalog_changed(self, item, previous):
        if item and item.data(Qt.ItemDataRole.UserRole):
            self.select_function(item.data(Qt.ItemDataRole.UserRole))

    def snapshot(self):
        x_range, points = self.range_panel.values()
        return {"parameters": self.parameters.values(), "x_range": list(x_range), "points": points}

    def select_function(self, key):
        if self.spec:
            self.function_states[self.spec.key] = self.snapshot()
            if self.spec.key != key:
                self.dirty = True
        self.debounce.stop()
        self._selecting = True
        self.spec = BY_KEY[key]
        state = self.function_states.get(key)
        self.parameters.set_spec(self.spec, state["parameters"] if state else None)
        self.range_panel.set_values(state["x_range"] if state else self.spec.x_range,
                                    state["points"] if state else self.spec.points)
        self.title.setText(self.spec.name)
        self.category.setText(self.spec.category)
        self.subtitle.setText(f"{self.spec.key}  /  Explora su comportamiento con tus propios valores.")
        self.formula.setText(self.spec.formula)
        axes = ("m", "n") if key == "Ackermann" else ("x", "f(x)")
        self.plot.set_axis_labels(*axes)
        self.details.set_spec(self.spec)
        self.calculate_button.setEnabled(not unavailable_reason(self.spec))
        self._selecting = False
        self._fit_next = True
        self.calculate()

    def _set_animations(self, enabled):
        self.plot.set_animations_enabled(enabled)
        self.settings.setValue("animations", enabled)

    def _range_edited(self):
        self._fit_next = True
        self._edited()

    def _edited(self):
        if self._selecting:
            return
        self.dirty = True
        self.current_curve = None
        self.details.set_curve(None)
        self._render_curves()
        self.sample_info.setText("Variables modificadas · Traza la función para obtener nuevas muestras.")
        self.pin_button.setEnabled(False)
        self.graph_info.setText("Cambios pendientes de trazar")
        self._update_code()
        self._schedule()

    def _schedule(self):
        if self.live.isChecked() and not self._selecting:
            self.debounce.start()

    def _update_code(self):
        if self.spec is None:
            return
        try:
            state = self.snapshot()
            code = generate_code(self.spec, state["parameters"], state["x_range"], state["points"], variable_name="f")
            self.details.set_code(code)
            self.code_valid = True
        except (ValueError, TypeError) as error:
            self.details.set_code(f"# Revisa las variables: {error}")
            self.code_valid = False
        self.details.copy_button.setEnabled(self.code_valid)

    def calculate(self):
        if self.spec is None:
            return
        self.debounce.stop()
        self._update_code()
        state = self.snapshot()
        self.function_states[self.spec.key] = state
        try:
            self.current_curve = compute_curve(self.spec, state["parameters"], state["x_range"], state["points"])
            self._curve_state = copy.deepcopy(state)
        except Exception as error:
            self.current_curve = None
            self._curve_state = None
            self.details.set_curve(None)
            self.error_label.setText(f"No se pudo trazar {self.spec.key}: {error}")
            self.error_label.show()
            self.graph_info.setText("Revisa los parámetros o el dominio")
            self.sample_info.setText("La librería no ha devuelto una curva válida para estos valores.")
            self.pin_button.setEnabled(False)
            self._render_curves()
            return
        self.pin_button.setEnabled(len(self.comparisons) < 4)
        warnings = self.current_curve.warnings
        self.error_label.setText(" · ".join(warnings))
        self.error_label.setVisible(bool(warnings))
        self.details.set_curve(self.current_curve)
        self._render_curves()
        if self._fit_next:
            self.fit_view()
            self._fit_next = False
        count = len(self.current_curve.x)
        self.graph_info.setText(f"{self.spec.key}   ·   {count:,} muestras".replace(",", " "))
        values = self.current_curve.series[0].colors if self.spec.key == "Ackermann" else self.current_curve.y
        finite = np.asarray(values)[np.isfinite(values)]
        self.sample_info.setText(
            f"DATOS DE MARKSFUNCS     mín. muestreado  {finite.min():.5g}     máx. muestreado  {finite.max():.5g}"
            if len(finite) else "No hay valores reales finitos en este intervalo."
        )

    def _render_curves(self):
        curves = []
        for index, curve in enumerate(self.comparison_curves):
            for series in curve.series:
                curves.append({"x": series.x, "y": series.y, "label": series.label,
                               "scatter": series.scatter, "color": COLORS[index], "values": series.colors})
        if self.current_curve:
            for index, series in enumerate(self.current_curve.series):
                curves.append({"x": series.x, "y": series.y, "label": series.label,
                               "scatter": series.scatter, "color": ("#087f8c", "#478eb7")[index % 2], "values": series.colors})
        self.plot.set_curves(curves)

    def fit_view(self):
        self.plot.fit_curves()

    def reset_parameters(self):
        if self.spec:
            self.parameters.set_spec(self.spec)
            self.range_panel.set_values(self.spec.x_range, self.spec.points)
            self._fit_next = True
            self.dirty = True
            self.calculate()

    def pin_curve(self):
        if self.current_curve is not None and self.snapshot() != self._curve_state:
            self.dirty = True
            self.calculate()
        if not self.current_curve or len(self.comparisons) >= 4:
            return
        self.comparisons.append({"key": self.spec.key, **copy.deepcopy(self.snapshot())})
        self.comparison_curves.append(self.current_curve)
        self.dirty = True
        self._refresh_comparisons()
        self._render_curves()

    def _refresh_comparisons(self):
        while self.comparison_list.count():
            item = self.comparison_list.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for index, snapshot in enumerate(self.comparisons):
            text = f"{index + 1}.  {BY_KEY[snapshot['key']].name}  ×"
            chip = button(text, lambda checked=False, i=index: self.remove_comparison(i), "Ghost")
            chip.setStyleSheet(f"color: {COLORS[index]}; text-align: left;")
            chip.setToolTip(f"{snapshot['parameters']}\nClic para retirar esta curva")
            chip.setAccessibleName(f"Retirar comparación {index + 1}: {snapshot['key']}")
            self.comparison_list.addWidget(chip)
        self.comparison_note.setVisible(not self.comparisons)
        self.pin_button.setEnabled(self.current_curve is not None and len(self.comparisons) < 4)

    def remove_comparison(self, index):
        self.comparisons.pop(index)
        self.comparison_curves.pop(index)
        self.dirty = True
        self._refresh_comparisons()
        self._render_curves()

    def clear_comparisons(self):
        self.comparisons.clear()
        self.comparison_curves.clear()
        self.dirty = True
        self._refresh_comparisons()
        self._render_curves()

    def project_state(self):
        self.function_states[self.spec.key] = self.snapshot()
        return {"version": 1, "selected": self.spec.key,
                "functions": copy.deepcopy(self.function_states), "comparisons": copy.deepcopy(self.comparisons)}

    def save_project(self):
        path, _ = QFileDialog.getSaveFileName(self, "Guardar sesión", self.session_path or "mi-laboratorio.mfuncs", "Sesión marksfuncs (*.mfuncs)")
        if not path:
            return False
        try:
            save_session(path, self.project_state())
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "No se pudo guardar", str(error))
            return False
        self.session_path = path
        self.dirty = False
        self.statusBar().showMessage(f"Sesión guardada en {path}", 6000)
        return True

    def _confirm_discard(self):
        if self.spec and self.snapshot() != self.function_states.get(self.spec.key):
            self.dirty = True
        if not self.dirty:
            return True
        answer = QMessageBox.question(self, "Cambios sin guardar", "¿Quieres guardar tus variables y comparaciones antes de continuar?",
                                      QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel)
        if answer == QMessageBox.StandardButton.Save:
            return self.save_project()
        return answer == QMessageBox.StandardButton.Discard

    def open_project(self):
        if not self._confirm_discard():
            return
        path, _ = QFileDialog.getOpenFileName(self, "Abrir sesión", "", "Sesión marksfuncs (*.mfuncs *.json)")
        if not path:
            return
        try:
            state = load_session(path)
            curves = [compute_curve(s["key"], s["parameters"], s["x_range"], s["points"]) for s in state["comparisons"]]
        except (OSError, ValueError, RuntimeError) as error:
            QMessageBox.warning(self, "No se pudo abrir", str(error))
            return
        self.spec = None
        self.function_states = state["functions"]
        self.comparisons = state["comparisons"]
        self.comparison_curves = curves
        self.session_path = path
        self._select_key(state["selected"])
        self._refresh_comparisons()
        self.dirty = False
        self.statusBar().showMessage(f"Sesión recuperada: {Path(path).name}", 6000)

    def copy_code(self):
        self._update_code()
        if not self.code_valid:
            return
        QApplication.clipboard().setText(self.details.code.toPlainText())
        self.statusBar().showMessage("Código Python copiado", 3000)

    def export_menu(self):
        from PyQt6.QtWidgets import QMenu
        menu = QMenu(self)
        for text, kind in (("Gráfica como PNG", "png"), ("Muestras como CSV", "csv"), ("Código Python", "py")):
            action = menu.addAction(text)
            action.setEnabled(not unavailable_reason(self.spec) and (kind == "py" or self.current_curve is not None))
            action.triggered.connect(lambda checked=False, k=kind: self.export_file(k))
        menu.exec(self.cursor().pos())

    def export_file(self, kind):
        state = self.snapshot()
        if state != self.function_states.get(self.spec.key):
            self.dirty = True
        if kind == "py":
            self._update_code()
            if not self.code_valid:
                QMessageBox.warning(self, "Revisa las variables", "El código necesita parámetros válidos para poder exportarse.")
                return
        elif state != self._curve_state:
            self.calculate()
        if kind != "py" and self.current_curve is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Exportar", f"{self.spec.key}.{kind}", f"{kind.upper()} (*.{kind})")
        if not path:
            return
        try:
            if kind == "png":
                self.plot.finish_animation()
                if not self.plot.grab().save(path, "PNG"):
                    raise OSError("No se pudo escribir la imagen.")
            elif kind == "py":
                Path(path).write_text(self.details.code.toPlainText(), encoding="utf-8")
            elif kind == "csv" and self.current_curve:
                series = self.current_curve.series
                with open(path, "w", newline="", encoding="utf-8") as stream:
                    writer = csv.writer(stream)
                    headers = ["m" if self.spec.key == "Ackermann" else "x"]
                    for item in series:
                        headers.append("n" if self.spec.key == "Ackermann" else item.label)
                        if item.colors is not None:
                            headers.append("A(m, n)")
                    writer.writerow(headers)
                    for index, x in enumerate(series[0].x):
                        row = [x]
                        for item in series:
                            row.append(item.y[index] if index < len(item.y) else "")
                            if item.colors is not None:
                                row.append(item.colors[index] if index < len(item.colors) else "")
                        writer.writerow(row)
        except OSError as error:
            QMessageBox.warning(self, "No se pudo exportar", str(error))
            return
        self.statusBar().showMessage(f"Exportado: {path}", 5000)

    def show_guide(self):
        QMessageBox.information(self, "Tu laboratorio de funciones",
            "1. Elige una función en el catálogo o búscala con Ctrl+F.\n"
            "2. Asigna variables con los deslizadores o escribe valores exactos.\n"
            "3. Ajusta el intervalo de x y el número de muestras.\n"
            "4. Fija hasta cuatro curvas para compararlas.\n\n"
            "La gráfica usa las muestras de marksfuncs. Los valores fuera del dominio real se muestran como huecos. "
            "Cambiar la vista no vuelve a muestrear: ajusta el intervalo para ampliar el dominio calculado.\n\n"
            "Ctrl+Enter: trazar · Ctrl+R: restablecer variables\n"
            "Ctrl+0: centrar vista · Ctrl+S: guardar · Ctrl+O: abrir\n"
            "F1: esta guía · Doble clic en la gráfica: restablecer vista\n\n"
            "Cómo funciona explica cada clase. Código Python reproduce la función activa. "
            "CSV exporta sus muestras y PNG la vista con las comparaciones. Las sesiones conservan tus variables.")

    def closeEvent(self, event):
        if self._confirm_discard():
            event.accept()
        else:
            event.ignore()
