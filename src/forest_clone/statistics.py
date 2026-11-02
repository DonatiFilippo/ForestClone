"""Productivity statistics derived from completed sessions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Iterable, Mapping, Any

from .forest import live_tree_count


@dataclass(frozen=True)
class Statistics:
    completed_sessions: int
    focused_seconds: int
    trees_planted: int
    today_seconds: int
    streak_days: int


def calculate_statistics(
    sessions: Iterable[Mapping[str, Any]], today: date | None = None
) -> Statistics:
    current_day = today or date.today()
    completed = [row for row in sessions if row["status"] == "completed"]
    focused_seconds = sum(int(row["duration_seconds"]) for row in completed)
    session_days = {
        datetime.fromtimestamp(float(row["started_at"])).date() for row in completed
    }
    today_seconds = sum(
        int(row["duration_seconds"])
        for row in completed
        if datetime.fromtimestamp(float(row["started_at"])).date() == current_day
    )

    streak = 0
    cursor = current_day
    if cursor not in session_days:
        cursor -= timedelta(days=1)
    while cursor in session_days:
        streak += 1
        cursor -= timedelta(days=1)

    count = len(completed)
    trees = sum(live_tree_count(int(row["duration_seconds"])) for row in completed)
    return Statistics(count, focused_seconds, trees, today_seconds, streak)


def format_duration(seconds: int) -> str:
    hours, remainder = divmod(seconds, 3600)
    minutes = remainder // 60
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"
