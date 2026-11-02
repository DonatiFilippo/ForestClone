from __future__ import annotations

from datetime import date, datetime, timedelta
import math

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPalette, QPen, QPolygonF
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
    QStyle,
    QSystemTrayIcon,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..app import FocusController
from ..forest import TreeModel, live_tree_count, tree_scale, trees_for_session
from ..statistics import calculate_statistics, format_duration
from ..storage import Storage
from ..timer import TimerState


def _draw_tree(
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
        painter.drawLine(QPointF(-2, -48), QPointF(-31, -76))
        painter.drawLine(QPointF(-1, -57), QPointF(28, -88))
        painter.drawLine(QPointF(-19, -65), QPointF(-32, -91))
        painter.drawLine(QPointF(17, -76), QPointF(34, -70))
        painter.setPen(QPen(QColor("#9c765e"), 2))
        painter.drawLine(QPointF(1, -2), QPointF(-1, -67))
        painter.restore()
        return

    if species == "pine":
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
    else:
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
        # Peach fruit makes species identifiable without text.
        fruit = [(-22, -101), (24, -91), (4, -124), (38, -112), (-38, -88)]
        for fx, fy in fruit[: 2 if sapling else len(fruit)]:
            painter.setBrush(QColor("#f1a07f"))
            painter.drawEllipse(QRectF(fx - 6, fy - 6, 12, 12))
        painter.setBrush(QColor(255, 255, 255, 33))
        painter.drawEllipse(QRectF(-36, -129, 27, 18))

    painter.restore()


class TreeWidget(QWidget):
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
        sky = QColor("#22342b") if dark else QColor("#eff8ef")
        hill_back = QColor("#294437") if dark else QColor("#d9eed8")
        hill_front = QColor("#31513f") if dark else QColor("#c4e3c5")
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(sky)
        diameter = min(self.width() - 20, self.height() - 12)
        scene = QRectF((self.width() - diameter) / 2, (self.height() - diameter) / 2, diameter, diameter)
        painter.drawEllipse(scene)
        painter.setBrush(QColor(247, 194, 92, 110 if dark else 145))
        painter.drawEllipse(QRectF(scene.right() - 65, scene.top() + 36, 24, 24))
        base = scene.bottom() - 30
        painter.setBrush(hill_back)
        painter.drawEllipse(QRectF(scene.left() - 25, base - 32, scene.width() * 0.78, 76))
        painter.setBrush(hill_front)
        painter.drawEllipse(QRectF(scene.left() + scene.width() * 0.28, base - 24, scene.width() * 0.82, 67))
        size = min(105.0, diameter * 0.43) * self.final_scale
        _draw_tree(
            painter, scene.center().x(), base + 8, size, self.species, self.progress, sapling=self.sapling
        )


class ForestCanvas(QWidget):
    """Scrollable procedural terrain populated by completed sessions."""

    TREES_PER_CLEARING = 18
    CLEARING_HEIGHT = 390

    def __init__(self) -> None:
        super().__init__()
        self.sessions: list[object] = []
        self.trees: list[TreeModel] = []
        self.setMinimumHeight(self.CLEARING_HEIGHT)

    def set_sessions(self, sessions: list[object]) -> None:
        self.sessions = sessions
        self.trees = [
            tree for session in sessions for tree in trees_for_session(session)  # type: ignore[arg-type]
        ]
        self._update_height()
        self.update()

    def resizeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        self._update_height()
        super().resizeEvent(event)

    def _update_height(self) -> None:
        clearings = max(1, math.ceil(len(self.trees) / self.TREES_PER_CLEARING))
        self.setMinimumHeight(clearings * self.CLEARING_HEIGHT)

    def paintEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        dark = self.palette().color(QPalette.ColorRole.Window).lightness() < 128
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

        # Sun and distant rolling hills.
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

        # Winding stream and walking path make clearing read as terrain, not grid.
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

        # Deterministic stones and small flowers; zero timer/CPU cost after paint.
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
        for local, session_index in enumerate(range(start, end)):
            row, slot = divmod(local, 6)
            column = column_order[slot]
            jitter_x = ((session_index * 37) % 25) - 12
            jitter_y = ((session_index * 23) % 19) - 9
            x = (column + 0.48) * width / 6 + jitter_x
            ground = top + 224 + row * 66 + jitter_y
            river_x = width * (0.66 - 0.09 * ((ground - top - 175) / 215))
            if abs(x - river_x) < 45:
                x += -58 if column < 3 else 58
            model = self.trees[session_index]
            size = (58 + row * 7 + (session_index * 7) % 8) * model.scale
            placements.append((ground, x, size, model))
        for ground, x, size, model in sorted(placements, key=lambda item: item[0]):
            _draw_tree(
                painter,
                x,
                ground,
                size,
                model.species,
                1.0,
                dead=model.dead,
                sapling=model.sapling,
            )


class MainWindow(QMainWindow):
    data_changed = Signal()

    def __init__(self, controller: FocusController, storage: Storage) -> None:
        super().__init__()
        self.controller = controller
        self.storage = storage
        self.forest_anchor = date.today()
        self._sessions: list[object] = []
        self.setWindowTitle("Pocket Forest")
        self.resize(940, 650)
        self.setMinimumSize(760, 540)
        self._build_ui()
        self._build_tray()
        self.data_changed.connect(self.refresh_data_views)
        self.tick_timer = QTimer(self)
        self.tick_timer.setInterval(500)
        self.tick_timer.timeout.connect(self._tick)
        self.tick_timer.start()
        self._load_settings()
        self.refresh_data_views()
        self._tick()

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("root")
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(184)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(18, 24, 18, 20)
        brand = QLabel("●  POCKET\n    FOREST")
        brand.setObjectName("brand")
        tagline = QLabel("Focus. Grow. Repeat.")
        tagline.setObjectName("tagline")
        self.navigation = QListWidget()
        self.navigation.setObjectName("navigation")
        self.navigation.addItems(["  Focus", "  Forest", "  History", "  Settings"])
        self.navigation.setCurrentRow(0)
        self.navigation.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        side_layout.addWidget(brand)
        side_layout.addWidget(tagline)
        side_layout.addSpacing(30)
        side_layout.addWidget(self.navigation)
        side_layout.addStretch()
        local_label = QLabel("Offline  •  Private")
        local_label.setObjectName("localLabel")
        side_layout.addWidget(local_label)

        self.pages = QStackedWidget()
        self.pages.setObjectName("pages")
        self.pages.addWidget(self._focus_page())
        self.pages.addWidget(self._forest_page())
        self.pages.addWidget(self._history_page())
        self.pages.addWidget(self._settings_page())
        self.navigation.currentRowChanged.connect(self.pages.setCurrentIndex)
        layout.addWidget(sidebar)
        layout.addWidget(self.pages, 1)
        self.setCentralWidget(root)

    @staticmethod
    def _page_header(title: str, subtitle: str) -> tuple[QLabel, QLabel]:
        heading = QLabel(title)
        heading.setObjectName("pageTitle")
        caption = QLabel(subtitle)
        caption.setObjectName("pageSubtitle")
        return heading, caption

    @staticmethod
    def _stat_card(label: str) -> tuple[QFrame, QLabel]:
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
        return card, value

    def _focus_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("page")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(34, 28, 34, 26)
        layout.setSpacing(18)
        heading, caption = self._page_header("Focus session", "One task. One tree. Give it your full attention.")
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
        self.session_status = QLabel("READY TO FOCUS")
        self.session_status.setObjectName("sessionStatus")
        self.session_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.timer_label = QLabel("25:00")
        self.timer_label.setObjectName("timerLabel")
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress = QProgressBar()
        self.progress.setObjectName("sessionProgress")
        self.progress.setRange(0, 1000)
        self.progress.setTextVisible(False)
        controls.addWidget(self.session_status)
        controls.addWidget(self.timer_label)
        controls.addWidget(self.progress)

        duration_row = QHBoxLayout()
        duration_label = QLabel("Session length")
        duration_label.setObjectName("fieldLabel")
        self.duration = QComboBox()
        for minutes in (15, 25, 45, 60):
            self.duration.addItem(f"{minutes} min", minutes)
        self.duration.addItem("Custom", None)
        self.duration.setCurrentIndex(1)
        self.duration.currentIndexChanged.connect(self._duration_changed)
        self.custom_duration = QSpinBox()
        self.custom_duration.setRange(1, 480)
        self.custom_duration.setSuffix(" min")
        self.custom_duration.setValue(25)
        self.custom_duration.valueChanged.connect(self._tree_selection_changed)
        self.custom_duration.hide()
        duration_row.addWidget(duration_label)
        duration_row.addStretch()
        duration_row.addWidget(self.duration)
        duration_row.addWidget(self.custom_duration)
        controls.addLayout(duration_row)

        species_row = QHBoxLayout()
        species_label = QLabel("Tree to plant")
        species_label.setObjectName("fieldLabel")
        self.tree_species = QComboBox()
        self.tree_species.addItem("Peach tree", "peach")
        self.tree_species.addItem("Pine tree", "pine")
        self.tree_species.currentIndexChanged.connect(self._tree_selection_changed)
        species_row.addWidget(species_label)
        species_row.addStretch()
        species_row.addWidget(self.tree_species)
        controls.addLayout(species_row)

        buttons = QHBoxLayout()
        self.primary_button = QPushButton("Start focusing")
        self.primary_button.setObjectName("primaryButton")
        self.primary_button.setDefault(True)
        self.primary_button.clicked.connect(self._primary_action)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setObjectName("secondaryButton")
        self.cancel_button.clicked.connect(self._cancel)
        self.cancel_button.hide()
        buttons.addWidget(self.primary_button, 1)
        buttons.addWidget(self.cancel_button)
        controls.addLayout(buttons)
        controls.addStretch()
        card_layout.addLayout(controls, 4)
        layout.addWidget(card, 1)

        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)
        today_card, self.today_value = self._stat_card("FOCUS TODAY")
        trees_card, self.trees_value = self._stat_card("TREES GROWN")
        streak_card, self.streak_value = self._stat_card("DAY STREAK")
        total_card, self.total_value = self._stat_card("TOTAL FOCUS")
        for stat in (today_card, trees_card, streak_card, total_card):
            stats_row.addWidget(stat)
        layout.addLayout(stats_row)
        return page

    def _forest_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("page")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(34, 28, 34, 26)
        layout.setSpacing(8)
        self.forest_title, caption = self._page_header("Your forest", "Explore completed sessions across a living landscape.")
        self.forest_count = QLabel("0 TREES PLANTED")
        self.forest_count.setObjectName("eyebrow")

        period_bar = QFrame()
        period_bar.setObjectName("periodBar")
        period_layout = QHBoxLayout(period_bar)
        period_layout.setContentsMargins(12, 8, 12, 8)
        period_layout.setSpacing(8)
        self.forest_previous = QPushButton("‹")
        self.forest_previous.setObjectName("periodButton")
        self.forest_previous.setToolTip("Previous period")
        self.forest_previous.clicked.connect(lambda: self._move_forest_period(-1))
        self.forest_period_label = QLabel()
        self.forest_period_label.setObjectName("periodLabel")
        self.forest_period_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.forest_next = QPushButton("›")
        self.forest_next.setObjectName("periodButton")
        self.forest_next.setToolTip("Next period")
        self.forest_next.clicked.connect(lambda: self._move_forest_period(1))
        self.forest_scope = QComboBox()
        self.forest_scope.setObjectName("scopePicker")
        self.forest_scope.addItems(["Day", "Week", "Month", "All"])
        self.forest_scope.setCurrentText("Week")
        self.forest_scope.currentTextChanged.connect(self._refresh_forest)
        period_layout.addWidget(self.forest_previous)
        period_layout.addWidget(self.forest_period_label, 1)
        period_layout.addWidget(self.forest_next)
        period_layout.addSpacing(8)
        period_layout.addWidget(self.forest_scope)

        self.forest_canvas = ForestCanvas()
        scroll = QScrollArea()
        scroll.setObjectName("forestScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(self.forest_canvas)
        layout.addWidget(self.forest_title)
        layout.addWidget(caption)
        layout.addWidget(self.forest_count)
        layout.addSpacing(8)
        layout.addWidget(period_bar)
        layout.addWidget(scroll, 1)
        return page

    def _history_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("page")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(34, 28, 34, 28)
        layout.setSpacing(8)
        title, caption = self._page_header("Session history", "A clear record of focused and interrupted sessions.")
        self.history = QTableWidget(0, 4)
        self.history.setObjectName("historyTable")
        self.history.setHorizontalHeaderLabels(["DATE", "START", "DURATION", "STATUS"])
        self.history.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.history.verticalHeader().hide()
        self.history.verticalHeader().setDefaultSectionSize(46)
        self.history.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.history.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.history.setShowGrid(False)
        layout.addWidget(title)
        layout.addWidget(caption)
        layout.addSpacing(16)
        layout.addWidget(self.history, 1)
        return page

    def _settings_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("page")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(34, 28, 34, 28)
        layout.setSpacing(8)
        title, caption = self._page_header("Settings", "Shape Pocket Forest around your focus routine.")
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
        save.clicked.connect(self._save_settings)
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
        return page

    def _build_tray(self) -> None:
        icon = self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        self.tray = QSystemTrayIcon(icon, self)
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.show()

    def _selected_minutes(self) -> int:
        value = self.duration.currentData()
        return self.custom_duration.value() if value is None else int(value)

    def _duration_changed(self) -> None:
        custom = self.duration.currentData() is None
        self.custom_duration.setVisible(custom)
        if self.controller.timer.state == TimerState.IDLE:
            self.timer_label.setText(f"{self._selected_minutes():02d}:00")
            self._tree_selection_changed()

    def _tree_selection_changed(self, *_args: object) -> None:
        if self.controller.timer.state != TimerState.IDLE:
            return
        species = str(self.tree_species.currentData())
        self.tree.set_tree(species, self._selected_minutes() * 60)
        self.storage.set_setting("tree_type", species)

    def _primary_action(self) -> None:
        state = self.controller.timer.state
        try:
            if state == TimerState.IDLE:
                self.controller.start(
                    self._selected_minutes() * 60, str(self.tree_species.currentData())
                )
            elif state == TimerState.RUNNING:
                self.controller.pause()
            elif state == TimerState.PAUSED:
                self.controller.resume()
        except (RuntimeError, ValueError) as error:
            QMessageBox.warning(self, "Could not update timer", str(error))
        self.data_changed.emit()
        self._tick()

    def _cancel(self) -> None:
        answer = QMessageBox.question(
            self,
            "Cancel focus session?",
            "This session will be recorded as interrupted.",
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.controller.cancel()
            self.data_changed.emit()
            self._tick()

    def _tick(self) -> None:
        completed = self.controller.check_completion()
        timer = self.controller.timer
        remaining = math.ceil(timer.remaining_seconds)
        minutes, seconds = divmod(remaining, 60)
        if timer.state == TimerState.IDLE:
            minutes, seconds = self._selected_minutes(), 0
        self.timer_label.setText(f"{minutes:02d}:{seconds:02d}")
        self.progress.setValue(round(timer.progress * 1000))
        active = timer.state in (TimerState.RUNNING, TimerState.PAUSED)
        # Idle state previews next mature tree; active session grows it from sapling.
        self.tree.set_progress(timer.progress if active else 1.0)
        self.duration.setEnabled(not active)
        self.custom_duration.setEnabled(not active)
        self.tree_species.setEnabled(not active)
        self.cancel_button.setVisible(active)
        state_text = {
            TimerState.IDLE: "READY TO FOCUS",
            TimerState.RUNNING: "FOCUSING — TREE GROWING",
            TimerState.PAUSED: "SESSION PAUSED",
            TimerState.COMPLETED: "SESSION COMPLETE",
        }
        self.session_status.setText(state_text[timer.state])
        self.primary_button.setText(
            "Pause session"
            if timer.state == TimerState.RUNNING
            else "Resume session"
            if timer.state == TimerState.PAUSED
            else "Start focusing"
        )
        if completed:
            self.data_changed.emit()
            self._notify_completion()
            timer.reset()
            self._tick()

    def _notify_completion(self) -> None:
        QApplication.alert(self, 5000)
        planted = live_tree_count(self.controller.timer.duration_seconds)
        message = f"{planted} {'tree' if planted == 1 else 'trees'} planted. Nice work!"
        if self.notifications.isChecked() and self.tray.isVisible():
            self.tray.showMessage(
                "Focus complete",
                message,
                QSystemTrayIcon.MessageIcon.Information,
                5000,
            )
        else:
            QMessageBox.information(self, "Focus complete", message)

    def _forest_period_bounds(self) -> tuple[date | None, date | None, str]:
        scope = self.forest_scope.currentText()
        anchor = self.forest_anchor
        if scope == "Day":
            return anchor, anchor, anchor.strftime("%A, %B %d, %Y")
        if scope == "Week":
            start = anchor - timedelta(days=anchor.weekday())
            end = start + timedelta(days=6)
            if start.month == end.month:
                label = f"{start.strftime('%b %d')} – {end.strftime('%d, %Y')}"
            else:
                label = f"{start.strftime('%b %d')} – {end.strftime('%b %d, %Y')}"
            return start, end, label
        if scope == "Month":
            start = anchor.replace(day=1)
            next_month = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
            return start, next_month - timedelta(days=1), start.strftime("%B %Y")
        return None, None, "All-time forest"

    def _move_forest_period(self, direction: int) -> None:
        scope = self.forest_scope.currentText()
        if scope == "Day":
            self.forest_anchor += timedelta(days=direction)
        elif scope == "Week":
            self.forest_anchor += timedelta(days=direction * 7)
        elif scope == "Month":
            month_index = self.forest_anchor.year * 12 + self.forest_anchor.month - 1 + direction
            year, month_zero = divmod(month_index, 12)
            self.forest_anchor = date(year, month_zero + 1, 1)
        self._refresh_forest()

    def _refresh_forest(self, *_args: object) -> None:
        start, end, label = self._forest_period_bounds()
        finished = [
            row
            for row in self._sessions
            if row["status"] in ("completed", "interrupted")  # type: ignore[index]
        ]
        if start is not None and end is not None:
            visible = [
                row
                for row in finished
                if start <= datetime.fromtimestamp(float(row["started_at"])).date() <= end  # type: ignore[index]
            ]
        else:
            visible = finished
        focused = sum(
            int(row["duration_seconds"])
            for row in visible
            if row["status"] == "completed"  # type: ignore[index]
        )
        models = [
            tree for session in visible for tree in trees_for_session(session)  # type: ignore[arg-type]
        ]
        live = sum(not tree.dead for tree in models)
        dead = sum(tree.dead for tree in models)
        dead_label = f"  •  {dead} WITHERED" if dead else ""
        self.forest_period_label.setText(label)
        self.forest_count.setText(
            f"{live} {'TREE' if live == 1 else 'TREES'}{dead_label}  •  {format_duration(focused)} FOCUS"
        )
        self.forest_canvas.set_sessions(visible)
        all_time = self.forest_scope.currentText() == "All"
        self.forest_previous.setEnabled(not all_time)
        self.forest_next.setEnabled(not all_time and end is not None and end < date.today())

    def refresh_data_views(self) -> None:
        sessions = self.storage.sessions()
        self._sessions = sessions
        stats = calculate_statistics(sessions)
        self.today_value.setText(format_duration(stats.today_seconds))
        self.trees_value.setText(str(stats.trees_planted))
        self.streak_value.setText(f"{stats.streak_days} days")
        self.total_value.setText(format_duration(stats.focused_seconds))
        self._refresh_forest()
        self.history.setRowCount(len(sessions))
        labels = {
            "completed": "Completed",
            "interrupted": "Interrupted",
            "running": "In progress",
            "paused": "Paused",
        }
        status_colors = {
            "completed": QColor("#3f9158"),
            "interrupted": QColor("#b65d57"),
            "running": QColor("#3b7f98"),
            "paused": QColor("#b4863e"),
        }
        for row_index, row in enumerate(sessions):
            started = datetime.fromtimestamp(float(row["started_at"]))
            status = str(row["status"])
            values = (
                started.strftime("%b %d, %Y"),
                started.strftime("%H:%M"),
                format_duration(int(row["duration_seconds"])),
                labels[status],
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 3:
                    item.setForeground(status_colors[status])
                self.history.setItem(row_index, column, item)

    def _load_settings(self) -> None:
        minutes = int(self.storage.get_setting("default_duration", "25"))
        self.default_duration.setValue(minutes)
        standard = self.duration.findData(minutes)
        if standard >= 0:
            self.duration.setCurrentIndex(standard)
        else:
            self.duration.setCurrentIndex(self.duration.count() - 1)
            self.custom_duration.setValue(minutes)
        species = (
            self.controller.tree_type
            if self.controller.active_session_id is not None
            else self.storage.get_setting("tree_type", "peach")
        )
        species_index = self.tree_species.findData(species)
        self.tree_species.setCurrentIndex(max(0, species_index))
        self.tree.set_tree(species, self.controller.timer.duration_seconds or minutes * 60)
        self.notifications.setChecked(self.storage.get_setting("notifications", "1") == "1")
        theme = self.storage.get_setting("theme", "System")
        self.theme.setCurrentText(theme)
        self._apply_theme(theme)

    def _save_settings(self) -> None:
        self.storage.set_setting("default_duration", str(self.default_duration.value()))
        self.storage.set_setting("notifications", "1" if self.notifications.isChecked() else "0")
        self.storage.set_setting("theme", self.theme.currentText())
        if self.controller.timer.state == TimerState.IDLE:
            minutes = self.default_duration.value()
            index = self.duration.findData(minutes)
            if index >= 0:
                self.duration.setCurrentIndex(index)
            else:
                self.duration.setCurrentIndex(self.duration.count() - 1)
                self.custom_duration.setValue(minutes)
        self._apply_theme(self.theme.currentText())

    def _apply_theme(self, theme: str) -> None:
        app = QApplication.instance()
        system_dark = app.palette().color(QPalette.ColorRole.Window).lightness() < 128
        dark = theme == "Dark" or (theme == "System" and system_dark)
        if dark:
            colors = {
                "bg": "#141b18",
                "surface": "#1d2722",
                "surface2": "#24312a",
                "border": "#34463c",
                "text": "#eef5f0",
                "muted": "#98a99e",
                "input": "#26342d",
                "sidebar": "#15251d",
            }
        else:
            colors = {
                "bg": "#f3f6f2",
                "surface": "#ffffff",
                "surface2": "#f7faf7",
                "border": "#dce6dd",
                "text": "#203027",
                "muted": "#718077",
                "input": "#f8faf8",
                "sidebar": "#183f2b",
            }
        app.setStyleSheet(
            f"""
            * {{ font-family: 'Inter', 'Segoe UI', sans-serif; }}
            QWidget#root, QWidget#page, QStackedWidget#pages {{ background: {colors['bg']}; color: {colors['text']}; }}
            QFrame#sidebar {{ background: {colors['sidebar']}; border: none; }}
            QLabel#brand {{ color: #f1f8f3; font-size: 17px; font-weight: 800; letter-spacing: 1px; }}
            QLabel#tagline, QLabel#localLabel {{ color: #9fc2ac; font-size: 11px; }}
            QListWidget#navigation {{ background: transparent; color: #b9d0c1; border: none; outline: none; font-size: 14px; }}
            QListWidget#navigation::item {{ height: 44px; padding-left: 8px; margin: 3px 0; border-radius: 8px; }}
            QListWidget#navigation::item:selected {{ background: #2d6548; color: white; font-weight: 600; }}
            QListWidget#navigation::item:hover:!selected {{ background: #204c35; color: white; }}
            QLabel#pageTitle {{ color: {colors['text']}; font-size: 27px; font-weight: 750; }}
            QLabel#pageSubtitle {{ color: {colors['muted']}; font-size: 13px; }}
            QLabel#eyebrow, QLabel#sessionStatus {{ color: #4c9663; font-size: 10px; font-weight: 800; letter-spacing: 1px; }}
            QFrame#focusCard, QFrame#settingsCard, QFrame#statCard, QFrame#periodBar {{ background: {colors['surface']}; border: 1px solid {colors['border']}; border-radius: 14px; }}
            QLabel#timerLabel {{ color: {colors['text']}; font-size: 52px; font-weight: 650; letter-spacing: 2px; }}
            QLabel#fieldLabel {{ color: {colors['muted']}; font-size: 12px; }}
            QLabel#statValue {{ color: {colors['text']}; font-size: 20px; font-weight: 700; }}
            QLabel#statLabel {{ color: {colors['muted']}; font-size: 9px; font-weight: 700; letter-spacing: 1px; }}
            QPushButton {{ min-height: 34px; padding: 0 16px; border-radius: 8px; font-weight: 600; }}
            QPushButton#primaryButton {{ color: white; background: #438f59; border: 1px solid #438f59; }}
            QPushButton#primaryButton:hover {{ background: #367e4c; border-color: #367e4c; }}
            QPushButton#primaryButton:pressed {{ background: #2e6e42; }}
            QPushButton#secondaryButton {{ color: {colors['text']}; background: transparent; border: 1px solid {colors['border']}; }}
            QPushButton#secondaryButton:hover {{ background: {colors['surface2']}; }}
            QPushButton#periodButton {{ min-width: 34px; max-width: 34px; padding: 0; color: {colors['text']}; background: {colors['surface2']}; border: 1px solid {colors['border']}; font-size: 21px; }}
            QPushButton#periodButton:hover {{ border-color: #63a574; background: {colors['input']}; }}
            QLabel#periodLabel {{ color: {colors['text']}; font-size: 13px; font-weight: 650; }}
            QPushButton:disabled {{ background: {colors['border']}; color: {colors['muted']}; border-color: {colors['border']}; }}
            QComboBox, QSpinBox {{ min-height: 34px; padding: 0 10px; color: {colors['text']}; background: {colors['input']}; border: 1px solid {colors['border']}; border-radius: 7px; }}
            QComboBox:hover, QSpinBox:hover {{ border-color: #63a574; }}
            QComboBox::drop-down {{ border: none; width: 24px; }}
            QComboBox QAbstractItemView {{ color: {colors['text']}; background: {colors['surface']}; selection-background-color: #438f59; border: 1px solid {colors['border']}; }}
            QProgressBar#sessionProgress {{ min-height: 7px; max-height: 7px; background: {colors['border']}; border: none; border-radius: 3px; }}
            QProgressBar#sessionProgress::chunk {{ background: #55a76b; border-radius: 3px; }}
            QScrollArea#forestScroll {{ background: transparent; border: none; }}
            QScrollArea#forestScroll > QWidget > QWidget {{ background: {colors['surface']}; border-radius: 14px; }}
            QTableWidget#historyTable {{ color: {colors['text']}; background: {colors['surface']}; alternate-background-color: {colors['surface2']}; border: 1px solid {colors['border']}; border-radius: 12px; selection-background-color: #dcefe1; selection-color: #203027; outline: none; }}
            QTableWidget#historyTable::item {{ padding-left: 12px; border-bottom: 1px solid {colors['border']}; }}
            QHeaderView::section {{ color: {colors['muted']}; background: {colors['surface2']}; border: none; border-bottom: 1px solid {colors['border']}; padding: 12px; font-size: 10px; font-weight: 700; }}
            QCheckBox {{ color: {colors['text']}; spacing: 9px; }}
            QCheckBox::indicator {{ width: 17px; height: 17px; border: 1px solid {colors['border']}; border-radius: 4px; background: {colors['input']}; }}
            QCheckBox::indicator:checked {{ background: #438f59; border-color: #438f59; }}
            QFormLayout QLabel {{ color: {colors['text']}; }}
            QToolTip {{ color: {colors['text']}; background: {colors['surface']}; border: 1px solid {colors['border']}; }}
            """
        )
        self.tree.update()
        self.forest_canvas.update()
