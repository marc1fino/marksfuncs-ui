"""Interaction and discontinuity checks for the real plotting widget."""

import math
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
from PyQt6.QtCore import QPoint, QPointF, Qt
from PyQt6.QtGui import QWheelEvent
from PyQt6.QtWidgets import QApplication

from marksfuncs_ui.plot_widget import PlotWidget, _number


class PlotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.widget = PlotWidget()
        self.widget.resize(700, 450)
        self.widget.set_animations_enabled(False)

    def tearDown(self):
        self.widget.close()
        self.widget.deleteLater()
        self.app.processEvents()

    def test_nonfinite_samples_and_poles_break_curve(self):
        curve = {"x": np.array([-2., -1., 0., 1., 2.]), "y": np.array([1., 2., math.nan, 3., 4.])}
        path = self.widget._curve_path(curve)
        self.assertTrue(path.elementAt(2).isMoveTo())
        pole = {"x": np.array([-0.1, -0.01, 0.01, 0.1]), "y": np.array([-10., -100., 100., 10.])}
        path = self.widget._curve_path(pole)
        self.assertTrue(path.elementAt(2).isMoveTo())

    def test_zoom_keeps_cursor_data_anchor_and_reset_restores_bounds(self):
        point = QPointF(250, 180)
        before = self.widget._to_data(point)
        event = QWheelEvent(point, point, QPoint(), QPoint(0, 120), Qt.MouseButton.NoButton,
                            Qt.KeyboardModifier.NoModifier, Qt.ScrollPhase.NoScrollPhase, False)
        self.widget.wheelEvent(event)
        after = self.widget._to_data(point)
        self.assertAlmostEqual(before[0], after[0])
        self.assertAlmostEqual(before[1], after[1])
        self.assertLess(self.widget.view[1] - self.widget.view[0], 12)
        self.widget.reset_view()
        self.assertEqual(self.widget.view, (-6., 6., -4., 4.))

    def test_curve_updates_preserve_camera_and_validate_lengths(self):
        self.widget.set_view(-3, 7, -8, 9)
        self.widget.set_curves([{"x": [0, 1], "y": [2, 3], "label": "Linear"}])
        self.assertEqual(self.widget.view, (-3., 7., -8., 9.))
        self.assertEqual(self.widget.reveal, 1.0)
        with self.assertRaises(ValueError):
            self.widget.set_curves([{"x": [0, 1], "y": [2]}])

    def test_multi_curve_and_nonfinite_data_render_to_image(self):
        self.widget.set_curves([
            {"x": [-1, 0, 1], "y": [1, math.nan, 2], "label": "first"},
            {"x": [-1, 0, 1], "y": [2, 3, 2], "label": "second", "scatter": True},
        ])
        image = self.widget.grab().toImage()
        self.assertFalse(image.isNull())
        self.assertEqual(image.width(), self.widget.width())

    def test_fit_records_reset_view_and_keeps_small_signals_visible(self):
        self.widget.set_curves([{"x": [0, 1, 2], "y": [1e-20, 2e-20, 3e-20]}])
        self.widget.fit_curves()
        fitted = self.widget.view
        self.assertLess(fitted[2], 1e-20)
        self.assertGreater(fitted[3], 3e-20)
        self.assertLess(fitted[3] - fitted[2], 1e-19)
        self.widget._change_view((-3, 7, -8, 9))
        self.widget.reset_view()
        self.assertEqual(self.widget.view, fitted)

    def test_scientific_labels_and_zoom_retain_tiny_or_large_signals(self):
        self.assertEqual(_number(1e-20), "1e-20")
        self.assertEqual(_number(-1e-20), "-1e-20")
        self.assertEqual(_number(-0.0), "0")
        point = QPointF(250, 180)
        for magnitude in (1e-20, 1e30):
            with self.subTest(magnitude=magnitude):
                self.widget.set_view(-3, 3, -magnitude, magnitude)
                before = self.widget.view
                event = QWheelEvent(point, point, QPoint(), QPoint(0, 120), Qt.MouseButton.NoButton,
                                    Qt.KeyboardModifier.NoModifier, Qt.ScrollPhase.NoScrollPhase, False)
                self.widget.wheelEvent(event)
                self.assertLess(self.widget.view[3] - self.widget.view[2], before[3] - before[2])
                self.assertTrue(all(math.isfinite(value) for value in self.widget.view))
                self.assertFalse(self.widget.grab().isNull())

    def test_fit_constant_large_value_and_overflow_do_not_crash(self):
        self.widget.set_curves([{"x": [0, 1], "y": [1e30, 1e30]}])
        self.widget.fit_curves()
        self.assertLess(self.widget.view[2], 1e30)
        self.assertGreater(self.widget.view[3], 1e30)
        self.widget.set_curves([{"x": [0, 1], "y": [-1e308, 1e308]}])
        self.widget.fit_curves()
        self.assertTrue(all(math.isfinite(value) for value in self.widget.view))

    def test_scalar_scatter_preserves_values_and_renders_color_scale(self):
        self.widget.set_curves([{"x": [0, 1, 2], "y": [0, 1, 2],
                                "values": [1, 5, 9], "scatter": True, "label": "Ackermann"}])
        self.widget.set_axis_labels("m", "n")
        self.assertEqual(self.widget._value_bounds, (1, 9))
        self.assertNotEqual(self.widget._value_color(1), self.widget._value_color(9))
        np.testing.assert_equal(self.widget._curves[0]["values"], [1, 5, 9])
        self.assertFalse(self.widget.grab().isNull())
        with self.assertRaises(ValueError):
            self.widget.set_curves([{"x": [0, 1], "y": [0, 1], "values": [2]}])


if __name__ == "__main__":
    unittest.main()
