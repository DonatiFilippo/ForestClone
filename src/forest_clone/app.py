"""Small application controller joining timer and persistence."""

from __future__ import annotations

import time
from typing import Callable

from .storage import Storage
from .timer import FocusTimer, TimerState


class FocusController:
    def __init__(
        self, storage: Storage, clock: Callable[[], float] = time.time
    ) -> None:
        self.storage = storage
        self._clock = clock
        self.timer = FocusTimer(clock)
        self.active_session_id: int | None = None
        self._restore_active()

    def _restore_active(self) -> None:
        row = self.storage.active_session()
        if row is None:
            return
        self.active_session_id = int(row["id"])
        state = TimerState(str(row["status"]))
        self.timer.restore(
            state=state,
            duration_seconds=int(row["duration_seconds"]),
            started_at=float(row["started_at"]),
            deadline=float(row["deadline"]) if row["deadline"] is not None else None,
            remaining_seconds=float(row["remaining_seconds"]),
        )
        if self.check_completion():
            # Completion was recovered before UI existed to acknowledge/reset it.
            self.timer.reset()

    def start(self, duration_seconds: int) -> None:
        if self.active_session_id is not None:
            raise RuntimeError("a focus session is already active")
        self.timer.start(duration_seconds)
        self.active_session_id = self.storage.create_session(
            self.timer.started_at or 0.0,
            duration_seconds,
            self.timer.deadline or 0.0,
        )

    def pause(self) -> None:
        self.timer.pause()
        self._persist_active()

    def resume(self) -> None:
        self.timer.resume()
        self._persist_active()

    def cancel(self) -> None:
        if self.active_session_id is None:
            return
        remaining = self.timer.remaining_seconds
        self.storage.finish_session(
            self.active_session_id,
            False,
            ended_at=self._clock(),
            remaining_seconds=remaining,
        )
        self.active_session_id = None
        self.timer.cancel()

    def check_completion(self) -> bool:
        if (
            self.active_session_id is not None
            and self.timer.state == TimerState.COMPLETED
        ):
            self.storage.finish_session(
                self.active_session_id, True, ended_at=self._clock()
            )
            self.active_session_id = None
            return True
        return False

    def _persist_active(self) -> None:
        if self.active_session_id is None:
            return
        snapshot = self.timer.snapshot()
        self.storage.update_active(
            self.active_session_id,
            snapshot.state.value,
            snapshot.deadline,
            snapshot.remaining_seconds,
        )
