"""Checks the Phase 4 menu output: run order, memory locations and compaction."""

import io
import os
from contextlib import redirect_stdout
from pathlib import Path
import unittest
from unittest.mock import patch

import cli_style as ui
from main import run_scheduler_from_input, main
from pcb_manager import PCBManager


ROOT = Path(__file__).resolve().parents[1]


class Phase4MenuTests(unittest.TestCase):
    def run_menu(self, data, answers):
        manager = PCBManager()
        manager.load_from_file(ROOT / "data" / data)
        with patch("builtins.input", side_effect=answers):
            with patch("cli_style.shutil.get_terminal_size",
                       return_value=os.terminal_size((100, 30))):
                with redirect_stdout(io.StringIO()) as output:
                    run_scheduler_from_input(manager)
        return output.getvalue().splitlines()

    def test_data_set_1_shows_run_order_memory_and_compaction(self):
        lines = self.run_menu("phase4_set1.txt", ["1", "1"])
        expected = [
            "Memory: 15000 locations (0-14999), First-Fit; each process gets one "
            "contiguous block of exactly its size.",
            "0 CS 1 P1 5 CS 6 P2 11 CS 12 P3 14 CS 15 P4 21",
            "1    P1       0-1      1      5       4    starts at 0, size 2000",
            "2    P2       5-6      6      11      5    starts at 2000, size 4000",
            "3    P3       11-12    12     14      2    starts at 500, size 12000",
            "4    P4       14-15    15     21      6    starts at 0, size 500",
            "Cycle 2: P3 waits for memory: needs 12000, largest hole 9000, total free 9000.",
            "Cycle 3: P4 allocated at 6000-6499 (starts at 6000, size 500).",
            "Cycle 11: P2 finished and released its memory. "
            "Holes after merging: 0-5999 (6000), 6500-14999 (8500).",
            "Cycle 11: COMPACTION #1 for P3: needs 12000, 14500 free in total but the "
            "largest hole is 8500.",
            "    P4 moved 6000 -> 0",
            "    Memory now: P4 0-499 | P3 500-12499 | free 12500-14999",
            "Turnaround          5       10       12       18",
            "Location            0     2000      500  6000->0",
            "Average Turnaround Time: 11.25 cycles",
            "Compactions: 1 (at cycle 11)",
            "FCFS with First-Fit completed for 4 processes. Average turnaround: 11.25 "
            "cycles. Context switches: 4. Compactions: 1.",
        ]
        positions = [lines.index(text) for text in expected]
        self.assertEqual(positions, sorted(positions))

    def test_worst_fit_reports_compaction_that_first_fit_avoids(self):
        first = self.run_menu("phase2_official.txt", ["1", "1"])
        worst = self.run_menu("phase2_official.txt", ["1", "2"])
        self.assertIn("Compactions: 0", first)
        self.assertFalse(any("COMPACTION" in line for line in first))
        self.assertIn("Compactions: 1 (at cycle 6)", worst)
        self.assertIn("    P3 moved 6000 -> 0", worst)
        self.assertIn("    P4 moved 6500 -> 500", worst)
        self.assertIn("    Memory now: P3 0-499 | P4 500-999 | P2 1000-12999 | "
                      "free 13000-14999", worst)

    def test_round_robin_uses_quantum_then_fit(self):
        lines = self.run_menu("phase4_set1.txt", ["3", "", "2"])
        self.assertIn("Time quantum: 3 cycles.", lines)
        self.assertIn("Compactions: 1 (at cycle 17)", lines)
        self.assertIn("Average Turnaround Time: 17.25 cycles", lines)

    def test_menu_lists_both_fits_and_new_title(self):
        lines = self.run_menu("phase4_set2.txt", ["2", "1"])
        self.assertIn("1. First-Fit (first hole large enough)", lines)
        self.assertIn("2. Worst-Fit (largest hole)", lines)
        with patch("builtins.input", side_effect=["7"]):
            with redirect_stdout(io.StringIO()) as output:
                main()
        self.assertIn("COM326 | PROJECT PHASE 4", output.getvalue())
        self.assertIn("8. Run CPU scheduler with memory allocation", output.getvalue())
        self.assertEqual(ui.PROJECT_TITLE.strip(), "COM326 | PROJECT PHASE 4")


if __name__ == "__main__":
    unittest.main()
