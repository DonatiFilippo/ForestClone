"""Main window orchestration for Pocket Forest."""

from __future__ import annotations

from datetime import date, datetime, timedelta
import math

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QListWidget, QMainWindow,
    QMessageBox, QStackedWidget, QVBoxLayout, QWidget,
)

from ..app import FocusController
from ..forest import describe_tree_yield, trees_for_session
from ..notifications import NotificationService
from ..statistics import calculate_statistics, format_duration
from ..storage import Storage
from ..timer import TimerState
from .completion_overlay import CompletionOverlay
from .focus_view import FocusView
from .forest_view import ForestView
from .history_view import HistoryView
from .notification_overlay import NotificationOverlay
from .settings_view import SettingsView
from .theme import apply_theme


class MainWindow(QMainWindow):
    """Coordinates controller, persistence, and independent page widgets."""

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
        self._build_notifications()
        self._connect_signals()
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

        self.focus_view = FocusView()
        self.forest_view = ForestView()
        self.history_view = HistoryView()
        self.settings_view = SettingsView()
        self.pages = QStackedWidget()
        self.pages.setObjectName("pages")
        for page in (self.focus_view, self.forest_view, self.history_view, self.settings_view):
            self.pages.addWidget(page)
        self.navigation.currentRowChanged.connect(self.pages.setCurrentIndex)
        layout.addWidget(sidebar)
        layout.addWidget(self.pages, 1)
        self.setCentralWidget(root)

    def _connect_signals(self) -> None:
        self.data_changed.connect(self.refresh_data_views)
        self.focus_view.primary_requested.connect(self._primary_action)
        self.focus_view.cancel_requested.connect(self._cancel)
        self.focus_view.selection_changed.connect(self._tree_selection_changed)
        self.forest_view.period_moved.connect(self._move_forest_period)
        self.forest_view.scope_changed.connect(self._refresh_forest)
        self.settings_view.save_requested.connect(self._save_settings)

    def _build_notifications(self) -> None:
        self.notification_overlay = NotificationOverlay(self.centralWidget())
        self.completion_overlay = CompletionOverlay(self.centralWidget())
        self.notifications = NotificationService(
            self, self.notification_overlay, self.completion_overlay
        )
        self.setWindowIcon(self.notifications.tray.icon())

    def resizeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        super().resizeEvent(event)
        if hasattr(self, "notification_overlay"):
            self.notification_overlay.reposition()
        if hasattr(self, "completion_overlay"):
            self.completion_overlay.resize_to_parent()

    def _tree_selection_changed(self, *_args: object) -> None:
        if self.controller.timer.state != TimerState.IDLE:
            return
        self.focus_view.update_tree_preview()
        self._tick()

    def _primary_action(self) -> None:
        state = self.controller.timer.state
        try:
            if state == TimerState.IDLE:
                self.controller.start(
                    self.focus_view.selected_minutes() * 60,
                    self.focus_view.selected_species(),
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
            "This session will be recorded as interrupted and leave a withered tree.",
        )
        if answer == QMessageBox.StandardButton.Yes:
            timer = self.controller.timer
            elapsed = max(0, timer.duration_seconds - round(timer.remaining_seconds))
            species = self.controller.tree_type
            self.controller.cancel()
            self.data_changed.emit()
            self._tick()
            self.notifications.notify(
                "Session interrupted",
                f"Focus stopped after {format_duration(elapsed)}. One withered {species} remains in your forest.",
                level="warning",
                desktop_enabled=self.settings_view.notifications.isChecked(),
                view_action=self._show_forest,
            )

    def _tick(self) -> None:
        completed = self.controller.check_completion()
        timer = self.controller.timer
        remaining = math.ceil(timer.remaining_seconds)
        self.focus_view.update_timer(timer.state, remaining, timer.progress)
        if completed:
            self.data_changed.emit()
            self._notify_completion()
            timer.reset()
            self._tick()

    def _notify_completion(self) -> None:
        timer = self.controller.timer
        message = describe_tree_yield(timer.duration_seconds, self.controller.tree_type)
        self.notifications.notify_completion(
            f"{message}. Nice work!",
            self.controller.tree_type,
            timer.duration_seconds,
            desktop_enabled=self.settings_view.notifications.isChecked(),
            view_action=self._show_forest,
            plant_action=self._plant_another,
        )

    def _plant_another(self) -> None:
        self.showNormal()
        self.navigation.setCurrentRow(0)
        self.focus_view.update_tree_preview()
        self.raise_()
        self.activateWindow()

    def _show_forest(self) -> None:
        self.showNormal()
        self.navigation.setCurrentRow(1)
        self.raise_()
        self.activateWindow()

    def _forest_period_bounds(self) -> tuple[date | None, date | None, str]:
        scope = self.forest_view.scope.currentText()
        anchor = self.forest_anchor
        if scope == "Day":
            return anchor, anchor, anchor.strftime("%A, %B %d, %Y")
        if scope == "Week":
            start = anchor - timedelta(days=anchor.weekday())
            end = start + timedelta(days=6)
            label = (
                f"{start.strftime('%b %d')} – {end.strftime('%d, %Y')}"
                if start.month == end.month
                else f"{start.strftime('%b %d')} – {end.strftime('%b %d, %Y')}"
            )
            return start, end, label
        if scope == "Month":
            start = anchor.replace(day=1)
            next_month = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
            return start, next_month - timedelta(days=1), start.strftime("%B %Y")
        return None, None, "All-time forest"

    def _move_forest_period(self, direction: int) -> None:
        scope = self.forest_view.scope.currentText()
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
            row for row in self._sessions
            if row["status"] in ("completed", "interrupted")  # type: ignore[index]
        ]
        visible = (
            [
                row for row in finished
                if start <= datetime.fromtimestamp(float(row["started_at"])).date() <= end  # type: ignore[index,operator]
            ]
            if start is not None and end is not None else finished
        )
        focused = sum(
            int(row["duration_seconds"]) for row in visible  # type: ignore[index]
            if row["status"] == "completed"  # type: ignore[index]
        )
        models = [
            tree for session in visible for tree in trees_for_session(session)  # type: ignore[arg-type]
        ]
        live = sum(not tree.dead for tree in models)
        dead = sum(tree.dead for tree in models)
        dead_label = f"  •  {dead} WITHERED" if dead else ""
        summary = (
            f"{live} {'TREE' if live == 1 else 'TREES'}{dead_label}"
            f"  •  {format_duration(focused)} FOCUS"
        )
        self.forest_view.set_period(
            label, summary, visible, end is not None and end < date.today()
        )

    def refresh_data_views(self) -> None:
        sessions = self.storage.sessions()
        self._sessions = sessions
        stats = calculate_statistics(sessions)
        self.focus_view.update_stats(
            format_duration(stats.today_seconds),
            stats.trees_planted,
            stats.streak_days,
            format_duration(stats.focused_seconds),
        )
        self._refresh_forest()
        self.history_view.set_sessions(sessions)

    def _load_settings(self) -> None:
        minutes = int(self.storage.get_setting("default_duration", "25"))
        self.settings_view.default_duration.setValue(minutes)
        self.focus_view.set_duration(minutes)
        species = (
            self.controller.tree_type
            if self.controller.active_session_id is not None
            else self.storage.get_setting("tree_type", "peach")
        )
        self.focus_view.set_species(species)
        preview_duration = self.controller.timer.duration_seconds or minutes * 60
        self.focus_view.tree.set_tree(species, preview_duration)
        self.settings_view.notifications.setChecked(
            self.storage.get_setting("notifications", "1") == "1"
        )
        theme = self.storage.get_setting("theme", "System")
        self.settings_view.theme.setCurrentText(theme)
        self._apply_theme(theme)

    def _save_settings(self) -> None:
        settings = self.settings_view
        self.storage.set_setting("default_duration", str(settings.default_duration.value()))
        self.storage.set_setting("notifications", "1" if settings.notifications.isChecked() else "0")
        self.storage.set_setting("theme", settings.theme.currentText())
        if self.controller.timer.state == TimerState.IDLE:
            self.focus_view.set_duration(settings.default_duration.value())
        self._apply_theme(settings.theme.currentText())

    def _apply_theme(self, theme: str) -> None:
        app = QApplication.instance()
        if isinstance(app, QApplication):
            apply_theme(app, theme)
        self.focus_view.tree.update()
        self.forest_view.canvas.update()
