from pathlib import Path
import sqlite3
import tempfile
import unittest

from forest_clone.app import FocusController
from forest_clone.storage import Storage
from forest_clone.timer import TimerState


class Clock:
    def __init__(self, value: float = 1_700_000_000.0) -> None:
        self.value = value

    def __call__(self) -> float:
        return self.value


class StorageControllerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "test.db"
        self.clock = Clock()
        self.storage = Storage(self.path)

    def tearDown(self) -> None:
        self.storage.close()
        self.temp.cleanup()

    def test_completed_session_persists(self) -> None:
        controller = FocusController(self.storage, self.clock)
        controller.start(60)
        self.clock.value += 61
        self.assertTrue(controller.check_completion())
        row = self.storage.sessions()[0]
        self.assertEqual(row["status"], "completed")
        self.assertEqual(row["duration_seconds"], 60)

    def test_tree_preference_updates_only_after_tree_is_planted(self) -> None:
        controller = FocusController(self.storage, self.clock)
        controller.start(60, "pine")
        self.assertEqual(self.storage.get_setting("tree_type", "peach"), "peach")
        self.clock.value += 61
        controller.check_completion()
        self.assertEqual(self.storage.get_setting("tree_type", "peach"), "pine")

    def test_interrupted_tree_becomes_last_preference(self) -> None:
        controller = FocusController(self.storage, self.clock)
        controller.start(60, "pine")
        controller.cancel()
        self.assertEqual(self.storage.get_setting("tree_type", "peach"), "pine")

    def test_interrupted_session_persists_remaining_time(self) -> None:
        controller = FocusController(self.storage, self.clock)
        controller.start(60)
        self.clock.value += 12
        controller.cancel()
        row = self.storage.sessions()[0]
        self.assertEqual(row["status"], "interrupted")
        self.assertEqual(row["remaining_seconds"], 48)

    def test_running_session_restores_after_restart(self) -> None:
        first = FocusController(self.storage, self.clock)
        first.start(100)
        self.clock.value += 30
        restored = FocusController(self.storage, self.clock)
        self.assertEqual(restored.timer.state, TimerState.RUNNING)
        self.assertEqual(restored.timer.remaining_seconds, 70)

    def test_elapsed_session_completes_during_restart(self) -> None:
        first = FocusController(self.storage, self.clock)
        first.start(10)
        self.clock.value += 20
        restored = FocusController(self.storage, self.clock)
        self.assertIsNone(restored.active_session_id)
        self.assertEqual(restored.timer.state, TimerState.IDLE)
        self.assertEqual(self.storage.sessions()[0]["status"], "completed")

    def test_existing_database_migrates_tree_type(self) -> None:
        self.storage.close()
        self.path.unlink()
        connection = sqlite3.connect(self.path)
        connection.execute(
            """CREATE TABLE sessions (
                id INTEGER PRIMARY KEY, started_at REAL NOT NULL,
                duration_seconds INTEGER NOT NULL, status TEXT NOT NULL,
                deadline REAL, remaining_seconds REAL NOT NULL, ended_at REAL
            )"""
        )
        connection.commit()
        connection.close()
        self.storage = Storage(self.path)
        session_id = self.storage.create_session(
            self.clock.value, 60, self.clock.value + 60, "pine"
        )
        self.assertEqual(self.storage.active_session()["tree_type"], "pine")
        self.storage.finish_session(session_id, False)

    def test_paused_session_restores_without_time_loss(self) -> None:
        first = FocusController(self.storage, self.clock)
        first.start(100)
        self.clock.value += 25
        first.pause()
        self.clock.value += 500
        restored = FocusController(self.storage, self.clock)
        self.assertEqual(restored.timer.state, TimerState.PAUSED)
        self.assertEqual(restored.timer.remaining_seconds, 75)


if __name__ == "__main__":
    unittest.main()
