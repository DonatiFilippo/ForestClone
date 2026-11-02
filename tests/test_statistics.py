from datetime import date, datetime
import unittest

from forest_clone.statistics import calculate_statistics


def timestamp(day: date) -> float:
    return datetime(day.year, day.month, day.day, 12).timestamp()


class StatisticsTests(unittest.TestCase):
    def test_totals_today_and_streak(self) -> None:
        today = date(2025, 6, 10)
        rows = [
            {"status": "completed", "duration_seconds": 1500, "started_at": timestamp(today)},
            {"status": "completed", "duration_seconds": 900, "started_at": timestamp(date(2025, 6, 9))},
            {"status": "completed", "duration_seconds": 600, "started_at": timestamp(date(2025, 6, 8))},
            {"status": "interrupted", "duration_seconds": 999, "started_at": timestamp(today)},
        ]
        result = calculate_statistics(rows, today)
        self.assertEqual(result.completed_sessions, 3)
        self.assertEqual(result.focused_seconds, 3000)
        self.assertEqual(result.today_seconds, 1500)
        self.assertEqual(result.trees_planted, 3)
        self.assertEqual(result.streak_days, 3)

    def test_streak_allows_today_not_started(self) -> None:
        today = date(2025, 6, 10)
        rows = [{"status": "completed", "duration_seconds": 60, "started_at": timestamp(date(2025, 6, 9))}]
        self.assertEqual(calculate_statistics(rows, today).streak_days, 1)


if __name__ == "__main__":
    unittest.main()
