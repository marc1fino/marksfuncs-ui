"""Explanations, reproducible Python and the library's sampled coordinates."""

from html import escape

import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QButtonGroup, QHBoxLayout, QHeaderView, QLabel, QPlainTextEdit,
    QPushButton, QStackedWidget, QTableWidget, QTableWidgetItem,
    QTextBrowser, QVBoxLayout, QWidget,
)


class DetailsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 0, 6, 6)
        layout.setSpacing(0)
        tabs = QHBoxLayout()
        tabs.setSpacing(0)
        self.group = QButtonGroup(self)
        for index, text in enumerate(("Cómo funciona", "Código Python", "Tabla de valores")):
            button = QPushButton(text)
            button.setObjectName("Tab")
            button.setCheckable(True)
            button.setChecked(index == 0)
            self.group.addButton(button, index)
            tabs.addWidget(button)
        tabs.addStretch()
        self.copy_button = QPushButton("Copiar código")
        self.copy_button.setObjectName("Ghost")
        tabs.addWidget(self.copy_button)
        layout.addLayout(tabs)
        self.stack = QStackedWidget()
        self.explanation = QTextBrowser()
        self.explanation.setOpenExternalLinks(False)
        self.code = QPlainTextEdit()
        self.code.setReadOnly(True)
        self.code.setAccessibleName("Código Python generado con marksfuncs")
        table_page = QWidget()
        table_layout = QVBoxLayout(table_page)
        table_layout.setContentsMargins(8, 4, 8, 0)
        self.table_note = QLabel()
        self.table_note.setObjectName("Subtitle")
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["x", "f(x)"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setAccessibleName("Coordenadas devueltas por marksfuncs")
        table_layout.addWidget(self.table_note)
        table_layout.addWidget(self.table)
        for page in (self.explanation, self.code, table_page):
            self.stack.addWidget(page)
        self.group.idClicked.connect(self.stack.setCurrentIndex)
        layout.addWidget(self.stack)
        self.setMinimumHeight(155)

    def set_spec(self, spec):
        parameters = "".join(
            f"<li><b>{escape(p.key)}</b> · {escape(p.label)}. {escape(p.help)}</li>"
            for p in spec.parameters
        )
        note = f"<p style='color:#966d35'>{escape(spec.note)}</p>" if spec.note else ""
        self.explanation.setHtml(
            "<html><body style='font-family:Manrope;font-size:12px;color:#536c60'>"
            f"<p style='color:#254b41'>{escape(spec.description)}</p>"
            f"<p><b>Dominio y uso</b> · {escape(spec.domain)}</p>"
            f"<ul>{parameters}</ul>{note}</body></html>"
        )

    def set_code(self, code):
        self.code.setPlainText(code)

    def set_curve(self, curve):
        self.table.clearContents()
        if curve is None:
            self.table.setRowCount(0)
            self.table_note.setText("Calcula una función para consultar sus valores.")
            return
        series = curve.series
        headers = ["m" if curve.class_name == "Ackermann" else "x"]
        for item in series:
            headers.append("n" if curve.class_name == "Ackermann" else item.label)
            if item.colors is not None:
                headers.append("A(m, n)")
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        count = len(series[0].x)
        indices = np.unique(np.linspace(0, max(0, count - 1), min(count, 400), dtype=int))
        self.table.setRowCount(len(indices))
        for row, index in enumerate(indices):
            values = [series[0].x[index]]
            for item in series:
                values.append(item.y[index] if index < len(item.y) else np.nan)
                if item.colors is not None:
                    values.append(item.colors[index] if index < len(item.colors) else np.nan)
            for column, value in enumerate(values):
                text = f"{value:.7g}" if np.isfinite(value) else "sin valor real"
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(row, column, item)
        self.table_note.setText(f"{len(indices)} de {count} puntos · Exportar CSV guarda todas las muestras.")
