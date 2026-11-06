"""End-to-end native workspace behavior against the installed marksfuncs."""

import copy
import csv
import json
import os
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
from PyQt6.QtCore import QPoint, QLocale, Qt
from PyQt6.QtGui import QCloseEvent, QColor, QImage, QPalette
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QLabel, QLineEdit, QMessageBox,
    QPushButton, QScrollArea,
)

from marksfuncs_ui.catalog import CATALOG
from marksfuncs_ui.engine import CalculationError, unavailable_reason
from marksfuncs_ui.main_window import MainWindow
from marksfuncs_ui.theme import STYLE, load_fonts


class MainWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.previous_identity = (cls.app.organizationName(), cls.app.applicationName())
        cls.app.setOrganizationName("marksfuncs-test-suite")
        cls.app.setApplicationName("native-workspace-tests")
        load_fonts()
        cls.app.setStyleSheet(STYLE)

    @classmethod
    def tearDownClass(cls):
        cls.app.setOrganizationName(cls.previous_identity[0])
        cls.app.setApplicationName(cls.previous_identity[1])

    def setUp(self):
        self.files = tempfile.TemporaryDirectory()
        self.window = MainWindow()
        self.window.animations.setChecked(False)
        self.window.show()
        self.app.processEvents()

    def tearDown(self):
        self.window.debounce.stop()
        self.window.dirty = False
        with patch.object(self.window, "_confirm_discard", return_value=True):
            self.window.close()
        self.window.deleteLater()
        self.app.processEvents()
        self.files.cleanup()

    def path(self, name):
        return Path(self.files.name) / name

    def export(self, kind, name):
        path = self.path(name)
        with patch("marksfuncs_ui.main_window.QFileDialog.getSaveFileName", return_value=(str(path), "")):
            self.window.export_file(kind)
        self.assertTrue(path.is_file())
        return path

    def save_clean_linear(self):
        self.window.select_function("Linear")
        self.window.reset_parameters()
        self.window.live.setChecked(False)
        path = self.path("saved-clean.mfuncs")
        with patch("marksfuncs_ui.main_window.QFileDialog.getSaveFileName", return_value=(str(path), "")):
            self.assertTrue(self.window.save_project())
        self.assertFalse(self.window.dirty)

    def type_pending_number(self, control, text):
        scroll = next(area for area in self.window.findChildren(QScrollArea)
                      if area.widget().isAncestorOf(control))
        scroll.ensureWidgetVisible(control)
        self.app.processEvents()
        control.setLocale(QLocale.c())
        control.setFocus()
        control.selectAll()
        QTest.keyClicks(control, text)

    def assert_english_page(self):
        self.app.processEvents()
        spanish_copy = re.compile(
            r"\b(?:función|funciones|muestras|gráfica|calcular|guardar|abrir|"
            r"restablecer|comportamiento|explora|laboratorio|polinomio|pendiente|"
            r"amplitud|sucesiones|señales|parámetros)\b|"
            r"de una idea|asigna valores|observa el cambio|dominio y uso|"
            r"sin valor real|coordenadas devueltas|no implementa graph",
            re.IGNORECASE,
        )
        texts = [self.window.details.explanation.toPlainText(), self.window.windowTitle()]
        for widget in self.window.findChildren((QLabel, QPushButton, QCheckBox, QLineEdit)):
            texts.extend((widget.text(), widget.toolTip(), widget.accessibleName()))
            if isinstance(widget, QLineEdit):
                texts.append(widget.placeholderText())
        self.assertIsNone(spanish_copy.search("\n".join(texts)))
        self.assertEqual(self.window.title.font().family(), "Space Grotesk")
        for control in (*self.window.parameters.controls.values(), self.window.range_panel.x_min,
                        self.window.range_panel.x_max, self.window.range_panel.points,
                        self.window.live, self.window.animations, self.window.calculate_button):
            self.assertEqual(control.font().family(), "Manrope")

    def test_all_functions_select_with_real_curve_or_explicit_upstream_limitation(self):
        for spec in CATALOG:
            with self.subTest(function=spec.key):
                self.window.select_function(spec.key)
                self.assertEqual(self.window.spec.key, spec.key)
                self.assertEqual(self.window.title.text(), spec.name)
                self.assertIn(spec.description, self.window.details.explanation.toPlainText())
                self.assert_english_page()
                if unavailable_reason(spec):
                    self.assertFalse(self.window.calculate_button.isEnabled())
                    self.assertFalse(self.window.pin_button.isEnabled())
                    self.assertIsNone(self.window.current_curve)
                    self.assertIn("does not implement graph", self.window.error_label.text())
                    self.assertEqual(self.window.details.table.rowCount(), 0)
                else:
                    self.assertTrue(self.window.calculate_button.isEnabled())
                    self.assertIsNotNone(self.window.current_curve)
                    self.assertTrue(self.window.details.table.rowCount())
                    self.assertIn(f"from marksfuncs.functions import {spec.key}", self.window.details.code.toPlainText())

    def test_minimal_brand_and_blue_plot_replace_decorative_copy(self):
        self.assertEqual(self.window.windowTitle(), "marksfuncs-ui")
        brand = self.window.findChild(QLabel, "Brand")
        self.assertEqual(brand.text(), "marksfuncs-ui")
        self.assertEqual(brand.font().family(), "Space Grotesk")
        brand_color = brand.palette().color(QPalette.ColorRole.WindowText)
        self.assertTrue(200 <= brand_color.hsvHue() <= 260)
        self.assertGreater(brand_color.hsvSaturation(), 150)
        active_color = QColor(self.window.plot._curves[-1]["color"])
        self.assertTrue(200 <= active_color.hsvHue() <= 260)
        self.assertGreater(active_color.hsvSaturation(), 150)
        self.assertFalse(hasattr(self.window, "subtitle"))
        self.assertFalse(hasattr(self.window, "sample_info"))
        decorative_copy = re.compile(
            r"from an idea|a space for|explore.{0,20}understand|function laboratory|"
            r"laboratory of functions|assign values|watch.{0,15}change|"
            r"explore its behavior|your own values|marksfuncs data|/\s*studio",
            re.IGNORECASE,
        )
        label_text = "\n".join(widget.text() for widget in self.window.findChildren(QLabel))
        self.assertIsNone(decorative_copy.search(label_text))

    def test_expression_math_notation_is_evaluated_by_marksfuncs(self):
        self.window.select_function("ExpressionFunction")
        self.window.range_panel.set_values((0.1, 2), 101)
        for expression, expected in (("x^2", np.square), ("ln(x)", np.log)):
            with self.subTest(expression=expression):
                self.window.parameters.controls["expression"].setText(expression)
                self.window.calculate()
                self.assertIsNotNone(self.window.current_curve)
                self.assertFalse(self.window.error_label.isVisible())
                np.testing.assert_allclose(self.window.current_curve.y, expected(self.window.current_curve.x))
                self.assertEqual(self.window.project_state()["functions"]["ExpressionFunction"]["parameters"]["expression"], expression)
                code = self.window.details.code.toPlainText()
                self.assertIn("from marksfuncs.functions import ExpressionFunction", code)
                self.assertIn("f.graph()", code)

    def test_error_label_identifies_input_and_library_failures(self):
        self.window.select_function("ExpressionFunction")
        self.window.parameters.controls["expression"].setText("sin(")
        self.window.calculate()
        self.assertTrue(self.window.error_label.isVisible())
        self.assertTrue(self.window.error_label.text().startswith("Input:"))
        self.assertIsNone(self.window.current_curve)
        self.window.parameters.controls["expression"].setText("sin(x)")
        with patch("marksfuncs_ui.main_window.compute_curve", side_effect=CalculationError(
            "fixture library failure", source="marksfuncs"
        )):
            self.window.calculate()
        self.assertTrue(self.window.error_label.text().startswith("marksfuncs:"))
        self.assertIn("fixture library failure", self.window.error_label.text())
        self.assertIsNone(self.window.current_curve)

    def test_live_expression_syntax_error_clears_when_valid_input_is_plotted(self):
        self.window.select_function("ExpressionFunction")
        control = self.window.parameters.controls["expression"]
        self.assertTrue(self.window.live.isChecked())
        control.setText("sin(")
        self.assertIsNone(self.window.current_curve)
        self.assertEqual(self.window.details.table.rowCount(), 0)
        self.assertFalse(self.window.plot._curves)
        QTest.qWait(250)
        self.assertTrue(self.window.error_label.text().startswith("Input:"))
        self.assertIsNone(self.window.current_curve)
        control.setText("sin(x)")
        self.assertIsNone(self.window.current_curve)
        QTest.qWait(250)
        self.assertIsNotNone(self.window.current_curve)
        self.assertFalse(self.window.error_label.isVisible())
        self.assertTrue(self.window.details.table.rowCount())
        np.testing.assert_allclose(self.window.current_curve.y, np.sin(self.window.current_curve.x))

    def test_pinned_curve_survives_parameter_edits_and_function_switches(self):
        self.window.select_function("Linear")
        self.window.pin_curve()
        pinned = self.window.comparison_curves[0].y.copy()
        self.window.parameters.controls["m"].setValue(2.25)
        self.window.calculate()
        self.assertEqual(self.window.comparisons[0]["parameters"]["m"], 1)
        np.testing.assert_array_equal(self.window.comparison_curves[0].y, pinned)
        self.assertFalse(np.array_equal(self.window.current_curve.y, pinned))
        self.window.select_function("Quadratic")
        self.window.parameters.controls["c"].setValue(3.5)
        self.window.calculate()
        self.window.select_function("Linear")
        self.assertEqual(self.window.parameters.values()["m"], 2.25)
        self.assertEqual(len(self.window.comparisons), 1)
        self.assertEqual(len(self.window.plot._curves), 2)
        self.window.select_function("Quadratic")
        self.assertEqual(self.window.parameters.values()["c"], 3.5)

    def test_live_off_clears_stale_data_until_explicit_calculation(self):
        self.window.select_function("Linear")
        self.window.live.setChecked(False)
        old_y = self.window.current_curve.y.copy()
        self.window.parameters.controls["m"].setValue(3)
        self.assertIsNone(self.window.current_curve)
        self.assertFalse(self.window.plot._curves)
        self.assertEqual(self.window.details.table.rowCount(), 0)
        self.assertFalse(self.window.pin_button.isEnabled())
        self.assertFalse(self.window.debounce.isActive())
        self.assertIn("m = 3", self.window.details.code.toPlainText())
        self.window.calculate_button.click()
        self.assertIsNotNone(self.window.current_curve)
        self.assertTrue(self.window.pin_button.isEnabled())
        self.assertFalse(np.array_equal(old_y, self.window.current_curve.y))

    def test_pending_edit_ctrl_return_uses_exact_decimal_without_focus_loss(self):
        self.window.select_function("Linear")
        self.window.live.setChecked(False)
        control = self.window.parameters.controls["m"]
        control.setLocale(QLocale.c())
        control.setFocus()
        control.selectAll()
        QTest.keyClicks(control, "2.34567891")
        self.assertEqual(control.value(), 1)
        QTest.keyClick(control, Qt.Key.Key_Return, Qt.KeyboardModifier.ControlModifier)
        self.app.processEvents()
        self.assertAlmostEqual(self.window.parameters.values()["m"], 2.34567891, places=8)
        np.testing.assert_allclose(self.window.current_curve.y, 2.34567891 * self.window.current_curve.x)
        self.assertIn("m = 2.34567891", self.window.details.code.toPlainText())
        self.assertFalse(self.window.debounce.isActive())

    def test_pending_numeric_edits_prompt_before_discarding_saved_clean_session(self):
        for key, text, expected in (("m", "2.34567891", 2.34567891),
                                    ("x_min", "-4.12345678", -4.12345678),
                                    ("points", "517", 517)):
            with self.subTest(control=key):
                self.save_clean_linear()
                control = self.window.parameters.controls["m"] if key == "m" else getattr(self.window.range_panel, key)
                previous = control.value()
                self.type_pending_number(control, text)
                self.assertEqual(control.value(), previous)
                self.assertFalse(self.window.dirty)
                with patch("marksfuncs_ui.main_window.QMessageBox.question", return_value=QMessageBox.StandardButton.Cancel) as question:
                    self.assertFalse(self.window._confirm_discard())
                question.assert_called_once()
                self.assertAlmostEqual(control.value(), expected, places=8)
                self.assertTrue(self.window.dirty)

    def test_ctrl_open_and_close_cannot_lose_uncommitted_numeric_text(self):
        for action in ("open", "close"):
            with self.subTest(action=action):
                self.save_clean_linear()
                control = self.window.parameters.controls["m"]
                self.type_pending_number(control, "2.34567891")
                self.assertFalse(self.window.dirty)
                with patch("marksfuncs_ui.main_window.QMessageBox.question", return_value=QMessageBox.StandardButton.Cancel) as question, patch(
                    "marksfuncs_ui.main_window.QFileDialog.getOpenFileName"
                ) as file_dialog:
                    if action == "open":
                        QTest.keyClick(control, Qt.Key.Key_O, Qt.KeyboardModifier.ControlModifier)
                        self.app.processEvents()
                    else:
                        event = QCloseEvent()
                        self.window.closeEvent(event)
                        self.assertFalse(event.isAccepted())
                question.assert_called_once()
                file_dialog.assert_not_called()
                self.assertEqual(self.window.spec.key, "Linear")
                self.assertAlmostEqual(control.value(), 2.34567891, places=8)

    def test_pending_numeric_edit_is_calculated_before_pinning_snapshot(self):
        self.save_clean_linear()
        control = self.window.parameters.controls["m"]
        self.type_pending_number(control, "2.34567891")
        self.assertEqual(control.value(), 1)
        self.window.pin_curve()
        self.assertEqual(len(self.window.comparisons), 1)
        self.assertEqual(self.window.comparisons[0]["parameters"]["m"], 2.34567891)
        pinned = self.window.comparison_curves[0]
        np.testing.assert_allclose(pinned.y, 2.34567891 * pinned.x)
        self.assertEqual(self.window.project_state()["functions"]["Linear"]["parameters"]["m"], 2.34567891)

    def test_pending_numeric_export_syncs_code_and_csv_to_visual_assignments(self):
        for kind in ("py", "csv"):
            with self.subTest(kind=kind):
                self.save_clean_linear()
                control = self.window.parameters.controls["m"]
                self.type_pending_number(control, "2.34567891")
                self.assertEqual(control.value(), 1)
                path = self.export(kind, f"pending.{kind}")
                if kind == "py":
                    self.assertIn("m = 2.34567891", path.read_text(encoding="utf-8"))
                else:
                    with path.open(encoding="utf-8", newline="") as stream:
                        rows = list(csv.reader(stream))
                    samples = np.asarray(rows[1:], dtype=float)
                    np.testing.assert_allclose(samples[:, 1], 2.34567891 * samples[:, 0])
                self.assertTrue(self.window.dirty)

    def test_save_open_roundtrip_restores_parameters_ranges_and_pinned_curves(self):
        self.window.select_function("Linear")
        self.window.parameters.controls["m"].setValue(1.23456789)
        self.window.range_panel.set_values((-2.25, 7.75), 777)
        self.window.calculate()
        self.window.pin_curve()
        self.window.select_function("ExpressionFunction")
        self.window.parameters.controls["expression"].setText("cos(x) + 0.5*x")
        self.window.calculate()
        expected = copy.deepcopy(self.window.project_state())
        path = self.path("workspace.mfuncs")
        with patch("marksfuncs_ui.main_window.QFileDialog.getSaveFileName", return_value=(str(path), "")):
            self.assertTrue(self.window.save_project())
        self.assertFalse(self.window.dirty)
        self.window.clear_comparisons()
        self.window.select_function("Quadratic")
        with patch("marksfuncs_ui.main_window.QMessageBox.question", return_value=QMessageBox.StandardButton.Discard), patch(
            "marksfuncs_ui.main_window.QFileDialog.getOpenFileName", return_value=(str(path), "")
        ):
            self.window.open_project()
        self.assertEqual(self.window.project_state(), expected)
        self.assertEqual(self.window.spec.key, "ExpressionFunction")
        self.assertEqual(len(self.window.comparison_curves), 1)
        self.assertEqual(self.window.session_path, str(path))
        self.assertFalse(self.window.dirty)

    def test_invalid_session_does_not_replace_current_workspace(self):
        self.window.select_function("Linear")
        self.window.parameters.controls["m"].setValue(2)
        self.window.calculate()
        self.window.pin_curve()
        expected = copy.deepcopy(self.window.project_state())
        expected_y = self.window.current_curve.y.copy()
        path = self.path("broken.mfuncs")
        path.write_text(json.dumps({"version": 99}), encoding="utf-8")
        with patch("marksfuncs_ui.main_window.QMessageBox.question", return_value=QMessageBox.StandardButton.Discard), patch(
            "marksfuncs_ui.main_window.QFileDialog.getOpenFileName", return_value=(str(path), "")
        ), patch("marksfuncs_ui.main_window.QMessageBox.warning") as warning:
            self.window.open_project()
        warning.assert_called_once()
        self.assertEqual(self.window.project_state(), expected)
        np.testing.assert_array_equal(self.window.current_curve.y, expected_y)
        self.assertIsNone(self.window.session_path)

    def test_failed_upstream_clears_active_curve_and_table_but_keeps_comparisons(self):
        self.window.pin_curve()
        pinned = self.window.comparison_curves[0]
        with patch("marksfuncs_ui.main_window.compute_curve", side_effect=RuntimeError("upstream unavailable")):
            self.window.calculate()
        self.assertIsNone(self.window.current_curve)
        self.assertEqual(self.window.details.table.rowCount(), 0)
        self.assertEqual(len(self.window.plot._curves), len(pinned.series))
        self.assertFalse(self.window.pin_button.isEnabled())
        self.assertIn("upstream unavailable", self.window.error_label.text())

    def test_png_csv_and_python_exports_contain_actual_current_data(self):
        self.window.select_function("ComplexExponential")
        image_path = self.export("png", "curves.png")
        image = QImage(str(image_path))
        self.assertFalse(image.isNull())
        self.assertEqual(image.size(), self.window.plot.size())
        csv_path = self.export("csv", "curves.csv")
        with csv_path.open(encoding="utf-8", newline="") as stream:
            rows = list(csv.reader(stream))
        self.assertEqual(len(rows), len(self.window.current_curve.x) + 1)
        self.assertEqual(len(rows[0]), 3)
        np.testing.assert_allclose(np.asarray(rows[1:], dtype=float)[:, 1], self.window.current_curve.series[0].y)
        np.testing.assert_allclose(np.asarray(rows[1:], dtype=float)[:, 2], self.window.current_curve.series[1].y)
        source_path = self.export("py", "curves.py")
        source = source_path.read_text(encoding="utf-8")
        self.assertEqual(source, self.window.details.code.toPlainText())
        compile(source, str(source_path), "exec")

    def test_ackermann_csv_and_table_include_matrix_values_and_axis_names(self):
        self.window.select_function("Ackermann")
        self.assertEqual(self.window.details.table.columnCount(), 3)
        self.assertEqual([self.window.details.table.horizontalHeaderItem(i).text() for i in range(3)],
                         ["m", "n", "A(m, n)"])
        path = self.export("csv", "ackermann.csv")
        with path.open(encoding="utf-8", newline="") as stream:
            rows = list(csv.reader(stream))
        self.assertEqual(rows[0], ["m", "n", "A(m, n)"])
        np.testing.assert_array_equal(np.asarray(rows[1:], dtype=float)[:, 2],
                                      self.window.current_curve.series[0].colors)

    def test_compact_inspector_keeps_controls_inside_scrollable_column(self):
        self.window.resize(1080, 720)
        self.window.select_function("GeneralizedLogistics")
        self.app.processEvents()
        scroll = next(area for area in self.window.findChildren(QScrollArea)
                      if area.widget().isAncestorOf(self.window.parameters))
        content = scroll.widget()
        self.assertLessEqual(content.width(), scroll.viewport().width())
        controls = [*self.window.parameters.controls.values(), self.window.range_panel.x_min,
                    self.window.range_panel.x_max, self.window.range_panel.points,
                    self.window.live, self.window.animations]
        for control in controls:
            with self.subTest(control=control.accessibleName() or control.text()):
                scroll.ensureWidgetVisible(control)
                self.app.processEvents()
                origin = control.mapTo(content, QPoint())
                self.assertGreaterEqual(origin.x(), 0)
                self.assertLessEqual(origin.x() + control.width(), content.width())
                self.assertGreater(control.width(), 40)
                self.assertTrue(scroll.viewport().rect().contains(control.mapTo(scroll.viewport(), control.rect().center())))


if __name__ == "__main__":
    unittest.main()
