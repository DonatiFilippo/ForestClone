"""Large animated session-completion celebration."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QEasingCurve, QTimer, Qt, QVariantAnimation
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from .tree_painter import TreeWidget


class CompletionOverlay(QFrame):
    """Attention-grabbing but non-modal completion layer."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("completionOverlay")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._view_action: Callable[[], None] | None = None
        self._plant_action: Callable[[], None] | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(30, 30, 30, 30)
        outer.addStretch()
        center = QHBoxLayout()
        center.addStretch()
        self.card = QFrame()
        self.card.setObjectName("celebrationCard")
        self.card.setMinimumSize(500, 520)
        self.card.setMaximumSize(680, 590)
        shadow = QGraphicsDropShadowEffect(self.card)
        shadow.setBlurRadius(42)
        shadow.setOffset(0, 12)
        shadow.setColor(QColor(0, 0, 0, 100))
        self.card.setGraphicsEffect(shadow)
        content = QVBoxLayout(self.card)
        content.setContentsMargins(42, 30, 42, 32)
        content.setSpacing(7)
        self.eyebrow = QLabel("FOCUS COMPLETE")
        self.eyebrow.setObjectName("celebrationEyebrow")
        self.eyebrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title = QLabel("Your forest grew!")
        self.title.setObjectName("celebrationTitle")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message = QLabel()
        self.message.setObjectName("celebrationMessage")
        self.message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message.setWordWrap(True)
        self.tree = TreeWidget()
        self.tree.setMinimumSize(300, 310)
        self.tree.setMaximumHeight(340)
        buttons = QHBoxLayout()
        self.continue_button = QPushButton("Continue")
        self.continue_button.setObjectName("secondaryButton")
        self.view_button = QPushButton("View forest")
        self.view_button.setObjectName("secondaryButton")
        self.plant_button = QPushButton("Plant another")
        self.plant_button.setObjectName("primaryButton")
        buttons.addWidget(self.continue_button)
        buttons.addWidget(self.view_button)
        buttons.addWidget(self.plant_button)
        content.addWidget(self.eyebrow)
        content.addWidget(self.title)
        content.addWidget(self.message)
        content.addWidget(self.tree, 1)
        content.addLayout(buttons)
        center.addWidget(self.card)
        center.addStretch()
        outer.addLayout(center)
        outer.addStretch()

        self.animation = QVariantAnimation(self)
        self.animation.setDuration(1400)
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.setEasingCurve(QEasingCurve.Type.OutBack)
        self.animation.valueChanged.connect(
            lambda value: self.tree.set_progress(float(value))
        )
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.hide)
        self.continue_button.clicked.connect(self.hide)
        self.view_button.clicked.connect(self._view_forest)
        self.plant_button.clicked.connect(self._plant_another)
        self.hide()

    def show_completion(
        self,
        message: str,
        species: str,
        duration_seconds: int,
        *,
        view_action: Callable[[], None] | None = None,
        plant_action: Callable[[], None] | None = None,
    ) -> None:
        self.message.setText(message)
        self._view_action = view_action
        self._plant_action = plant_action
        self.plant_button.setVisible(plant_action is not None)
        self.tree.set_tree(species, duration_seconds)
        self.tree.set_progress(0.0)
        self.resize_to_parent()
        self.show()
        self.raise_()
        self.animation.stop()
        self.animation.start()
        self.timer.start(20000)

    def resize_to_parent(self) -> None:
        parent = self.parentWidget()
        if parent is not None:
            self.setGeometry(parent.rect())
            self.card.setFixedSize(
                min(680, max(500, parent.width() - 50)),
                min(590, max(520, parent.height() - 50)),
            )

    def _view_forest(self) -> None:
        action = self._view_action
        self.hide()
        if action is not None:
            action()

    def _plant_another(self) -> None:
        action = self._plant_action
        self.hide()
        if action is not None:
            action()
