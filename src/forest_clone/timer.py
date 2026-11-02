"""Accurate, UI-independent focus timer state machine."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import time
from typing import Callable


class TimerState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"


@dataclass(frozen=True)
class TimerSnapshot:
    state: TimerState
    duration_seconds: int
    remaining_seconds: float
    started_at: float | None
    deadline: float | None


class FocusTimer:
    """Timer using absolute wall-clock deadlines rather than tick counting."""

    def __init__(self, clock: Callable[[], float] = time.time) -> None:
        self._clock = clock
        self.reset()

    @property
    def state(self) -> TimerState:
        self._update_completion()
        return self._state

    @property
    def duration_seconds(self) -> int:
        return self._duration_seconds

    @property
    def started_at(self) -> float | None:
        return self._started_at

    @property
    def deadline(self) -> float | None:
        return self._deadline

    @property
    def remaining_seconds(self) -> float:
        if self._state == TimerState.RUNNING and self._deadline is not None:
            remaining = max(0.0, self._deadline - self._clock())
            if remaining == 0:
                self._state = TimerState.COMPLETED
            return remaining
        return max(0.0, self._remaining_seconds)

    @property
    def progress(self) -> float:
        if not self._duration_seconds:
            return 0.0
        return min(1.0, 1.0 - self.remaining_seconds / self._duration_seconds)

    def start(self, duration_seconds: int) -> None:
        if duration_seconds <= 0:
            raise ValueError("duration_seconds must be positive")
        now = self._clock()
        self._state = TimerState.RUNNING
        self._duration_seconds = int(duration_seconds)
        self._remaining_seconds = float(duration_seconds)
        self._started_at = now
        self._deadline = now + duration_seconds

    def pause(self) -> None:
        if self.state != TimerState.RUNNING:
            raise RuntimeError("only a running timer can be paused")
        self._remaining_seconds = self.remaining_seconds
        self._deadline = None
        self._state = TimerState.PAUSED

    def resume(self) -> None:
        if self._state != TimerState.PAUSED:
            raise RuntimeError("only a paused timer can be resumed")
        self._deadline = self._clock() + self._remaining_seconds
        self._state = TimerState.RUNNING

    def cancel(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._state = TimerState.IDLE
        self._duration_seconds = 0
        self._remaining_seconds = 0.0
        self._started_at = None
        self._deadline = None

    def restore(
        self,
        *,
        state: TimerState,
        duration_seconds: int,
        started_at: float,
        deadline: float | None,
        remaining_seconds: float,
    ) -> None:
        if state not in (TimerState.RUNNING, TimerState.PAUSED):
            raise ValueError("only active timer states can be restored")
        self._state = state
        self._duration_seconds = duration_seconds
        self._started_at = started_at
        self._deadline = deadline if state == TimerState.RUNNING else None
        self._remaining_seconds = remaining_seconds
        self._update_completion()

    def snapshot(self) -> TimerSnapshot:
        remaining = self.remaining_seconds
        return TimerSnapshot(
            self._state,
            self._duration_seconds,
            remaining,
            self._started_at,
            self._deadline,
        )

    def _update_completion(self) -> None:
        if (
            self._state == TimerState.RUNNING
            and self._deadline is not None
            and self._clock() >= self._deadline
        ):
            self._remaining_seconds = 0.0
            self._state = TimerState.COMPLETED
