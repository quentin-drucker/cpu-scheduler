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


class SchedulingMenuTests(unittest.TestCase):
    def setUp(self):
        self.manager = PCBManager()
        self.manager.load_from_file(ROOT / "data/phase2_official.txt")

    def run_prompt(self, function, answers):
        # Reuse real menu code with supplied keyboard answers. Results still
        # come from the real scheduler; only input and terminal width are fixed.
        with patch("builtins.input", side_effect=answers):
            with patch("cli_style.shutil.get_terminal_size",
                       return_value=os.terminal_size((100, 30))):
                with redirect_stdout(io.StringIO()) as output:
                    function(self.manager)
        return output.getvalue()

    def schedule_rows(self, output):
        # Table rows contain seven integers; headings and explanations do not.
        # Inspecting the output verifies which records the UI actually showed.
        rows = []
        for line in output.splitlines():
            words = line.split()
            if len(words) == 7 and all(word.lstrip('-').isdigit() for word in words):
                rows.append(tuple(map(int, words)))
        return rows

    def test_both_choices_show_exact_order_timing_and_average(self):
        for choice, name, average, rows in [
            ("1", "FCFS", "4.40", [(1,0,0,2,0,2,2), (2,1,1,2,2,4,3),
                                    (3,2,2,1,4,5,3), (4,3,3,3,5,8,5), (5,4,3,4,8,12,9)]),
            ("2", "SJF", "4.20", [(1,0,0,2,0,2,2), (2,2,2,1,2,3,1),
                                   (3,1,1,2,3,5,4), (4,3,3,3,5,8,5), (5,4,3,4,8,12,9)])
        ]:
            with self.subTest(algorithm=name):
                output = self.run_prompt(run_scheduler_from_input, [choice])
                self.assertIn(name + " Schedule", output)
                self.assertIn(f"Average Turnaround Time: {average} cycles", output)
                self.assertIn("context-switch penalties are ignored", output)
                self.assertEqual(self.schedule_rows(output), rows)
                self.assertNotIn("\033", output)

    def test_empty_does_not_ask_for_algorithm_or_show_average(self):
        self.manager = PCBManager()
        output = self.run_prompt(run_scheduler_from_input, [])
        self.assertIn("Load a file or add a PCB first", output)
        self.assertNotIn("Average", output)
        self.assertNotIn("completed", ui.last_result)

    def test_invalid_choice_retries_and_cancel_preserves_records(self):
        before = [vars(pcb).copy() for pcb in self.manager.get_pcbs()]
        output = self.run_prompt(run_scheduler_from_input, ["", "9", "cat", " c "])
        self.assertEqual(output.count("Error: Choose 1, 2, or C."), 3)
        self.assertEqual(ui.last_result, "Scheduling cancelled.")
        self.assertNotIn("Average Turnaround", output)
        self.assertEqual([vars(pcb) for pcb in self.manager.get_pcbs()], before)
        output = self.run_prompt(run_scheduler_from_input, ["wrong", " 2 "])
        self.assertIn("SJF completed", output)

    def test_edit_cpu_and_arrival_affects_next_run(self):
        self.run_prompt(edit_pcb_from_input, ["0", "4", "1"])
        output = self.run_prompt(run_scheduler_from_input, ["1"])
        self.assertEqual(self.schedule_rows(output)[0], (1, 0, 0, 1, 0, 1, 1))
        self.run_prompt(edit_pcb_from_input, ["0", "3", "20"])
        output = self.run_prompt(run_scheduler_from_input, ["2"])
        rows = self.schedule_rows(output)
        self.assertEqual(rows[0][1], 1)
        self.assertEqual(rows[-1], (5, 0, 20, 1, 20, 21, 1))

    def test_add_remove_and_load_affect_next_run(self):
        self.run_prompt(add_pcb_from_input, ["99", "1000", "0", "1", "3", "1"])
        output = self.run_prompt(run_scheduler_from_input, ["2"])
        self.assertEqual(self.schedule_rows(output)[0][1], 99)
        self.run_prompt(remove_pcb_from_input, ["99", "Y"])
        output = self.run_prompt(run_scheduler_from_input, ["2"])
        self.assertEqual([row[1] for row in self.schedule_rows(output)], [0, 2, 1, 3, 4])
        self.run_prompt(load_pcbs_from_input, ["M", str(ROOT / "data/phase2_idle.txt")])
        output = self.run_prompt(run_scheduler_from_input, ["1"])
        self.assertEqual(self.schedule_rows(output),
                         [(1,1,5,2,5,7,2), (2,2,12,1,12,13,1)])

    def test_full_menu_runs_both_then_views_unchanged_data(self):
        answers = ["1", "M", str(ROOT / "data/phase2_official.txt"),
                   "8", "1", "8", "2", "2", "7"]
        with patch("builtins.input", side_effect=answers):
            with redirect_stdout(io.StringIO()) as output:
                main()
        text = output.getvalue()
        self.assertIn("Average Turnaround Time: 4.40 cycles", text)
        self.assertIn("Average Turnaround Time: 4.20 cycles", text)
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
