"""Checks First-Fit, Worst-Fit, hole merging and compaction on their own."""

import unittest

from memory_manager import MemoryManager, FIRST_FIT, WORST_FIT, MEMORY_SIZE


def spans(items):
    return [(item["start"], item["size"]) for item in items]


def fragmented(fit):
    """A 0-2999, B 3000-3999, C 4000-8999, D 9000-9999; then A and C leave.

    Holes: 0-2999 (3000), 4000-8999 (5000), 10000-14999 (5000).
    """
    memory = MemoryManager(fit)
    for pid, size in [("A", 3000), ("B", 1000), ("C", 5000), ("D", 1000)]:
        memory.allocate(pid, size)
    memory.release("A")
    memory.release("C")
    return memory


class MemoryManagerTests(unittest.TestCase):
    def assert_covers_memory(self, memory):
        # Blocks and holes together cover 0-14999 exactly once, and no two
        # holes touch (they would have been merged).
        pieces = sorted(spans(memory.blocks) + spans(memory.holes))
        position = 0
        for start, size in pieces:
            self.assertEqual(start, position)
            self.assertGreater(size, 0)
            position += size
        self.assertEqual(position, memory.size)
        for left, right in zip(memory.holes, memory.holes[1:]):
            self.assertLess(left["start"] + left["size"], right["start"])

    def test_starts_as_one_hole_of_15000(self):
        memory = MemoryManager(FIRST_FIT)
        self.assertEqual(MEMORY_SIZE, 15000)
        self.assertEqual(spans(memory.holes), [(0, 15000)])
        self.assertEqual(memory.blocks, [])

    def test_rejects_unknown_rule_and_unknown_release(self):
        with self.assertRaises(ValueError):
            MemoryManager("Best-Fit")
        with self.assertRaises(ValueError):
            MemoryManager(FIRST_FIT).release(7)

    def test_first_fit_takes_lowest_hole_that_fits(self):
        memory = fragmented(FIRST_FIT)
        self.assertEqual(memory.allocate("E", 2000)["start"], 0)
        # 0-1999 used, so 2000-2999 stays a 1000 hole.
        self.assertEqual(spans(memory.holes), [(2000, 1000), (4000, 5000), (10000, 5000)])
        # 4000 is too big for 2000-2999, so First-Fit moves on to 4000.
        self.assertEqual(memory.allocate("F", 4000)["start"], 4000)
        self.assert_covers_memory(memory)

    def test_worst_fit_takes_largest_hole_lowest_on_tie(self):
        memory = fragmented(WORST_FIT)
        # Two 5000 holes tie; the lower address wins.
        self.assertEqual(memory.allocate("E", 2000)["start"], 4000)
        # Now 10000-14999 (5000) is the largest.
        self.assertEqual(memory.allocate("F", 500)["start"], 10000)
        self.assert_covers_memory(memory)

    def test_exact_fit_removes_the_hole(self):
        memory = MemoryManager(WORST_FIT)
        memory.allocate(1, 15000)
        self.assertEqual(memory.holes, [])
        self.assertIsNone(memory.allocate(2, 1))
        self.assert_covers_memory(memory)

    def test_release_merges_with_holes_on_both_sides(self):
        memory = fragmented(FIRST_FIT)
        memory.release("B")          # between 0-2999 and 4000-8999
        self.assertEqual(spans(memory.holes), [(0, 9000), (10000, 5000)])
        memory.release("D")          # between 0-8999 and 10000-14999
        self.assertEqual(spans(memory.holes), [(0, 15000)])
        self.assert_covers_memory(memory)

    def test_release_merges_one_side_only(self):
        memory = MemoryManager(FIRST_FIT)
        for pid in [1, 2, 3]:
            memory.allocate(pid, 1000)
        memory.release(1)            # nothing on its left
        self.assertEqual(spans(memory.holes), [(0, 1000), (3000, 12000)])
        memory.release(3)            # joins the top hole only
        self.assertEqual(spans(memory.holes), [(0, 1000), (2000, 13000)])
        self.assert_covers_memory(memory)

    def test_compaction_needed_only_when_total_fits_but_no_hole_does(self):
        memory = fragmented(FIRST_FIT)     # holes 3000, 5000, 5000 = 13000 free
        self.assertFalse(memory.needs_compaction(5000))    # a hole fits
        self.assertTrue(memory.needs_compaction(6000))     # only the total fits
        self.assertTrue(memory.needs_compaction(13000))
        self.assertFalse(memory.needs_compaction(13001))   # compaction cannot help

    def test_compaction_slides_blocks_down_in_address_order(self):
        memory = fragmented(FIRST_FIT)
        moves = memory.compact()
        self.assertEqual(moves, [{"process_id": "B", "from": 3000, "to": 0},
                                 {"process_id": "D", "from": 9000, "to": 1000}])
        self.assertEqual(spans(memory.blocks), [(0, 1000), (1000, 1000)])
        self.assertEqual(spans(memory.holes), [(2000, 13000)])
        self.assertEqual(memory.compact(), [])     # already compact: nothing moves
        self.assert_covers_memory(memory)

    def test_layout_is_a_snapshot(self):
        memory = MemoryManager(FIRST_FIT)
        memory.allocate(1, 100)
        snapshot = memory.layout()
        memory.release(1)
        self.assertEqual(snapshot, {"blocks": [{"process_id": 1, "start": 0, "size": 100}],
                                    "holes": [{"start": 100, "size": 14900}]})


if __name__ == "__main__":
    unittest.main()
