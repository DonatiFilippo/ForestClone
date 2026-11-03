"""Focus timer page widgets and presentation state."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox, QFrame, QHBoxLayout, QLabel, QProgressBar, QPushButton, QSpinBox,
    QVBoxLayout, QWidget,
)

from ..timer import TimerState
from .tree_painter import TreeWidget
from .widgets import page_header


class FocusView(QWidget):
    primary_requested = Signal()
    cancel_requested = Signal()
    selection_changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("page")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(34, 28, 34, 26)
        layout.setSpacing(18)
        heading, caption = page_header("Focus session", "One task. One tree. Give it your full attention.")
        layout.addWidget(heading)
        layout.addWidget(caption)

        card = QFrame()
        card.setObjectName("focusCard")
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(24, 16, 30, 22)
        card_layout.setSpacing(24)
        self.tree = TreeWidget()
        card_layout.addWidget(self.tree, 5)

        controls = QVBoxLayout()
        controls.setSpacing(12)
        controls.addStretch()
        self.status = QLabel("READY TO FOCUS")
        self.status.setObjectName("sessionStatus")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.timer = QLabel("25:00")
        self.timer.setObjectName("timerLabel")
        self.timer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress = QProgressBar()
        self.progress.setObjectName("sessionProgress")
        self.progress.setRange(0, 1000)
        self.progress.setTextVisible(False)
        controls.addWidget(self.status)
        controls.addWidget(self.timer)
        controls.addWidget(self.progress)

        duration_row = QHBoxLayout()
        duration_label = QLabel("Session length")
        duration_label.setObjectName("fieldLabel")
        self.duration = QComboBox()
        for minutes in (15, 25, 45, 60):
            self.duration.addItem(f"{minutes} min", minutes)
        self.duration.addItem("Custom", None)
        self.duration.setCurrentIndex(1)
        self.custom_duration = QSpinBox()
        self.custom_duration.setRange(1, 480)
        self.custom_duration.setSuffix(" min")
        self.custom_duration.setValue(25)
        self.custom_duration.hide()
        duration_row.addWidget(duration_label)
        duration_row.addStretch()
        duration_row.addWidget(self.duration)
        duration_row.addWidget(self.custom_duration)
        controls.addLayout(duration_row)

        species_row = QHBoxLayout()
        species_label = QLabel("Tree to plant")
        species_label.setObjectName("fieldLabel")
        self.species = QComboBox()
        self.species.addItem("Peach tree", "peach")
        self.species.addItem("Pine tree", "pine")
        species_row.addWidget(species_label)
        species_row.addStretch()
        species_row.addWidget(self.species)
        controls.addLayout(species_row)

        buttons = QHBoxLayout()
        self.primary = QPushButton("Start focusing")
        self.primary.setObjectName("primaryButton")
        self.primary.setDefault(True)
        self.cancel = QPushButton("Cancel")
        self.cancel.setObjectName("secondaryButton")
        self.cancel.hide()
        buttons.addWidget(self.primary, 1)
        buttons.addWidget(self.cancel)
        controls.addLayout(buttons)
        controls.addStretch()
        card_layout.addLayout(controls, 4)
        layout.addWidget(card, 1)

        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)
        self.today = self._add_stat(stats_row, "FOCUS TODAY")
        self.trees = self._add_stat(stats_row, "TREES GROWN")
        self.streak = self._add_stat(stats_row, "DAY STREAK")
        self.total = self._add_stat(stats_row, "TOTAL FOCUS")
        layout.addLayout(stats_row)

        self.primary.clicked.connect(self.primary_requested)
        self.cancel.clicked.connect(self.cancel_requested)
        self.duration.currentIndexChanged.connect(self._duration_changed)
        self.custom_duration.valueChanged.connect(self.selection_changed)
        self.species.currentIndexChanged.connect(self.selection_changed)

    @staticmethod
    def _add_stat(row: QHBoxLayout, label: str) -> QLabel:
        card = QFrame()
        card.setObjectName("statCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 12)
        value = QLabel("—")
        value.setObjectName("statValue")
        caption = QLabel(label)
        caption.setObjectName("statLabel")
        layout.addWidget(value)
        layout.addWidget(caption)
        row.addWidget(card)
        return value

    def selected_minutes(self) -> int:
        value = self.duration.currentData()
        return self.custom_duration.value() if value is None else int(value)

    def selected_species(self) -> str:
        return str(self.species.currentData())

    def set_duration(self, minutes: int) -> None:
        index = self.duration.findData(minutes)
        if index >= 0:
            self.duration.setCurrentIndex(index)
        else:
            self.duration.setCurrentIndex(self.duration.count() - 1)
            self.custom_duration.setValue(minutes)

    def set_species(self, species: str) -> None:
        self.species.setCurrentIndex(max(0, self.species.findData(species)))

    def update_timer(self, state: TimerState, remaining: int, progress: float) -> None:
        if state == TimerState.IDLE:
            remaining = self.selected_minutes() * 60
        minutes, seconds = divmod(remaining, 60)
        self.timer.setText(f"{minutes:02d}:{seconds:02d}")
        self.progress.setValue(round(progress * 1000))
        active = state in (TimerState.RUNNING, TimerState.PAUSED)
        self.tree.set_progress(progress if active else 1.0)
        self.duration.setEnabled(not active)
        self.custom_duration.setEnabled(not active)
        self.species.setEnabled(not active)
        self.cancel.setVisible(active)
        self.status.setText({
            TimerState.IDLE: "READY TO FOCUS",
            TimerState.RUNNING: "FOCUSING — TREE GROWING",
            TimerState.PAUSED: "SESSION PAUSED",
            TimerState.COMPLETED: "SESSION COMPLETE",
        }[state])
        self.primary.setText(
            "Pause session" if state == TimerState.RUNNING
            else "Resume session" if state == TimerState.PAUSED
            else "Start focusing"
        )

    def update_stats(self, today: str, trees: int, streak: int, total: str) -> None:
        self.today.setText(today)
        self.trees.setText(str(trees))
        self.streak.setText(f"{streak} days")
        self.total.setText(total)

    def update_tree_preview(self) -> None:
        self.tree.set_tree(self.selected_species(), self.selected_minutes() * 60)

    def _duration_changed(self) -> None:
        self.custom_duration.setVisible(self.duration.currentData() is None)
        self.selection_changed.emit()
