"""Lightweight procedural tree rendering shared by focus and forest views."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPalette, QPen, QPolygonF
from PySide6.QtWidgets import QSizePolicy, QWidget

from ..forest import tree_scale


def draw_tree(
    painter: QPainter,
    x: float,
    ground: float,
    size: float,
    species: str = "peach",
    progress: float = 1.0,
    *,
    dead: bool = False,
    sapling: bool = False,
) -> None:
    """Draw peach, pine, sapling, or interrupted-session tree."""
    painter.save()
    painter.translate(x, ground)
    growth = 0.38 + 0.62 * max(0.0, min(1.0, progress))
    painter.scale(size * growth / 100.0, size * growth / 100.0)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(32, 74, 48, 35))
    painter.drawEllipse(QRectF(-34, -5, 68, 11))

    if dead:
        painter.setPen(QPen(QColor("#705b4d"), 10, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(QPointF(0, 0), QPointF(-3, -72))
        painter.setPen(QPen(QColor("#705b4d"), 6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        for start, end in (
            ((-2, -48), (-31, -76)), ((-1, -57), (28, -88)),
            ((-19, -65), (-32, -91)), ((17, -76), (34, -70)),
        ):
            painter.drawLine(QPointF(*start), QPointF(*end))
        painter.setPen(QPen(QColor("#9c765e"), 2))
        painter.drawLine(QPointF(1, -2), QPointF(-1, -67))
        painter.restore()
        return

    if species == "pine":
        _draw_pine(painter, progress, sapling)
    else:
        _draw_peach(painter, progress, sapling)
    painter.restore()


def _draw_pine(painter: QPainter, progress: float, sapling: bool) -> None:
    trunk = QLinearGradient(0, -55, 12, 0)
    trunk.setColorAt(0, QColor("#75503a"))
    trunk.setColorAt(1, QColor("#4e3528"))
    painter.setBrush(trunk)
    painter.drawRoundedRect(QRectF(-6, -48, 12, 50), 4, 4)
    layers = ((-82, 35, "#2f6f4e"), (-62, 48, "#3f855a"), (-40, 57, "#54a267"))
    if sapling:
        layers = ((-61, 28, "#3f855a"), (-42, 38, "#54a267"))
    visible = max(1, round(progress * len(layers)))
    for y, width, color in layers[-visible:]:
        painter.setBrush(QColor(color))
        painter.drawPolygon(
            QPolygonF([QPointF(0, y - 35), QPointF(-width, y + 24), QPointF(width, y + 24)])
        )
    painter.setBrush(QColor(255, 255, 255, 24))
    painter.drawPolygon(QPolygonF([QPointF(-3, -111), QPointF(-28, -55), QPointF(-8, -62)]))


def _draw_peach(painter: QPainter, progress: float, sapling: bool) -> None:
    trunk_path = QPainterPath()
    trunk_path.moveTo(-10, 1)
    trunk_path.cubicTo(-8, -25, -7, -53, -3, -72)
    trunk_path.lineTo(5, -72)
    trunk_path.cubicTo(7, -42, 10, -20, 12, 1)
    trunk_path.closeSubpath()
    trunk = QLinearGradient(-10, -40, 12, -35)
    trunk.setColorAt(0, QColor("#684532"))
    trunk.setColorAt(0.55, QColor("#8a5b3d"))
    trunk.setColorAt(1, QColor("#4c3428"))
    painter.setBrush(trunk)
    painter.drawPath(trunk_path)
    painter.setPen(QPen(QColor("#6b4633"), 6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.drawLine(QPointF(0, -54), QPointF(-24, -76))
    painter.drawLine(QPointF(2, -61), QPointF(24, -84))
    painter.setPen(Qt.PenStyle.NoPen)
    clusters = [
        (-31, -80, 32, "#41945a"), (29, -83, 34, "#2f7d4b"),
        (-12, -109, 38, "#2f7d4b"), (18, -112, 36, "#41945a"),
        (0, -84, 43, "#59aa67"), (-40, -104, 25, "#59aa67"),
        (42, -105, 24, "#79bd7c"), (2, -132, 28, "#59aa67"),
    ]
    maximum = 3 if sapling else len(clusters)
    visible = max(2, round(2 + progress * (maximum - 2)))
    for cx, cy, radius, color in clusters[:visible]:
        painter.setBrush(QColor(color))
        painter.drawEllipse(QRectF(cx - radius, cy - radius, radius * 2, radius * 2))
    fruit = [(-22, -101), (24, -91), (4, -124), (38, -112), (-38, -88)]
    for fx, fy in fruit[: 2 if sapling else len(fruit)]:
        painter.setBrush(QColor("#f1a07f"))
        painter.drawEllipse(QRectF(fx - 6, fy - 6, 12, 12))
    painter.setBrush(QColor(255, 255, 255, 33))
    painter.drawEllipse(QRectF(-36, -129, 27, 18))


class TreeWidget(QWidget):
    """Focus-screen preview for selected tree and timer growth."""

    def __init__(self) -> None:
        super().__init__()
        self.progress = 0.0
        self.species = "peach"
        self.final_scale = 0.65
        self.sapling = False
        self.setMinimumSize(255, 255)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_progress(self, progress: float) -> None:
        self.progress = progress
        self.update()

    def set_tree(self, species: str, duration_seconds: int) -> None:
        self.species = species
        self.final_scale = tree_scale(duration_seconds)
        self.sapling = duration_seconds < 30 * 60
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        dark = self.palette().color(QPalette.ColorRole.Window).lightness() < 128
        painter.setPen(Qt.PenStyle.NoPen)
        diameter = min(self.width() - 20, self.height() - 12)
        scene = QRectF((self.width() - diameter) / 2, (self.height() - diameter) / 2, diameter, diameter)
        painter.setBrush(QColor("#22342b") if dark else QColor("#eff8ef"))
        painter.drawEllipse(scene)
        painter.setBrush(QColor(247, 194, 92, 110 if dark else 145))
        painter.drawEllipse(QRectF(scene.right() - 65, scene.top() + 36, 24, 24))
        base = scene.bottom() - 30
        painter.setBrush(QColor("#294437") if dark else QColor("#d9eed8"))
        painter.drawEllipse(QRectF(scene.left() - 25, base - 32, scene.width() * 0.78, 76))
        painter.setBrush(QColor("#31513f") if dark else QColor("#c4e3c5"))
        painter.drawEllipse(QRectF(scene.left() + scene.width() * 0.28, base - 24, scene.width() * 0.82, 67))
        size = min(105.0, diameter * 0.43) * self.final_scale
        draw_tree(
            painter, scene.center().x(), base + 8, size, self.species, self.progress, sapling=self.sapling
        )
