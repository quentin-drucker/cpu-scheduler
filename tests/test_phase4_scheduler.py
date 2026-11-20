"""Checks the scheduler and memory allocation running together (Phase 4).

Expected values are worked out by hand from the assignment data, not copied
from program output.
"""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from pcb import PCB
from pcb_manager import PCBManager
from memory_manager import FIRST_FIT, WORST_FIT, MEMORY_SIZE
from scheduler import schedule_fcfs, schedule_sjf, schedule_rr, average_turnaround


ROOT = Path(__file__).resolve().parents[1]
RUNS = [("FCFS", lambda p, fit: schedule_fcfs(p, fit)),
        ("SJF", lambda p, fit: schedule_sjf(p, fit)),
        ("RR", lambda p, fit: schedule_rr(p, 3, fit))]


def load(name):
    manager = PCBManager()
    manager.load_from_file(ROOT / "data" / name)
    return manager.get_pcbs()


def runs(schedule):
    # (id, start, finish, memory start) for each slice, in run order.
    return [(s["process_id"], s["start_time"], s["finish_time"], s["memory_start"])
            for s in schedule["slices"]]


def turnarounds(schedule):
    return [row["turnaround_time"] for row in schedule["processes"]]


class Phase4SchedulerTests(unittest.TestCase):
    def assert_memory_valid(self, schedule, pcbs):
        """Replays the memory events: no overlaps, no needless compaction."""
        held = {}
        sizes = {pcb.process_id: pcb.memory for pcb in pcbs}
        allocated, released = [], []
        for event in schedule["events"]:
            if event["kind"] == "allocate":
                self.assertNotIn(event["process_id"], held)
                self.assertEqual(event["size"], sizes[event["process_id"]])
                held[event["process_id"]] = event["start"]
                allocated.append(event["process_id"])
            elif event["kind"] == "release":
                del held[event["process_id"]]
                released.append(event["process_id"])
            elif event["kind"] == "compact":
                # Compaction happens only when the free total fits but no hole does.
                self.assertGreaterEqual(event["free"], event["size"])
                self.assertLess(event["largest"], event["size"])
                for move in event["moves"]:
                    self.assertEqual(held[move["process_id"]], move["from"])
                    held[move["process_id"]] = move["to"]
            ranges = sorted((start, start + sizes[pid]) for pid, start in held.items())
            for (_, end), (next_start, _) in zip(ranges, ranges[1:]):
                self.assertLessEqual(end, next_start)
            if ranges:
                self.assertGreaterEqual(ranges[0][0], 0)
                self.assertLessEqual(ranges[-1][1], MEMORY_SIZE)
        # Every process gets memory once and gives it back once.
        self.assertEqual(sorted(allocated), sorted(sizes))
        self.assertEqual(sorted(released), sorted(sizes))
        for piece in schedule["slices"]:
            self.assertEqual(piece["memory_size"], sizes[piece["process_id"]])

    def test_data_set_1_fcfs_compacts_at_cycle_11_with_both_fits(self):
        # P3 (12000) cannot fit at cycle 2 (9000 free) and waits; P4 (500)
        # fits and is placed at 6000 meanwhile. When P2 ends at 11 the holes
        # are 6000 and 8500: 14500 free but neither fits, so compact.
        pcbs = load("phase4_set1.txt")
        for fit in [FIRST_FIT, WORST_FIT]:
            with self.subTest(fit=fit):
                schedule = schedule_fcfs(pcbs, fit)
                # P3 keeps its ready-queue place, so it runs before P4.
                self.assertEqual(runs(schedule), [(1, 1, 5, 0), (2, 6, 11, 2000),
                                                  (3, 12, 14, 500), (4, 15, 21, 0)])
                self.assertEqual(turnarounds(schedule), [5, 10, 12, 18])
                self.assertAlmostEqual(average_turnaround(schedule["processes"]), 11.25)
                self.assertEqual(schedule["context_switches"], 4)
                [compaction] = schedule["compactions"]
                self.assertEqual((compaction["time"], compaction["process_id"],
                                  compaction["free"], compaction["largest"]),
                                 (11, 3, 14500, 8500))
                self.assertEqual(compaction["moves"],
                                 [{"process_id": 4, "from": 6000, "to": 0}])
                self.assertEqual(compaction["layout"], {
                    "blocks": [{"process_id": 4, "start": 0, "size": 500},
                               {"process_id": 3, "start": 500, "size": 12000}],
                    "holes": [{"start": 12500, "size": 2500}]})
                self.assertEqual([row["memory_starts"] for row in schedule["processes"]],
                                 [[0], [2000], [500], [6000, 0]])
                # The smaller P4 got memory while the larger P3 was waiting.
                kinds = [(e["kind"], e["process_id"]) for e in schedule["events"]]
                self.assertLess(kinds.index(("wait", 3)), kinds.index(("allocate", 4)))
                self.assert_memory_valid(schedule, pcbs)

    def test_data_set_1_round_robin_compacts_at_cycle_17(self):
        pcbs = load("phase4_set1.txt")
        schedule = schedule_rr(pcbs, 3, FIRST_FIT)
        # P3 is skipped while it waits; P2 and P4 run around it.
        self.assertEqual(runs(schedule), [
            (1, 1, 4, 0), (2, 5, 8, 2000), (4, 9, 12, 6000), (1, 13, 14, 0),
            (2, 15, 17, 2000), (3, 18, 20, 500), (4, 21, 24, 0)])
        self.assertEqual(turnarounds(schedule), [14, 16, 18, 21])
        self.assertAlmostEqual(average_turnaround(schedule["processes"]), 17.25)
        self.assertEqual(schedule["context_switches"], 7)
        self.assertEqual([c["time"] for c in schedule["compactions"]], [17])
        self.assert_memory_valid(schedule, pcbs)

    def test_merging_three_holes_avoids_compaction_for_first_fit_only(self):
        # Phase 2 official data. At cycle 3 P3 and P4 (500 each) arrive.
        # First-Fit puts them in the old P0 hole at 0 and 500; Worst-Fit puts
        # them at 6000 and 6500. When P1 (2000-5999) ends at 6:
        #  First-Fit: holes 1000-1999, 2000-5999, 6000-14999 merge into one
        #             14000 hole, so P2 (12000) fits at 1000 with no compaction.
        #  Worst-Fit: holes 0-5999 and 7000-14999 (6000 + 8000) need compaction.
        pcbs = load("phase2_official.txt")
        first = schedule_fcfs(pcbs, FIRST_FIT)
        worst = schedule_fcfs(pcbs, WORST_FIT)
        self.assertEqual(first["compactions"], [])
        self.assertEqual([row["memory_starts"] for row in first["processes"]],
                         [[0], [2000], [1000], [0], [500]])
        [compaction] = worst["compactions"]
        self.assertEqual(compaction["time"], 6)
        self.assertEqual(compaction["moves"], [{"process_id": 3, "from": 6000, "to": 0},
                                               {"process_id": 4, "from": 6500, "to": 500}])
        self.assertEqual([row["memory_starts"] for row in worst["processes"]],
                         [[0], [2000], [1000], [6000, 0], [6500, 500]])
        # Memory placement differs, but the CPU order is the same.
        for schedule in [first, worst]:
            self.assertEqual(turnarounds(schedule), [3, 5, 6, 9, 14])
            self.assert_memory_valid(schedule, pcbs)

    def test_data_set_3_fits_place_p7_differently_and_compact_differently(self):
        # At cycle 7 P1 frees 0-1999, then P7 (500) arrives. Holes: 0-1999 and
        # 7500-14999. First-Fit uses 0; Worst-Fit uses 7500. When P2 ends at 12,
        # 13000 is free but no hole fits P3 (12000), so both compact at 12.
        pcbs = load("phase4_set3.txt")
        first = schedule_fcfs(pcbs, FIRST_FIT)
        worst = schedule_fcfs(pcbs, WORST_FIT)
        self.assertEqual([row["memory_starts"] for row in first["processes"]],
                         [[0], [2000], [2000], [6000, 500], [6500, 1000], [7000, 1500], [0]])
        self.assertEqual([row["memory_starts"] for row in worst["processes"]],
                         [[0], [2000], [2000], [6000, 0], [6500, 500], [7000, 1000],
                          [7500, 1500]])
        self.assertEqual([c["time"] for c in first["compactions"]], [12])
        self.assertEqual([len(c["moves"]) for c in first["compactions"]], [3])
        self.assertEqual([len(c["moves"]) for c in worst["compactions"]], [4])
        # FCFS: penalty before each run; P3 waits in the queue but keeps its place.
        self.assertEqual(turnarounds(first), [7, 11, 16, 21, 25, 33, 37])
        self.assertEqual(turnarounds(worst), turnarounds(first))
        for schedule in [first, worst]:
            self.assert_memory_valid(schedule, pcbs)

    def test_first_fit_and_worst_fit_choose_different_holes(self):
        # A (3000) and B (5000) arrive at 0. A ends at 3, leaving holes
        # 0-2999 and 8000-14999. D (1000) arrives at 5 while B runs.
        pcbs = [PCB(1, 3000, 0, 2, 3, 1), PCB(2, 5000, 0, 10, 3, 1),
                PCB(3, 1000, 5, 1, 3, 1)]
        self.assertEqual(runs(schedule_fcfs(pcbs, FIRST_FIT))[-1], (3, 15, 16, 0))
        self.assertEqual(runs(schedule_fcfs(pcbs, WORST_FIT))[-1], (3, 15, 16, 8000))

    def test_sjf_only_picks_among_processes_holding_memory(self):
        # Phase 2 official data: at cycle 3 P2 (CPU 1) is the shortest job, but
        # it has no memory yet, so SJF runs P1 (CPU 2) instead.
        schedule = schedule_sjf(load("phase2_official.txt"), FIRST_FIT)
        self.assertEqual([s["process_id"] for s in schedule["slices"]], [0, 1, 2, 3, 4])
        self.assertAlmostEqual(average_turnaround(schedule["processes"]), 7.4)

    def test_every_algorithm_and_fit_keeps_memory_valid_on_all_data_sets(self):
        for data in ["phase4_set1.txt", "phase4_set2.txt", "phase4_set3.txt",
                     "phase3_official.txt"]:
            pcbs = load(data)
            for name, run in RUNS:
                for fit in [FIRST_FIT, WORST_FIT]:
                    with self.subTest(data=data, algorithm=name, fit=fit):
                        schedule = run(pcbs, fit)
                        self.assert_memory_valid(schedule, pcbs)
                        self.assertEqual(schedule["fit"], fit)

    def test_memory_runs_never_change_the_stored_pcbs(self):
        pcbs = load("phase4_set3.txt")
        before = [vars(pcb).copy() for pcb in pcbs]
        first = schedule_rr(pcbs, 3, WORST_FIT)
        self.assertEqual(schedule_rr(pcbs, 3, WORST_FIT), first)
        self.assertEqual([vars(pcb) for pcb in pcbs], before)

    def test_without_a_fit_runs_match_phase_3(self):
        pcbs = load("phase3_official.txt")
        schedule = schedule_fcfs(pcbs)
        self.assertIsNone(schedule["fit"])
        self.assertEqual(schedule["events"], [])
        self.assertAlmostEqual(average_turnaround(schedule["processes"]), 121 / 6)

    def test_all_processes_fitting_gives_phase_3_results(self):
        # When the total memory fits at once, memory never delays anyone.
        pcbs = [PCB(pid, 1000, arrival, cpu, 3, 1)
                for pid, arrival, cpu in [(0, 0, 8), (1, 1, 8), (2, 2, 1), (3, 3, 3),
                                          (4, 3, 4), (5, 4, 4)]]
        for name, run in RUNS:
            for fit in [FIRST_FIT, WORST_FIT]:
                with self.subTest(algorithm=name, fit=fit):
                    with_memory = run(pcbs, fit)
                    without = run(pcbs, None)
                    self.assertEqual(turnarounds(with_memory), turnarounds(without))
                    self.assertEqual(with_memory["compactions"], [])

    def test_memory_over_15000_is_rejected_when_loading(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "too_big.txt"
            path.write_text("1 2000 0 4 3 1\n2 15001 1 5 3 1\n")
            with self.assertRaisesRegex(ValueError, "Line 2: Memory must be 15000 or less"):
                PCBManager().load_from_file(path)


if __name__ == "__main__":
    unittest.main()
