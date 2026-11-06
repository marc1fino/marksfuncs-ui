"""Short opacity transitions that respect the application's motion preference."""

from PyQt6.QtCore import QEasingCurve, QObject, QPropertyAnimation
from PyQt6.QtWidgets import QGraphicsOpacityEffect


class FadeTransition(QObject):
    def __init__(self, widget):
        super().__init__(widget)
        self.widget = widget
        self.enabled = True
        self.effect = QGraphicsOpacityEffect(widget)
        self.effect.setOpacity(1.0)
        widget.setGraphicsEffect(self.effect)
        self.animation = QPropertyAnimation(self.effect, b"opacity", self)
        self.animation.setDuration(240)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def set_enabled(self, enabled):
        self.enabled = bool(enabled)
        if not self.enabled:
            self.animation.stop()
            self.effect.setOpacity(1.0)

    def start(self):
        running = self.animation.state() == QPropertyAnimation.State.Running
        opacity = self.effect.opacity()
        self.animation.stop()
        if not self.enabled or not self.widget.isVisible():
            self.effect.setOpacity(1.0)
            return
        self.animation.setStartValue(opacity if running else 0.45)
        self.animation.setEndValue(1.0)
        self.animation.start()
