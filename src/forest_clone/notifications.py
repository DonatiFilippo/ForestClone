"""Desktop and in-app notification coordination."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QMainWindow, QSystemTrayIcon

from .ui.completion_overlay import CompletionOverlay
from .ui.notification_overlay import NotificationOverlay


def create_app_icon() -> QIcon:
    """Create lightweight forest icon without runtime asset lookup."""
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#edf6ee"))
    painter.drawRoundedRect(1, 1, 62, 62, 14, 14)
    painter.setBrush(QColor("#795548"))
    painter.drawRoundedRect(28, 31, 8, 24, 3, 3)
    painter.setBrush(QColor("#4f9d5d"))
    painter.drawEllipse(12, 8, 40, 40)
    painter.setBrush(QColor("#70b277"))
    painter.drawEllipse(8, 23, 28, 25)
    painter.drawEllipse(29, 23, 27, 25)
    painter.end()
    return QIcon(pixmap)


class NotificationService:
    def __init__(
        self,
        window: QMainWindow,
        overlay: NotificationOverlay,
        completion_overlay: CompletionOverlay,
    ) -> None:
        self.window = window
        self.overlay = overlay
        self.completion_overlay = completion_overlay
        self.tray = QSystemTrayIcon(create_app_icon(), window)
        self.tray.setToolTip("Pocket Forest")
        self.tray.messageClicked.connect(self._restore_window)
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.show()

    def notify(
        self,
        title: str,
        message: str,
        *,
        level: str = "success",
        desktop_enabled: bool = True,
        view_action: Callable[[], None] | None = None,
    ) -> None:
        self.overlay.show_notification(
            title, message, level=level, view_action=view_action
        )
        active = self.window.isActiveWindow() and not self.window.isMinimized()
        if not active and desktop_enabled and self.tray.isVisible():
            icon = (
                QSystemTrayIcon.MessageIcon.Warning
                if level == "warning"
                else QSystemTrayIcon.MessageIcon.Information
            )
            self.tray.showMessage(title, message, icon, 7000)
        QApplication.alert(self.window, 5000)

    def notify_completion(
        self,
        message: str,
        species: str,
        duration_seconds: int,
        *,
        desktop_enabled: bool = True,
        view_action: Callable[[], None] | None = None,
        plant_action: Callable[[], None] | None = None,
    ) -> None:
        was_inactive = not self.window.isActiveWindow() or self.window.isMinimized()
        if was_inactive and desktop_enabled and self.tray.isVisible():
            self.tray.showMessage(
                "Focus complete",
                message,
                QSystemTrayIcon.MessageIcon.Information,
                10000,
            )
        if was_inactive:
            self._restore_window()
        self.completion_overlay.show_completion(
            message,
            species,
            duration_seconds,
            view_action=view_action,
            plant_action=plant_action,
        )
        QApplication.alert(self.window, 12000)
        QApplication.beep()
        QTimer.singleShot(450, QApplication.beep)

    def _restore_window(self) -> None:
        self.window.showNormal()
        self.window.raise_()
        self.window.activateWindow()
