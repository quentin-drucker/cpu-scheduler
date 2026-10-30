"""Checks scheduling through the same menu functions used at the keyboard."""

import io
import os
from contextlib import redirect_stdout
from pathlib import Path
import unittest
from unittest.mock import patch

import cli_style as ui
from main import (main, run_scheduler_from_input, edit_pcb_from_input,
                  add_pcb_from_input, remove_pcb_from_input, load_pcbs_from_input)
from pcb_manager import PCBManager


ROOT = Path(__file__).resolve().parents[1]
QUANTUM_PROMPT = "Time quantum in cycles (Enter for 3 from the data file, C to cancel): "
QUANTUM_ERROR = "Error: Quantum must be a whole number greater than 0."


class SchedulingMenuTests(unittest.TestCase):
    def setUp(self):
        self.manager = PCBManager()
        self.manager.load_from_file(ROOT / "data/phase3_official.txt")

    def run_prompt(self, function, answers):
        # Reuse real menu code with supplied keyboard answers. Results still
        # come from the real scheduler; only input and terminal width are fixed.
        with patch("builtins.input", side_effect=answers) as read:
            with patch("cli_style.shutil.get_terminal_size",
                       return_value=os.terminal_size((100, 30))):
                with redirect_stdout(io.StringIO()) as output:
                    function(self.manager)
        # The patched input never prints its prompt, so keep the prompts it received.
        self.prompts = [call.args[0] for call in read.call_args_list]
        return output.getvalue()

    def turnarounds(self, output):
        # The results table's Turnaround row lists one value per process,
        # in collection order. Reading it checks what the UI actually showed.
        line = next(line for line in output.splitlines() if line.startswith("Turnaround"))
        return [int(word) for word in line.split()[1:]]

    def test_three_choices_show_timeline_average_and_switches(self):
        for answers, name, short, average, switches, first_line in [
            (["1"], "FCFS Schedule", "FCFS", "20.17", 6,
             "0 CS 1 P0 9 CS 10 P1 18 CS 19 P2 20 CS 21 P3 24 CS 25 P4 29 CS 30 P5 34"),
            (["2"], "SJF Schedule", "SJF", "16.83", 6,
             "0 CS 1 P0 9 CS 10 P2 11 CS 12 P3 15 CS 16 P4 20 CS 21 P5 25 CS 26 P1 34"),
            (["3", ""], "Round-Robin Schedule", "Round-Robin", "25.67", 12,
             "0 CS 1 P0 4 CS 5 P1 8 CS 9 P2 10 CS 11 P3 14 CS 15 P4 18 CS 19 P5 22"),
        ]:
            with self.subTest(algorithm=name):
                output = self.run_prompt(run_scheduler_from_input, answers)
                lines = output.splitlines()
                for text in ["1. First-Come, First-Served (FCFS)",
                             "2. Shortest-Job-First (SJF)", "3. Round-Robin (RR)", "C. Cancel"]:
                    self.assertIn(text, lines)
                self.assertEqual(self.prompts[0], "Choose an algorithm (1, 2, 3, or C): ")
                # The explanation, timeline and totals appear in this order.
                expected = [
                    name,
                    "Context-switch penalty: 1 cycle(s) before each process starts or resumes.",
                    "Timeline in CPU clock cycles (CS = context-switch penalty):",
                    first_line,
                    f"Average Turnaround Time: {average} cycles",
                    f"Context switches: {switches} ({switches} x 1 = {switches} "
                    "penalty cycles, including the first start)",
                    f"{short} completed for 6 processes. Average turnaround: "
                    f"{average} cycles. Context switches: {switches}.",
                ]
                positions = [lines.index(text) for text in expected]
                self.assertEqual(positions, sorted(positions))
                if short == "Round-Robin":
                    self.assertEqual(self.prompts[1], QUANTUM_PROMPT)
                    self.assertEqual(lines.index("Time quantum: 3 cycles."), positions[1] + 1)
                else:
                    self.assertNotIn("Time quantum: 3 cycles.", lines)
                self.assertNotIn("context-switch penalties are ignored", output)
                self.assertNotIn("\033", output)

    def test_quantum_override_and_validation(self):
        output = self.run_prompt(run_scheduler_from_input,
                                 ["3", "0", "-2", "abc", "2.5", " 2 "])
        self.assertEqual(output.count(QUANTUM_ERROR), 4)
        self.assertIn("Time quantum: 2 cycles.", output)
        self.assertIn("Average Turnaround Time: 27.50 cycles", output)
        # The override is for this run only; the saved records keep 3.
        self.assertEqual([pcb.quantum for pcb in self.manager.get_pcbs()], [3] * 6)

    def test_cancel_at_algorithm_or_quantum_preserves_records(self):
        before = [vars(pcb).copy() for pcb in self.manager.get_pcbs()]
        output = self.run_prompt(run_scheduler_from_input, ["", "9", "cat", " c "])
        self.assertEqual(output.count("Error: Choose 1, 2, 3, or C."), 3)
        self.assertEqual(ui.last_result, "Scheduling cancelled.")
        self.assertNotIn("Average Turnaround", output)
        output = self.run_prompt(run_scheduler_from_input, ["3", "c"])
        self.assertEqual(ui.last_result, "Scheduling cancelled.")
        self.assertNotIn("Average Turnaround", output)
        self.assertEqual([vars(pcb) for pcb in self.manager.get_pcbs()], before)
        output = self.run_prompt(run_scheduler_from_input, ["wrong", " 2 "])
        self.assertIn("SJF completed", output)

    def test_empty_does_not_ask_for_algorithm_or_show_average(self):
        self.manager = PCBManager()
        output = self.run_prompt(run_scheduler_from_input, [])
        self.assertIn("Load a file or add a PCB first", output)
        self.assertNotIn("Average", output)
        self.assertNotIn("completed", ui.last_result)

    def test_edit_cpu_and_arrival_affects_next_run(self):
        # Process 0 now needs 1 cycle: penalty 0-1, run 1-2, turnaround 2.
        self.run_prompt(edit_pcb_from_input, ["0", "4", "1"])
        output = self.run_prompt(run_scheduler_from_input, ["1"])
        self.assertEqual(self.turnarounds(output)[0], 2)
        # Arriving at 20, process 0 is the shortest job ready when P4 ends at 21.
        self.run_prompt(edit_pcb_from_input, ["0", "3", "20"])
        output = self.run_prompt(run_scheduler_from_input, ["2"])
        self.assertEqual(self.turnarounds(output), [3, 9, 10, 13, 18, 24])

    def test_add_remove_and_load_affect_next_run(self):
        self.run_prompt(add_pcb_from_input, ["99", "1000", "0", "1", "3", "1"])
        output = self.run_prompt(run_scheduler_from_input, ["2"])
        self.assertIn("0 CS 1 P99 2 CS", output)
        self.run_prompt(remove_pcb_from_input, ["99", "Y"])
        output = self.run_prompt(run_scheduler_from_input, ["2"])
        self.assertIn("0 CS 1 P0 9 CS 10 P2 11 CS 12 P3 15 CS 16 P4 20 CS 21 P5 25 CS 26 P1 34",
                      output.splitlines())
        self.run_prompt(load_pcbs_from_input, ["M", str(ROOT / "data/phase2_idle.txt")])
        output = self.run_prompt(run_scheduler_from_input, ["1"])
        self.assertIn("0 idle 5 CS 6 P1 8 idle 12 CS 13 P2 14", output.splitlines())
        self.assertEqual(self.turnarounds(output), [3, 2])

    def test_full_menu_runs_both_then_views_unchanged_data(self):
        answers = ["1", "M", str(ROOT / "data/phase2_official.txt"),
                   "8", "1", "8", "2", "8", "3", "", "2", "7"]
        with patch("builtins.input", side_effect=answers):
            with redirect_stdout(io.StringIO()) as output:
                main()
        text = output.getvalue()
        self.assertIn("Average Turnaround Time: 7.40 cycles", text)
        self.assertIn("Average Turnaround Time: 7.20 cycles", text)
        self.assertIn("Round-Robin completed for 5 processes. Average turnaround: 7.40 cycles.",
                      text)
        self.assertIn("Total PCBs: 5", text)
        self.assertIn("Exiting Process Manager", text)
        self.assertNotIn("Error:", text)

    def test_interactive_pause_once_and_cancel_replaces_success(self):
        # The extra empty strings acknowledge each normal main-menu pause.
        # Too many pauses would consume an algorithm/menu answer and fail.
        answers = ["1", "M", str(ROOT / "data/phase2_official.txt"), "",
                   "8", "1", "", "8", "C", "", "7"]
        with patch.object(ui, "interactive", return_value=True):
            with patch.object(ui, "terminal_effects", return_value=False):
                with patch("builtins.input", side_effect=answers) as read:
                    with redirect_stdout(io.StringIO()) as output:
                        main()
        self.assertEqual(read.call_count, len(answers))
        text = output.getvalue()
        self.assertIn("Previous action: Schedule: FCFS completed", text)
        self.assertIn("Previous action: Schedule: Scheduling cancelled.", text)
        final_menu = text.rsplit("Previous action:", 1)[1]
        self.assertNotIn("completed", final_menu)


if __name__ == "__main__":
    unittest.main()
