"""End-to-end native workspace behavior against the installed marksfuncs."""

import copy
import csv
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
from PyQt6.QtCore import QPoint, QLocale, Qt
from PyQt6.QtGui import QCloseEvent, QImage
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QMessageBox, QScrollArea

from marksfuncs_ui.catalog import CATALOG
from marksfuncs_ui.engine import unavailable_reason
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

    def test_all_functions_select_with_real_curve_or_explicit_upstream_limitation(self):
        for spec in CATALOG:
            with self.subTest(function=spec.key):
                self.window.select_function(spec.key)
                self.assertEqual(self.window.spec.key, spec.key)
                self.assertEqual(self.window.title.text(), spec.name)
                self.assertIn(spec.description, self.window.details.explanation.toPlainText())
                if unavailable_reason(spec):
                    self.assertFalse(self.window.calculate_button.isEnabled())
                    self.assertFalse(self.window.pin_button.isEnabled())
                    self.assertIsNone(self.window.current_curve)
                    self.assertIn("no implementa graph", self.window.error_label.text())
                    self.assertEqual(self.window.details.table.rowCount(), 0)
                else:
                    self.assertTrue(self.window.calculate_button.isEnabled())
                    self.assertIsNotNone(self.window.current_curve)
                    self.assertTrue(self.window.details.table.rowCount())
                    self.assertIn(f"from marksfuncs.functions import {spec.key}", self.window.details.code.toPlainText())

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
