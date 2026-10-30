"""Checks Phase 2 schedules against small, hand-calculated examples."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from pcb import PCB
from pcb_manager import PCBManager
from scheduler import schedule_fcfs, schedule_sjf, average_turnaround


ROOT = Path(__file__).resolve().parents[1]
FIELDS = ["process_id", "arrival_time", "cpu_required", "start_time",
          "finish_time", "turnaround_time"]
ALGORITHMS = [schedule_fcfs, schedule_sjf]


def processes(rows):
    """Adds the unused memory/quantum/penalty values to short test records."""
    return [PCB(process_id, 1, arrival, cpu, 3, 1)
            for process_id, arrival, cpu in rows]


class SchedulerTests(unittest.TestCase):
    def assert_schedule(self, algorithm, pcbs, expected, average):
        # Expected tuples are written by hand, not calculated by the scheduler.
        # Their fields follow FIELDS above, including arrival and CPU required.
        results = algorithm(pcbs)
        self.assertEqual([tuple(row[field] for field in FIELDS) for row in results],
                         expected)
        self.assertAlmostEqual(average_turnaround(results), average)

        # These general checks also make it clear what a valid run means:
        # every job finishes once, with no overlaps and no early starts.
        self.assertCountEqual([row["process_id"] for row in results],
                              [pcb.process_id for pcb in pcbs])
        previous_finish = 0
        for row in results:
            self.assertGreaterEqual(row["start_time"], row["arrival_time"])
            self.assertGreaterEqual(row["start_time"], previous_finish)
            self.assertEqual(row["finish_time"] - row["start_time"], row["cpu_required"])
            self.assertEqual(row["finish_time"] - row["arrival_time"], row["turnaround_time"])
            previous_finish = row["finish_time"]

    def official_pcbs(self):
        manager = PCBManager()
        manager.load_from_file(ROOT / "data/phase2_official.txt")
        return manager.get_pcbs()

    def test_official_file_matches_revised_handout(self):
        expected = "0 2000 0 2 3 1\n1 4000 1 2 3 1\n2 12000 2 1 3 1\n3 500 3 3 3 1\n4 500 3 4 3 1\n"
        self.assertEqual((ROOT / "data/phase2_official.txt").read_text(), expected)
        handout = (ROOT / "Assignment Specifications for Phase 2" /
                   "From moodle - Project Phase 2 Official Test Data File.txt")
        # The handout folder is gitignored, so a fresh clone may not have it.
        if handout.exists():
            self.assertIn(expected.strip(), handout.read_text())
        self.assertEqual(len(self.official_pcbs()), 5)

    def test_official_fcfs(self):
        self.assert_schedule(schedule_fcfs, self.official_pcbs(), [
            (0, 0, 2, 0, 2, 2), (1, 1, 2, 2, 4, 3), (2, 2, 1, 4, 5, 3),
            (3, 3, 3, 5, 8, 5), (4, 3, 4, 8, 12, 9)
        ], 4.4)

    def test_official_sjf_includes_arrival_at_completion(self):
        # At clock 2, process 2 is ready immediately and is shorter than 1.
        self.assert_schedule(schedule_sjf, self.official_pcbs(), [
            (0, 0, 2, 0, 2, 2), (2, 2, 1, 2, 3, 1), (1, 1, 2, 3, 5, 4),
            (3, 3, 3, 5, 8, 5), (4, 3, 4, 8, 12, 9)
        ], 4.2)

    def test_empty_has_no_average(self):
        for algorithm in ALGORITHMS:
            self.assertEqual(algorithm([]), [])
        self.assertIsNone(average_turnaround([]))

    def test_one_late_arrival(self):
        for algorithm in ALGORITHMS:
            self.assert_schedule(algorithm, processes([(9, 5, 3)]),
                                 [(9, 5, 3, 5, 8, 3)], 3)

    def test_initial_and_middle_idle_gaps(self):
        manager = PCBManager()
        manager.load_from_file(ROOT / "data/phase2_idle.txt")
        for algorithm in ALGORITHMS:
            self.assert_schedule(algorithm, manager.get_pcbs(),
                                 [(1, 5, 2, 5, 7, 2), (2, 12, 1, 12, 13, 1)], 1.5)

    def test_unsorted_input_and_gap(self):
        for algorithm in ALGORITHMS:
            self.assert_schedule(algorithm, processes([(30, 4, 1), (10, 0, 2), (20, 1, 1)]),
                                 [(10, 0, 2, 0, 2, 2), (20, 1, 1, 2, 3, 2),
                                  (30, 4, 1, 4, 5, 1)], 5 / 3)

    def test_all_arrive_together(self):
        pcbs = processes([(1, 0, 4), (2, 0, 1), (3, 0, 2)])
        self.assert_schedule(schedule_fcfs, pcbs,
                             [(1, 0, 4, 0, 4, 4), (2, 0, 1, 4, 5, 5),
                              (3, 0, 2, 5, 7, 7)], 16 / 3)
        self.assert_schedule(schedule_sjf, pcbs,
                             [(2, 0, 1, 0, 1, 1), (3, 0, 2, 1, 3, 3),
                              (1, 0, 4, 3, 7, 7)], 11 / 3)

    def test_later_short_jobs_do_not_interrupt(self):
        manager = PCBManager()
        manager.load_from_file(ROOT / "data/phase2_nonpreemptive.txt")
        self.assert_schedule(schedule_sjf, manager.get_pcbs(),
                             [(10, 0, 8, 0, 8, 8), (30, 2, 1, 8, 9, 7),
                              (20, 1, 2, 9, 11, 10)], 25 / 3)
        self.assert_schedule(schedule_fcfs, manager.get_pcbs(),
                             [(10, 0, 8, 0, 8, 8), (20, 1, 2, 8, 10, 9),
                              (30, 2, 1, 10, 11, 9)], 26 / 3)

    def test_ties_use_arrival_then_collection_order_not_id(self):
        manager = PCBManager()
        manager.load_from_file(ROOT / "data/phase2_ties.txt")
        for algorithm in ALGORITHMS:
            self.assert_schedule(algorithm, manager.get_pcbs(), [
                (30, 0, 2, 0, 2, 2), (20, 0, 2, 2, 4, 4),
                (10, 1, 2, 4, 6, 5), (40, 2, 2, 6, 8, 6)
            ], 4.25)

    def test_runs_preserve_objects_order_fields_and_results(self):
        pcbs = self.official_pcbs()
        original_objects = list(pcbs)
        original_values = [vars(pcb).copy() for pcb in pcbs]
        first = schedule_fcfs(pcbs)
        schedule_sjf(pcbs)
        self.assertEqual(first, schedule_fcfs(pcbs))
        for current, original in zip(pcbs, original_objects):
            self.assertIs(current, original)
        self.assertEqual([vars(pcb) for pcb in pcbs], original_values)
        # A result is a snapshot of integers, not a reference to mutable PCB data.
        pcbs[0].cpu_required = 99
        self.assertEqual(first[0]["cpu_required"], 2)

    def test_large_idle_jump(self):
        for algorithm in ALGORITHMS:
            self.assert_schedule(algorithm, processes([(1, 1000000000, 1)]),
                                 [(1, 1000000000, 1, 1000000000, 1000000001, 1)], 1)

    def test_memory_quantum_and_penalty_do_not_change_timing(self):
        original = processes([(1, 0, 8), (2, 1, 2)])
        # Values still pass Phase 1 validation, including matching shared fields.
        manager = PCBManager()
        manager.add_pcb(PCB(1, 30000, 0, 8, 1, 99))
        manager.add_pcb(PCB(2, 30000, 1, 2, 1, 99))
        for algorithm in ALGORITHMS:
            self.assertEqual(algorithm(original), algorithm(manager.get_pcbs()))

    def test_save_reload_after_scheduling_keeps_six_original_fields(self):
        manager = PCBManager()
        source = ROOT / "data/phase2_official.txt"
        manager.load_from_file(source)
        for algorithm in ALGORITHMS:
            algorithm(manager.get_pcbs())
        with TemporaryDirectory() as folder:
            saved = Path(folder) / "after_scheduling.txt"
            manager.save_to_file(saved)
            self.assertEqual(saved.read_text(), source.read_text())
            reloaded = PCBManager()
            reloaded.load_from_file(saved)
            self.assertEqual([vars(p) for p in reloaded.get_pcbs()],
                             [vars(p) for p in manager.get_pcbs()])


if __name__ == "__main__":
    unittest.main()
