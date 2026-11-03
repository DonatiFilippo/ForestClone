"""Forest page and procedural terrain rendering."""

from __future__ import annotations

from datetime import datetime
import math

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPalette, QPen
from PySide6.QtWidgets import (
    QComboBox, QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QToolTip,
    QVBoxLayout, QWidget,
)

from ..forest import TreeModel, trees_for_session
from .tree_painter import draw_tree
from .widgets import page_header


class ForestCanvas(QWidget):
    """Scrollable procedural terrain populated by persisted sessions."""

    TREES_PER_CLEARING = 18
    CLEARING_HEIGHT = 390

    def __init__(self) -> None:
        super().__init__()
        self.sessions: list[object] = []
        self.trees: list[TreeModel] = []
        self._tree_hits: list[tuple[QRectF, TreeModel]] = []
        self._hovered: tuple[int, int] | None = None
        self.setMouseTracking(True)
        self.setMinimumHeight(self.CLEARING_HEIGHT)

    def set_sessions(self, sessions: list[object]) -> None:
        self.sessions = sessions
        self.trees = [
            tree for session in sessions for tree in trees_for_session(session)  # type: ignore[arg-type]
        ]
        clearings = max(1, math.ceil(len(self.trees) / self.TREES_PER_CLEARING))
        self.setMinimumHeight(clearings * self.CLEARING_HEIGHT)
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        dark = self.palette().color(QPalette.ColorRole.Window).lightness() < 128
        self._tree_hits.clear()
        clearings = max(1, math.ceil(len(self.trees) / self.TREES_PER_CLEARING))
        for clearing in range(clearings):
            top = clearing * self.CLEARING_HEIGHT
            start = clearing * self.TREES_PER_CLEARING
            end = min(start + self.TREES_PER_CLEARING, len(self.trees))
            self._draw_terrain(painter, top, clearing, dark)
            self._draw_trees(painter, top, start, end)
        if not self.trees:
            painter.setPen(QColor("#b7cabd") if dark else QColor("#536d5b"))
            painter.drawText(
                QRectF(30, 145, self.width() - 60, 100),
                Qt.AlignmentFlag.AlignCenter,
                "This clearing is ready for new growth.\nComplete a focus session to plant a tree here.",
            )

    def _draw_terrain(self, painter: QPainter, top: float, seed: int, dark: bool) -> None:
        width = self.width()
        rect = QRectF(8, top + 8, width - 16, self.CLEARING_HEIGHT - 16)
        painter.save()
        painter.setClipRect(rect)
        painter.setPen(Qt.PenStyle.NoPen)
        sky = QLinearGradient(0, top, 0, top + self.CLEARING_HEIGHT)
        sky.setColorAt(0, QColor("#1d342c") if dark else QColor("#dcefe5"))
        sky.setColorAt(1, QColor("#2e4c3d") if dark else QColor("#f3f8e9"))
        painter.setBrush(sky)
        painter.drawRoundedRect(rect, 16, 16)
        painter.setBrush(QColor(245, 194, 91, 105 if dark else 180))
        painter.drawEllipse(QRectF(width - 112, top + 40, 36, 36))

        far_hill = QPainterPath()
        far_hill.moveTo(-20, top + 205)
        far_hill.cubicTo(width * 0.18, top + 82, width * 0.35, top + 205, width * 0.52, top + 130)
        far_hill.cubicTo(width * 0.7, top + 60, width * 0.84, top + 190, width + 20, top + 112)
        far_hill.lineTo(width + 20, top + 280)
        far_hill.lineTo(-20, top + 280)
        far_hill.closeSubpath()
        painter.setBrush(QColor("#315343") if dark else QColor("#a9cea9"))
        painter.drawPath(far_hill)

        meadow = QPainterPath()
        meadow.moveTo(-10, top + 210)
        meadow.cubicTo(width * 0.25, top + 165, width * 0.55, top + 230, width + 10, top + 174)
        meadow.lineTo(width + 10, top + self.CLEARING_HEIGHT + 10)
        meadow.lineTo(-10, top + self.CLEARING_HEIGHT + 10)
        meadow.closeSubpath()
        meadow_gradient = QLinearGradient(0, top + 180, 0, top + self.CLEARING_HEIGHT)
        meadow_gradient.setColorAt(0, QColor("#426b4f") if dark else QColor("#8fc28a"))
        meadow_gradient.setColorAt(1, QColor("#263f34") if dark else QColor("#65a36f"))
        painter.setBrush(meadow_gradient)
        painter.drawPath(meadow)

        stream = QPainterPath()
        stream.moveTo(width * 0.66, top + 175)
        stream.cubicTo(width * 0.72, top + 235, width * 0.49, top + 260, width * 0.57, top + 405)
        painter.setPen(QPen(QColor("#477b83") if dark else QColor("#72b8c1"), 36, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawPath(stream)
        painter.setPen(QPen(QColor(205, 242, 238, 75), 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawPath(stream)

        footpath = QPainterPath()
        footpath.moveTo(width * 0.15, top + 390)
        footpath.cubicTo(width * 0.22, top + 315, width * 0.34, top + 295, width * 0.30, top + 205)
        painter.setPen(QPen(QColor("#786b55") if dark else QColor("#d1bd8c"), 22, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawPath(footpath)

        painter.setPen(Qt.PenStyle.NoPen)
        for index in range(9):
            x = 30 + ((index * 97 + seed * 43) % max(80, width - 60))
            y = top + 245 + ((index * 37 + seed * 29) % 125)
            if index % 3 == 0:
                painter.setBrush(QColor("#77887b") if dark else QColor("#879b87"))
                painter.drawEllipse(QRectF(x, y, 10 + index % 4, 6 + index % 3))
            else:
                painter.setBrush(QColor("#e8c96d") if index % 2 else QColor("#e4eee4"))
                painter.drawEllipse(QRectF(x, y, 4, 4))
        painter.restore()

    def _draw_trees(self, painter: QPainter, top: float, start: int, end: int) -> None:
        width = self.width()
        placements: list[tuple[float, float, float, TreeModel]] = []
        column_order = (1, 4, 2, 5, 0, 3)
        for local, tree_index in enumerate(range(start, end)):
            row, slot = divmod(local, 6)
            column = column_order[slot]
            x = (column + 0.48) * width / 6 + ((tree_index * 37) % 25) - 12
            ground = top + 224 + row * 66 + ((tree_index * 23) % 19) - 9
            river_x = width * (0.66 - 0.09 * ((ground - top - 175) / 215))
            if abs(x - river_x) < 45:
                x += -58 if column < 3 else 58
            model = self.trees[tree_index]
            size = (58 + row * 7 + (tree_index * 7) % 8) * model.scale
            placements.append((ground, x, size, model))
        for ground, x, size, model in sorted(placements, key=lambda item: item[0]):
            draw_tree(
                painter, x, ground, size, model.species, dead=model.dead, sapling=model.sapling
            )
            hit_width = max(24.0, size * (0.55 if model.dead else 1.05))
            hit_height = max(38.0, size * (1.05 if model.dead else 1.45))
            self._tree_hits.append(
                (QRectF(x - hit_width / 2, ground - hit_height, hit_width, hit_height), model)
            )

    def mouseMoveEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        point = event.position()
        hit = next(
            ((bounds, model) for bounds, model in reversed(self._tree_hits) if bounds.contains(point)),
            None,
        )
        if hit is None:
            self._clear_hover()
            super().mouseMoveEvent(event)
            return
        _, model = hit
        key = (model.session_id, model.ordinal)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        if key != self._hovered:
            self._hovered = key
            QToolTip.showText(event.globalPosition().toPoint(), self._tooltip(model), self)
        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        self._clear_hover()
        super().leaveEvent(event)

    def _clear_hover(self) -> None:
        if self._hovered is not None:
            QToolTip.hideText()
            self._hovered = None
        self.unsetCursor()

    @staticmethod
    def _tooltip(model: TreeModel) -> str:
        species = "Peach" if model.species == "peach" else "Pine"
        title = f"Withered {species.lower()}" if model.dead else f"{species} {'sapling' if model.sapling else 'tree'}"
        started = datetime.fromtimestamp(model.started_at)
        planned = _format_tooltip_duration(model.duration_seconds)
        lines = [f"<b>{title}</b>", started.strftime("%A, %B %d, %Y at %H:%M"), f"Planned session: {planned}"]
        if model.dead:
            lines.append(f"Interrupted after {_format_tooltip_duration(model.elapsed_seconds)}")
        else:
            result = "Sapling from partial hour" if model.sapling and model.duration_seconds >= 3600 else "Session completed"
            lines.append(result)
            if model.total > 1:
                lines.append(f"Tree {model.ordinal} of {model.total} from this session")
        return "<br>".join(lines)


def _format_tooltip_duration(seconds: float) -> str:
    total_minutes = max(0, round(seconds / 60))
    hours, minutes = divmod(total_minutes, 60)
    if hours and minutes:
        return f"{hours}h {minutes}m"
    if hours:
        return f"{hours}h"
    return f"{minutes}m"


class ForestView(QWidget):
    period_moved = Signal(int)
    scope_changed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("page")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(34, 28, 34, 26)
        layout.setSpacing(8)
        title, caption = page_header("Your forest", "Explore completed sessions across a living landscape.")
        self.summary = QLabel("0 TREES PLANTED")
        self.summary.setObjectName("eyebrow")

        period_bar = QFrame()
        period_bar.setObjectName("periodBar")
        period_layout = QHBoxLayout(period_bar)
        period_layout.setContentsMargins(12, 8, 12, 8)
        period_layout.setSpacing(8)
        self.previous = QPushButton("‹")
        self.previous.setObjectName("periodButton")
        self.previous.setToolTip("Previous period")
        self.previous.clicked.connect(lambda: self.period_moved.emit(-1))
        self.period_label = QLabel()
        self.period_label.setObjectName("periodLabel")
        self.period_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.next = QPushButton("›")
        self.next.setObjectName("periodButton")
        self.next.setToolTip("Next period")
        self.next.clicked.connect(lambda: self.period_moved.emit(1))
        self.scope = QComboBox()
        self.scope.addItems(["Day", "Week", "Month", "All"])
        self.scope.setCurrentText("Week")
        self.scope.currentTextChanged.connect(self.scope_changed)
        period_layout.addWidget(self.previous)
        period_layout.addWidget(self.period_label, 1)
        period_layout.addWidget(self.next)
        period_layout.addSpacing(8)
        period_layout.addWidget(self.scope)

        self.canvas = ForestCanvas()
        scroll = QScrollArea()
        scroll.setObjectName("forestScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(self.canvas)
        layout.addWidget(title)
        layout.addWidget(caption)
        layout.addWidget(self.summary)
        layout.addSpacing(8)
        layout.addWidget(period_bar)
        layout.addWidget(scroll, 1)

    def set_period(self, label: str, summary: str, sessions: list[object], can_go_next: bool) -> None:
        self.period_label.setText(label)
        self.summary.setText(summary)
        self.canvas.set_sessions(sessions)
        all_time = self.scope.currentText() == "All"
        self.previous.setEnabled(not all_time)
        self.next.setEnabled(not all_time and can_go_next)
