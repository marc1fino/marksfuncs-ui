"""Visual assignments retain constructor values and emit deliberate edits."""

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QLocale, Qt
from PyQt6.QtTest import QSignalSpy, QTest
from PyQt6.QtWidgets import QApplication, QDoubleSpinBox, QLineEdit, QSpinBox

from marksfuncs_ui.catalog import BY_KEY, CATALOG
from marksfuncs_ui.controls import ParameterPanel, RangePanel


class ControlsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.panel = ParameterPanel()
        self.range_panel = RangePanel()

    def tearDown(self):
        for widget in (self.panel, self.range_panel):
            widget.close()
            widget.deleteLater()
        self.app.processEvents()

    def test_manual_decimal_is_not_rounded_back_to_slider_step(self):
        self.panel.set_spec(BY_KEY["Linear"])
        control = self.panel.controls["m"]
        self.assertIsInstance(control, QDoubleSpinBox)
        signals = QSignalSpy(self.panel.valueChanged)
        control.setValue(1.23456789)
        self.assertEqual(self.panel.values()["m"], 1.23456789)
        self.assertEqual(len(signals), 1)
        # Both ways of assigning m stay linked, and do not recurse through signals.
        slider = self.panel.sliders["m"]
        slider.setValue(slider.maximum())
        self.assertEqual(self.panel.values()["m"], 10)
        self.assertEqual(len(signals), 2)

    def test_integer_assignment_stays_integer_and_has_accessible_names(self):
        self.panel.set_spec(BY_KEY["Legendre"])
        control = self.panel.controls["grade"]
        self.assertIsInstance(control, QSpinBox)
        self.panel.sliders["grade"].setValue(8)
        self.assertEqual(self.panel.values(), {"grade": 8})
        self.assertIsInstance(self.panel.values()["grade"], int)
        self.assertTrue(control.accessibleName())
        self.assertTrue(self.panel.sliders["grade"].accessibleName())

    def test_expression_edit_preserves_text_and_emits_change(self):
        self.panel.set_spec(BY_KEY["ExpressionFunction"])
        control = self.panel.controls["expression"]
        self.assertIsInstance(control, QLineEdit)
        signals = QSignalSpy(self.panel.valueChanged)
        expression = "cos(x) + 0.125*x**2"
        control.setText(expression)
        self.assertEqual(self.panel.values(), {"expression": expression})
        self.assertEqual(len(signals), 1)
        control.clear()
        self.assertEqual(self.panel.values()["expression"], "")
        self.assertEqual(len(signals), 2)

    def test_restore_switch_and_reset_emit_only_requested_change(self):
        signals = QSignalSpy(self.panel.valueChanged)
        spec = BY_KEY["Linear"]
        self.panel.set_spec(spec, {"m": -0.12345678, "b": 2.5})
        self.assertEqual(self.panel.values(), {"m": -0.12345678, "b": 2.5})
        self.assertEqual(len(signals), 0)
        self.panel.reset_defaults()
        self.assertEqual(self.panel.values(), spec.defaults())
        self.assertEqual(len(signals), 1)
        self.panel.set_spec(BY_KEY["BesselOrder0"])
        self.assertEqual(self.panel.values(), {})
        self.assertFalse(self.panel.sliders)
        self.assertEqual(len(signals), 1)
        self.panel.set_spec(BY_KEY["PolynomialCoefficients"])
        self.assertEqual(self.panel.values(), BY_KEY["PolynomialCoefficients"].defaults())

    def test_range_restore_preserves_decimals_and_does_not_queue_work(self):
        signals = QSignalSpy(self.range_panel.changed)
        self.range_panel.set_values((-0.12345678, 8.7654321), 777)
        self.assertEqual(self.range_panel.values(), ((-0.12345678, 8.7654321), 777))
        self.assertEqual(len(signals), 0)
        self.range_panel.x_min.setValue(-2.25)
        self.assertEqual(len(signals), 1)
        self.range_panel.points.setValue(1000)
        self.assertEqual(len(signals), 2)
        self.assertEqual(self.range_panel.values(), ((-2.25, 8.7654321), 1000))

    def test_numeric_keyboard_edit_commits_without_slider_quantization(self):
        for locale in (QLocale("es_ES"), QLocale.c()):
            with self.subTest(locale=locale.name()):
                self.panel.set_spec(BY_KEY["Linear"])
                control = self.panel.controls["m"]
                control.setLocale(locale)
                self.panel.show()
                control.setFocus()
                control.selectAll()
                QTest.keyClicks(control, "2" + locale.decimalPoint() + "345678")
                QTest.keyClick(control, Qt.Key.Key_Return)
                self.assertAlmostEqual(self.panel.values()["m"], 2.345678, places=8)

    def test_snapshot_commits_pending_decimal_without_emitting_or_quantizing(self):
        for locale in (QLocale("es_ES"), QLocale.c()):
            with self.subTest(locale=locale.name()):
                self.panel.set_spec(BY_KEY["Linear"])
                control = self.panel.controls["m"]
                control.setLocale(locale)
                self.panel.show()
                control.setFocus()
                control.selectAll()
                QTest.keyClicks(control, "2" + locale.decimalPoint() + "345678")
                self.assertEqual(control.value(), 1)
                signals = QSignalSpy(self.panel.valueChanged)
                self.assertEqual(self.panel.values()["m"], 2.345678)
                self.assertEqual(len(signals), 0)
                slider = self.panel.sliders["m"]
                self.assertEqual(slider.value(), round((2.345678 + 10) / 20 * slider.maximum()))

    def test_snapshot_commits_pending_integer_without_emitting(self):
        self.panel.set_spec(BY_KEY["Legendre"])
        control = self.panel.controls["grade"]
        self.panel.show()
        control.setFocus()
        control.selectAll()
        QTest.keyClicks(control, "4")
        signals = QSignalSpy(self.panel.valueChanged)
        self.assertEqual(self.panel.values(), {"grade": 4})
        self.assertEqual(len(signals), 0)
        self.assertEqual(self.panel.sliders["grade"].value(), 4)

    def test_sampling_snapshot_commits_pending_editor_without_emitting(self):
        self.range_panel.show()
        for control, text, expected in (
            (self.range_panel.x_min, "-2.345678", ((-2.345678, 10), 401)),
            (self.range_panel.x_max, "8.765432", ((-2.345678, 8.765432), 401)),
            (self.range_panel.points, "155", ((-2.345678, 8.765432), 155)),
        ):
            with self.subTest(text=text):
                control.setLocale(QLocale.c())
                control.setFocus()
                control.selectAll()
                QTest.keyClicks(control, text)
                signals = QSignalSpy(self.range_panel.changed)
                self.assertEqual(self.range_panel.values(), expected)
                self.assertEqual(len(signals), 0)

    def test_all_controls_fit_a_narrow_inspector_with_application_style(self):
        from marksfuncs_ui.theme import STYLE, load_fonts
        load_fonts()
        previous_style = self.app.styleSheet()
        self.app.setStyleSheet(STYLE)
        try:
            self.range_panel.resize(230, 200)
            self.range_panel.show()
            self.app.processEvents()
            self.assertLessEqual(self.range_panel.minimumSizeHint().width(), 230)
            self.assertEqual(self.range_panel.width(), 230)
            for control in (self.range_panel.x_min, self.range_panel.x_max, self.range_panel.points):
                point = control.mapTo(self.range_panel, control.rect().topRight())
                self.assertLess(point.x(), self.range_panel.width())
                self.assertGreater(control.lineEdit().width(), 50)
            for spec in CATALOG:
                with self.subTest(function=spec.key):
                    self.panel.set_spec(spec)
                    self.panel.resize(230, 500)
                    self.panel.show()
                    self.app.processEvents()
                    self.assertLessEqual(self.panel.minimumSizeHint().width(), 230)
                    self.assertEqual(self.panel.width(), 230)
                    for control in self.panel.controls.values():
                        point = control.mapTo(self.panel, control.rect().topRight())
                        self.assertLess(point.x(), self.panel.width())
                        self.assertGreater(control.width(), 0)
                        if isinstance(control, (QSpinBox, QDoubleSpinBox)):
                            self.assertGreater(control.lineEdit().width(), 50)
        finally:
            self.app.setStyleSheet(previous_style)


if __name__ == "__main__":
    unittest.main()
