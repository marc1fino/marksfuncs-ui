"""Transition endpoints, interruption and unchanged library samples."""

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
from PyQt6.QtCore import QAbstractAnimation, QPoint, QPointF, Qt
from PyQt6.QtGui import QWheelEvent
from PyQt6.QtTest import QSignalSpy, QTest
from PyQt6.QtWidgets import QApplication, QWidget

from marksfuncs_ui.motion import FadeTransition
from marksfuncs_ui.plot_widget import PlotWidget


class MotionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.widget = QWidget()
        self.widget.resize(400, 240)
        self.fade = FadeTransition(self.widget)
        self.plot = PlotWidget()
        self.plot.resize(700, 450)

    def tearDown(self):
        for widget in (self.widget, self.plot):
            widget.close()
            widget.deleteLater()
        self.app.processEvents()

    def show_widget(self, widget):
        widget.show()
        self.app.processEvents()
        self.assertTrue(widget.isVisible())

    def test_fade_animates_visible_content_to_full_opacity(self):
        self.show_widget(self.widget)
        self.fade.start()
        self.assertEqual(self.fade.animation.state(), QAbstractAnimation.State.Running)
        self.assertLess(self.fade.effect.opacity(), 1)
        QTest.qWait(280)
        self.assertEqual(self.fade.animation.state(), QAbstractAnimation.State.Stopped)
        self.assertEqual(self.fade.effect.opacity(), 1)

    def test_fade_skips_hidden_content_and_respects_reduced_motion(self):
        self.fade.start()
        self.assertEqual(self.fade.animation.state(), QAbstractAnimation.State.Stopped)
        self.assertEqual(self.fade.effect.opacity(), 1)
        self.show_widget(self.widget)
        self.fade.set_enabled(False)
        self.fade.start()
        self.assertEqual(self.fade.animation.state(), QAbstractAnimation.State.Stopped)
        self.assertEqual(self.fade.effect.opacity(), 1)

    def test_disabling_motion_finishes_an_in_progress_fade(self):
        self.show_widget(self.widget)
        self.fade.start()
        self.fade.animation.setCurrentTime(80)
        self.assertLess(self.fade.effect.opacity(), 1)
        self.fade.set_enabled(False)
        self.assertEqual(self.fade.effect.opacity(), 1)
        QTest.qWait(280)
        self.assertEqual(self.fade.effect.opacity(), 1)
        self.assertEqual(self.fade.animation.state(), QAbstractAnimation.State.Stopped)

    def test_rapid_fade_restart_continues_from_current_opacity(self):
        self.show_widget(self.widget)
        self.fade.start()
        self.fade.animation.setCurrentTime(100)
        before = self.fade.effect.opacity()
        self.assertGreater(before, 0.45)
        self.fade.start()
        self.assertAlmostEqual(self.fade.effect.opacity(), before)
        QTest.qWait(280)
        self.assertEqual(self.fade.effect.opacity(), 1)

    def test_camera_transitions_reach_requested_bounds_without_changing_samples(self):
        self.show_widget(self.plot)
        x = np.array([-1.0, 0.0, 1.0])
        y = np.array([7.125, np.nan, -3.75])
        self.plot.set_curves([{"x": x, "y": y, "label": "library samples"}])
        transitions = QSignalSpy(self.plot.viewChanged)
        target = (-2.0, 4.0, -8.0, 10.0)
        initial = self.plot.view
        self.plot.set_view(*target)
        self.plot._camera_transition.setCurrentTime(100)
        intermediate = self.plot.view
        self.assertNotEqual(intermediate, initial)
        self.assertNotEqual(intermediate, target)
        QTest.qWait(320)
        np.testing.assert_allclose(self.plot.view, target)
        self.assertGreater(len(transitions), 2)
        np.testing.assert_array_equal(self.plot._curves[0]["x"], x)
        np.testing.assert_array_equal(self.plot._curves[0]["y"], y)

    def test_new_camera_target_cancels_the_previous_animation(self):
        self.show_widget(self.plot)
        self.plot.set_view(-20, 20, -10, 10)
        self.plot._camera_transition.setCurrentTime(100)
        interrupted = self.plot.view
        target = (0.0, 3.0, -1.0, 1.0)
        self.plot.set_view(*target)
        np.testing.assert_allclose(self.plot.view, interrupted)
        QTest.qWait(320)
        np.testing.assert_allclose(self.plot.view, target)
        self.assertEqual(self.plot._camera_transition.state(), QAbstractAnimation.State.Stopped)

    def test_reduced_motion_finishes_camera_and_curve_reveal(self):
        self.show_widget(self.plot)
        self.plot.set_curves([{"x": [0, 1], "y": [3, 7], "label": "library samples"}])
        target = (-3.0, 5.0, -4.0, 8.0)
        self.plot.set_view(*target)
        self.plot._animation.setCurrentTime(70)
        self.plot._camera_transition.setCurrentTime(70)
        self.assertLess(self.plot.reveal, 1)
        self.plot.set_animations_enabled(False)
        self.assertEqual(self.plot.reveal, 1)
        np.testing.assert_allclose(self.plot.view, target)
        QTest.qWait(320)
        np.testing.assert_allclose(self.plot.view, target)
        self.assertEqual(self.plot._animation.state(), QAbstractAnimation.State.Stopped)

    def test_snapshot_finishes_all_transitions_and_does_not_resume(self):
        self.show_widget(self.plot)
        self.plot.set_curves([{"x": [0, 1], "y": [3, 7], "label": "library samples"}])
        target = (-3.0, 5.0, -4.0, 8.0)
        self.plot.set_view(*target)
        self.plot._animation.setCurrentTime(60)
        self.plot._camera_transition.setCurrentTime(60)
        self.plot.finish_animation()
        self.assertEqual(self.plot.reveal, 1)
        np.testing.assert_allclose(self.plot.view, target)
        self.assertFalse(self.plot.grab().isNull())
        QTest.qWait(320)
        self.assertEqual(self.plot.reveal, 1)
        np.testing.assert_allclose(self.plot.view, target)

    def test_user_zoom_cancels_camera_motion_instead_of_being_undone(self):
        self.show_widget(self.plot)
        self.plot.set_view(-20, 20, -10, 10)
        self.plot._camera_transition.setCurrentTime(80)
        point = QPointF(250, 180)
        event = QWheelEvent(point, point, QPoint(), QPoint(0, 120), Qt.MouseButton.NoButton,
                            Qt.KeyboardModifier.NoModifier, Qt.ScrollPhase.NoScrollPhase, False)
        self.plot.wheelEvent(event)
        zoomed = self.plot.view
        self.assertEqual(self.plot._camera_transition.state(), QAbstractAnimation.State.Stopped)
        QTest.qWait(320)
        np.testing.assert_allclose(self.plot.view, zoomed)


if __name__ == "__main__":
    unittest.main()
