"""Non-modal in-app notification overlay."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)


class NotificationOverlay(QFrame):
    WIDTH = 390

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("notificationOverlay")
        self.setProperty("level", "success")
        self.setFixedWidth(self.WIDTH)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._view_action: Callable[[], None] | None = None

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 75))
        self.setGraphicsEffect(shadow)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 16, 14, 14)
        layout.setSpacing(14)
        self.icon = QLabel("✓")
        self.icon.setObjectName("notificationIcon")
        self.icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon.setFixedSize(34, 34)
        layout.addWidget(self.icon, alignment=Qt.AlignmentFlag.AlignTop)

        content = QVBoxLayout()
        content.setSpacing(4)
        self.title = QLabel()
        self.title.setObjectName("notificationTitle")
        self.message = QLabel()
        self.message.setObjectName("notificationMessage")
        self.message.setWordWrap(True)
        buttons = QHBoxLayout()
        buttons.setContentsMargins(0, 5, 0, 0)
        self.view_button = QPushButton("View forest")
        self.view_button.setObjectName("notificationAction")
        self.dismiss_button = QPushButton("Dismiss")
        self.dismiss_button.setObjectName("notificationDismiss")
        buttons.addWidget(self.view_button)
        buttons.addStretch()
        buttons.addWidget(self.dismiss_button)
        content.addWidget(self.title)
        content.addWidget(self.message)
        content.addLayout(buttons)
        layout.addLayout(content, 1)

        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.hide)
        self.dismiss_button.clicked.connect(self.hide)
        self.view_button.clicked.connect(self._view_forest)
        self.hide()

    def show_notification(
        self,
        title: str,
        message: str,
        *,
        level: str = "success",
        view_action: Callable[[], None] | None = None,
        timeout_ms: int = 9000,
    ) -> None:
        self.setProperty("level", level)
        self.style().unpolish(self)
        self.style().polish(self)
        self.icon.setText("✓" if level == "success" else "!" if level == "warning" else "i")
        self.title.setText(title)
        self.message.setText(message)
        self._view_action = view_action
        self.view_button.setVisible(view_action is not None)
        self.adjustSize()
        self.setFixedWidth(self.WIDTH)
        self.reposition()
        self.show()
        self.raise_()
        self.timer.start(timeout_ms)

    def reposition(self) -> None:
        parent = self.parentWidget()
        if parent is None:
            return
        margin = 22
        self.move(max(margin, parent.width() - self.width() - margin), margin)

    def _view_forest(self) -> None:
        action = self._view_action
        self.hide()
        if action is not None:
            action()
