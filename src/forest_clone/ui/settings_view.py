"""Application settings page."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFormLayout, QFrame, QPushButton, QSpinBox, QVBoxLayout, QWidget,
)

from .widgets import page_header


class SettingsView(QWidget):
    save_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("page")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(34, 28, 34, 28)
        layout.setSpacing(8)
        title, caption = page_header("Settings", "Shape Pocket Forest around your focus routine.")
        card = QFrame()
        card.setObjectName("settingsCard")
        form = QFormLayout(card)
        form.setContentsMargins(26, 24, 26, 24)
        form.setHorizontalSpacing(35)
        form.setVerticalSpacing(20)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        self.default_duration = QSpinBox()
        self.default_duration.setRange(1, 480)
        self.default_duration.setSuffix(" minutes")
        self.notifications = QCheckBox("Use desktop notification; otherwise show a dialog")
        self.theme = QComboBox()
        self.theme.addItems(["System", "Light", "Dark"])
        save = QPushButton("Save changes")
        save.setObjectName("primaryButton")
        save.clicked.connect(self.save_requested)
        form.addRow("Default session", self.default_duration)
        form.addRow("Completion alert", self.notifications)
        form.addRow("Appearance", self.theme)
        layout.addWidget(title)
        layout.addWidget(caption)
        layout.addSpacing(20)
        layout.addWidget(card)
        layout.addSpacing(10)
        layout.addWidget(save, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addStretch()
