"""Checks Phase 3 schedules against small, hand-calculated examples."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from pcb import PCB
from pcb_manager import PCBManager
from scheduler import schedule_fcfs, schedule_sjf, schedule_rr, average_turnaround


ROOT = Path(__file__).resolve().parents[1]
ALGORITHMS = [schedule_fcfs, schedule_sjf, lambda p: schedule_rr(p, 3)]


def processes(rows, quantum=3, penalty=1):
    """Adds the memory/quantum/penalty values to short test records."""
    return [PCB(process_id, 1, arrival, cpu, quantum, penalty)
            for process_id, arrival, cpu in rows]


def slice_tuples(schedule):
    # (id, switch_start, start, finish, CPU left) for each slice, in run order.
    return [(r["process_id"], r["switch_start"], r["start_time"],
             r["finish_time"], r["remaining"]) for r in schedule["slices"]]


def turnarounds(schedule):
    return {r["process_id"]: r["turnaround_time"] for r in schedule["processes"]}


def load(name):
    manager = PCBManager()
    manager.load_from_file(ROOT / "data" / name)
    return manager.get_pcbs()


class SchedulerTests(unittest.TestCase):
    def assert_schedule(self, schedule, pcbs, slices, turnaround, average, switches):
        # Expected values are written by hand, not calculated by the scheduler.
        # slices=None means only the totals were worked out for that case.
        if slices is not None:
            self.assertEqual(slice_tuples(schedule), slices)
        self.assertEqual(turnarounds(schedule), turnaround)
        self.assertAlmostEqual(average_turnaround(schedule["processes"]), average)
        self.assertEqual(schedule["context_switches"], switches)

        # These general checks also make it clear what a valid run means:
        # no overlaps, every penalty is the full length, each job gets exactly
        # its CPU time, and no process starts before it arrives.
        penalty = schedule["penalty"]
        quantum = schedule["quantum"]
        self.assertEqual([r["process_id"] for r in schedule["processes"]],
                         [pcb.process_id for pcb in pcbs])
        self.assertEqual(schedule["context_switches"],
                         sum(1 for r in schedule["slices"] if r["switch_start"] is not None))
        previous_finish = 0
        used = {}
        last_finish = {}
        for r in schedule["slices"]:
            first_moment = r["start_time"] if r["switch_start"] is None else r["switch_start"]
            self.assertGreaterEqual(first_moment, previous_finish)
            if r["switch_start"] is not None:
                self.assertEqual(r["start_time"] - r["switch_start"], penalty)
            pid = r["process_id"]
            if pid not in used:
                arrival = next(p.arrival_time for p in pcbs if p.process_id == pid)
                self.assertGreaterEqual(first_moment, arrival)
            length = r["finish_time"] - r["start_time"]
            if quantum is not None:
                self.assertLessEqual(length, quantum)
            used[pid] = used.get(pid, 0) + length
            last_finish[pid] = r["finish_time"]
            previous_finish = r["finish_time"]
        for pcb in pcbs:
            self.assertEqual(used[pcb.process_id], pcb.cpu_required)
        for r in schedule["processes"]:
            self.assertEqual(r["completion_time"], last_finish[r["process_id"]])
            self.assertEqual(r["turnaround_time"], r["completion_time"] - r["arrival_time"])

    def test_official_file_matches_revised_handout(self):
        expected = "0 2000 0 2 3 1\n1 4000 1 2 3 1\n2 12000 2 1 3 1\n3 500 3 3 3 1\n4 500 3 4 3 1\n"
        self.assertEqual((ROOT / "data/phase2_official.txt").read_text(), expected)
        handout = (ROOT / "Assignment Specifications" / "Assignment Specifications for Phase 2" /
                   "From moodle - Project Phase 2 Official Test Data File.txt")
        # The handout folder is gitignored, so a fresh clone may not have it.
        if handout.exists():
            self.assertIn(expected.strip(), handout.read_text())
        self.assertEqual(len(load("phase2_official.txt")), 5)

    def test_official_phase3_rr_quantum_3(self):
        pcbs = load("phase3_official.txt")
        self.assert_schedule(schedule_rr(pcbs, 3), pcbs, [
            (0, 0, 1, 4, 5), (1, 4, 5, 8, 5), (2, 8, 9, 10, 0), (3, 10, 11, 14, 0),
            (4, 14, 15, 18, 1), (5, 18, 19, 22, 1), (0, 22, 23, 26, 2), (1, 26, 27, 30, 2),
            (4, 30, 31, 32, 0), (5, 32, 33, 34, 0), (0, 34, 35, 37, 0), (1, 37, 38, 40, 0)
        ], {0: 37, 1: 39, 2: 8, 3: 11, 4: 29, 5: 30}, 154 / 6, 12)

    def test_official_phase3_rr_quantum_2(self):
        pcbs = load("phase3_official.txt")
        self.assert_schedule(schedule_rr(pcbs, 2), pcbs, None,
                             {0: 40, 1: 42, 2: 6, 3: 22, 4: 25, 5: 30}, 27.5, 15)

    def test_official_phase3_rr_quantum_1(self):
        pcbs = load("phase3_official.txt")
        self.assert_schedule(schedule_rr(pcbs, 1), pcbs, None,
                             {0: 54, 1: 55, 2: 4, 3: 27, 4: 37, 5: 38}, 215 / 6, 28)

    def test_official_phase3_fcfs(self):
        pcbs = load("phase3_official.txt")
        self.assert_schedule(schedule_fcfs(pcbs), pcbs, [
            (0, 0, 1, 9, 0), (1, 9, 10, 18, 0), (2, 18, 19, 20, 0),
            (3, 20, 21, 24, 0), (4, 24, 25, 29, 0), (5, 29, 30, 34, 0)
        ], {0: 9, 1: 17, 2: 18, 3: 21, 4: 26, 5: 30}, 121 / 6, 6)

    def test_official_phase3_sjf(self):
        pcbs = load("phase3_official.txt")
        self.assert_schedule(schedule_sjf(pcbs), pcbs, [
            (0, 0, 1, 9, 0), (2, 9, 10, 11, 0), (3, 11, 12, 15, 0),
            (4, 15, 16, 20, 0), (5, 20, 21, 25, 0), (1, 25, 26, 34, 0)
        ], {0: 9, 1: 33, 2: 9, 3: 12, 4: 17, 5: 21}, 101 / 6, 6)

    def test_arrival_at_quantum_expiry_queues_before_requeued_process(self):
        # P5 arrives while P0's first quantum runs. Our documented choice puts
        # new arrivals ahead of a process whose quantum just expired.
        starts = [(r["process_id"], r["start_time"])
                  for r in schedule_rr(load("phase3_official.txt"), 3)["slices"]]
        self.assertLess(starts.index((5, 19)), starts.index((0, 23)))

    def test_phase2_official_fcfs_with_penalty(self):
        pcbs = load("phase2_official.txt")
        self.assert_schedule(schedule_fcfs(pcbs), pcbs, [
            (0, 0, 1, 3, 0), (1, 3, 4, 6, 0), (2, 6, 7, 8, 0),
            (3, 8, 9, 12, 0), (4, 12, 13, 17, 0)
        ], {0: 3, 1: 5, 2: 6, 3: 9, 4: 14}, 7.4, 5)

    def test_phase2_official_sjf_with_penalty(self):
        # At clock 3, process 2 is ready and shorter than process 1.
        pcbs = load("phase2_official.txt")
        self.assert_schedule(schedule_sjf(pcbs), pcbs, [
            (0, 0, 1, 3, 0), (2, 3, 4, 5, 0), (1, 5, 6, 8, 0),
            (3, 8, 9, 12, 0), (4, 12, 13, 17, 0)
        ], {0: 3, 1: 7, 2: 3, 3: 9, 4: 14}, 7.2, 5)

    def test_same_process_continuing_pays_no_new_penalty(self):
        pcbs = processes([(1, 0, 7)])
        self.assert_schedule(schedule_rr(pcbs, 3), pcbs,
                             [(1, 0, 1, 4, 4), (1, None, 4, 7, 1), (1, None, 7, 8, 0)],
                             {1: 8}, 8, 1)

    def test_rr_lone_survivor_continues_without_penalty(self):
        pcbs = load("phase2_nonpreemptive.txt")
        self.assert_schedule(schedule_rr(pcbs, 3), pcbs, [
            (10, 0, 1, 4, 5), (20, 4, 5, 7, 0), (30, 7, 8, 9, 0),
            (10, 9, 10, 13, 2), (10, None, 13, 15, 0)
        ], {10: 15, 20: 6, 30: 7}, 28 / 3, 4)

    def test_initial_and_middle_idle_gaps(self):
        pcbs = load("phase2_idle.txt")
        for algorithm in ALGORITHMS:
            self.assert_schedule(algorithm(pcbs), pcbs,
                                 [(1, 5, 6, 8, 0), (2, 12, 13, 14, 0)],
                                 {1: 3, 2: 2}, 2.5, 2)

    def test_later_short_jobs_do_not_interrupt(self):
        pcbs = load("phase2_nonpreemptive.txt")
        self.assert_schedule(schedule_sjf(pcbs), pcbs,
                             [(10, 0, 1, 9, 0), (30, 9, 10, 11, 0), (20, 11, 12, 14, 0)],
                             {10: 9, 20: 13, 30: 9}, 31 / 3, 3)
        self.assert_schedule(schedule_fcfs(pcbs), pcbs,
                             [(10, 0, 1, 9, 0), (20, 9, 10, 12, 0), (30, 12, 13, 14, 0)],
                             {10: 9, 20: 11, 30: 12}, 32 / 3, 3)

    def test_ties_use_arrival_then_collection_order_not_id(self):
        pcbs = load("phase2_ties.txt")
        for algorithm in [schedule_fcfs, schedule_sjf]:
            self.assert_schedule(algorithm(pcbs), pcbs, [
                (30, 0, 1, 3, 0), (20, 3, 4, 6, 0), (10, 6, 7, 9, 0), (40, 9, 10, 12, 0)
            ], {40: 10, 30: 3, 20: 6, 10: 8}, 6.75, 4)

    def test_unsorted_input_and_gap(self):
        pcbs = processes([(30, 4, 1), (10, 0, 2), (20, 1, 1)])
        for algorithm in [schedule_fcfs, schedule_sjf]:
            self.assert_schedule(algorithm(pcbs), pcbs,
                                 [(10, 0, 1, 3, 0), (20, 3, 4, 5, 0), (30, 5, 6, 7, 0)],
                                 {30: 3, 10: 3, 20: 4}, 10 / 3, 3)

    def test_all_arrive_together(self):
        pcbs = processes([(1, 0, 4), (2, 0, 1), (3, 0, 2)])
        self.assert_schedule(schedule_fcfs(pcbs), pcbs,
                             [(1, 0, 1, 5, 0), (2, 5, 6, 7, 0), (3, 7, 8, 10, 0)],
                             {1: 5, 2: 7, 3: 10}, 22 / 3, 3)
        self.assert_schedule(schedule_sjf(pcbs), pcbs,
                             [(2, 0, 1, 2, 0), (3, 2, 3, 5, 0), (1, 5, 6, 10, 0)],
                             {1: 10, 2: 2, 3: 5}, 17 / 3, 3)
        self.assert_schedule(schedule_rr(pcbs, 3), pcbs,
                             [(1, 0, 1, 4, 1), (2, 4, 5, 6, 0), (3, 6, 7, 9, 0), (1, 9, 10, 11, 0)],
                             {1: 11, 2: 6, 3: 9}, 26 / 3, 4)

    def test_sjf_choice_is_made_before_the_penalty(self):
        # P3 arrives at 5, during P2's penalty, so it waits for the next choice.
        pcbs = processes([(1, 0, 2), (2, 4, 3), (3, 5, 1)], penalty=2)
        self.assert_schedule(schedule_sjf(pcbs), pcbs,
                             [(1, 0, 2, 4, 0), (2, 4, 6, 9, 0), (3, 9, 11, 12, 0)],
                             {1: 4, 2: 5, 3: 7}, 16 / 3, 3)

    def test_large_idle_jump(self):
        pcbs = processes([(1, 1000000000, 1)])
        for algorithm in ALGORITHMS:
            self.assert_schedule(algorithm(pcbs), pcbs,
                                 [(1, 1000000000, 1000000001, 1000000002, 0)],
                                 {1: 2}, 2, 1)

    def test_rr_with_large_quantum_matches_fcfs(self):
        for pcbs in [load("phase3_official.txt"), processes([(1, 0, 4), (2, 0, 1), (3, 0, 2)])]:
            rr, fcfs = schedule_rr(pcbs, 100), schedule_fcfs(pcbs)
            for key in ["slices", "processes", "context_switches"]:
                self.assertEqual(rr[key], fcfs[key])

    def test_rr_rejects_invalid_quantum(self):
        for quantum in [0, -1, "3", 2.5]:
            with self.subTest(quantum=quantum):
                with self.assertRaises(ValueError):
                    schedule_rr(processes([(1, 0, 2)]), quantum)

    def test_empty_has_no_average(self):
        for algorithm in ALGORITHMS:
            schedule = algorithm([])
            self.assertEqual(schedule["slices"], [])
            self.assertEqual(schedule["processes"], [])
            self.assertEqual(schedule["context_switches"], 0)
        self.assertIsNone(average_turnaround([]))

    def test_runs_preserve_objects_order_fields_and_results(self):
        pcbs = load("phase3_official.txt")
        original_objects = list(pcbs)
        original_values = [vars(pcb).copy() for pcb in pcbs]
        first = schedule_fcfs(pcbs)
        for algorithm in ALGORITHMS:
            self.assertEqual(algorithm(pcbs), algorithm(pcbs))
        self.assertEqual(first, schedule_fcfs(pcbs))
        for current, original in zip(pcbs, original_objects):
            self.assertIs(current, original)
        self.assertEqual([vars(pcb) for pcb in pcbs], original_values)
        for pcb in pcbs:
            self.assertEqual(pcb.remaining_time, pcb.cpu_required)
        # A result is a snapshot of integers, not a reference to mutable PCB data.
        pcbs[0].cpu_required = 99
        self.assertEqual(first["processes"][0]["cpu_required"], 8)

    def test_memory_and_quantum_do_not_change_fcfs_sjf_but_penalty_does(self):
        original = processes([(1, 0, 8), (2, 1, 2)])
        # Values still pass Phase 1 validation, including matching shared fields.
        manager = PCBManager()
        manager.add_pcb(PCB(1, 30000, 0, 8, 1, 1))
        manager.add_pcb(PCB(2, 30000, 1, 2, 1, 1))
        slow = processes([(1, 0, 8), (2, 1, 2)], penalty=5)
        for algorithm in [schedule_fcfs, schedule_sjf]:
            self.assertEqual(algorithm(original), algorithm(manager.get_pcbs()))
            before = algorithm(original)["processes"]
            after = algorithm(slow)["processes"]
            for a, b in zip(before, after):
                self.assertNotEqual(a["completion_time"], b["completion_time"])

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
