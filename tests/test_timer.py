import unittest

from forest_clone.timer import FocusTimer, TimerState


class Clock:
    def __init__(self, value: float = 1_000.0) -> None:
        self.value = value

    def __call__(self) -> float:
        return self.value


class FocusTimerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = Clock()
        self.timer = FocusTimer(self.clock)

    def test_uses_deadline_not_tick_count(self) -> None:
        self.timer.start(60)
        self.clock.value += 17.25
        self.assertAlmostEqual(self.timer.remaining_seconds, 42.75)
        self.assertAlmostEqual(self.timer.progress, 17.25 / 60)

    def test_pause_and_resume(self) -> None:
        self.timer.start(60)
        self.clock.value += 10
        self.timer.pause()
        self.clock.value += 100
        self.assertEqual(self.timer.remaining_seconds, 50)
        self.timer.resume()
        self.clock.value += 20
        self.assertEqual(self.timer.remaining_seconds, 30)

    def test_completion(self) -> None:
        self.timer.start(5)
        self.clock.value += 8
        self.assertEqual(self.timer.state, TimerState.COMPLETED)
        self.assertEqual(self.timer.remaining_seconds, 0)

    def test_rejects_invalid_transitions(self) -> None:
        with self.assertRaises(RuntimeError):
            self.timer.pause()
        with self.assertRaises(ValueError):
            self.timer.start(0)


if __name__ == "__main__":
    unittest.main()
