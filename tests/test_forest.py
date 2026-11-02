import unittest

from forest_clone.forest import live_tree_count, trees_for_session


class ForestRulesTests(unittest.TestCase):
    def test_completed_hours_plant_multiple_trees(self) -> None:
        self.assertEqual(live_tree_count(25 * 60), 1)
        self.assertEqual(live_tree_count(60 * 60), 1)
        self.assertEqual(live_tree_count(90 * 60), 2)
        self.assertEqual(live_tree_count(119 * 60), 2)
        self.assertEqual(live_tree_count(2 * 3600), 2)
        self.assertEqual(live_tree_count(4 * 3600), 4)

    def test_ninety_minutes_plants_grown_tree_and_sapling(self) -> None:
        trees = trees_for_session(
            {
                "id": 5,
                "status": "completed",
                "duration_seconds": 90 * 60,
                "remaining_seconds": 0,
                "tree_type": "peach",
            }
        )
        self.assertEqual(len(trees), 2)
        self.assertFalse(trees[0].sapling)
        self.assertTrue(trees[1].sapling)
        self.assertLess(trees[1].scale, trees[0].scale)

    def test_short_session_is_sapling(self) -> None:
        trees = trees_for_session(
            {
                "id": 1,
                "status": "completed",
                "duration_seconds": 25 * 60,
                "remaining_seconds": 0,
                "tree_type": "peach",
            }
        )
        self.assertEqual(len(trees), 1)
        self.assertTrue(trees[0].sapling)
        self.assertEqual(trees[0].species, "peach")

    def test_thirty_minutes_is_mature(self) -> None:
        tree = trees_for_session(
            {
                "id": 2,
                "status": "completed",
                "duration_seconds": 30 * 60,
                "remaining_seconds": 0,
                "tree_type": "pine",
            }
        )[0]
        self.assertFalse(tree.sapling)
        self.assertEqual(tree.species, "pine")

    def test_interrupted_session_plants_one_dead_tree_using_elapsed_time(self) -> None:
        trees = trees_for_session(
            {
                "id": 3,
                "status": "interrupted",
                "duration_seconds": 4 * 3600,
                "remaining_seconds": 3.5 * 3600,
                "tree_type": "pine",
            }
        )
        self.assertEqual(len(trees), 1)
        self.assertTrue(trees[0].dead)
        self.assertFalse(trees[0].sapling)

    def test_active_session_does_not_appear_in_forest(self) -> None:
        trees = trees_for_session(
            {
                "id": 4,
                "status": "paused",
                "duration_seconds": 3600,
                "remaining_seconds": 1800,
                "tree_type": "peach",
            }
        )
        self.assertEqual(trees, [])


if __name__ == "__main__":
    unittest.main()
