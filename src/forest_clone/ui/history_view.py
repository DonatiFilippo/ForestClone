"""Session history page."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QHeaderView, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from ..statistics import format_duration
from .widgets import page_header


class HistoryView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("page")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(34, 28, 34, 28)
        layout.setSpacing(8)
        title, caption = page_header("Session history", "A clear record of focused and interrupted sessions.")
        self.table = QTableWidget(0, 4)
        self.table.setObjectName("historyTable")
        self.table.setHorizontalHeaderLabels(["DATE", "START", "DURATION", "STATUS"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().hide()
        self.table.verticalHeader().setDefaultSectionSize(46)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setShowGrid(False)
        layout.addWidget(title)
        layout.addWidget(caption)
        layout.addSpacing(16)
        layout.addWidget(self.table, 1)

    def set_sessions(self, sessions: list[object]) -> None:
        labels = {
            "completed": "Completed", "interrupted": "Interrupted",
            "running": "In progress", "paused": "Paused",
        }
        colors = {
            "completed": QColor("#3f9158"), "interrupted": QColor("#b65d57"),
            "running": QColor("#3b7f98"), "paused": QColor("#b4863e"),
        }
        self.table.setRowCount(len(sessions))
        for row_index, row in enumerate(sessions):
            started = datetime.fromtimestamp(float(row["started_at"]))  # type: ignore[index]
            status = str(row["status"])  # type: ignore[index]
            values = (
                started.strftime("%b %d, %Y"), started.strftime("%H:%M"),
                format_duration(int(row["duration_seconds"])), labels[status],  # type: ignore[index]
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 3:
                    item.setForeground(colors[status])
                self.table.setItem(row_index, column, item)
