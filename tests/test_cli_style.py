import io
import os
from contextlib import redirect_stdout
from pathlib import Path
import unittest
from unittest.mock import patch

import cli_style as ui
from main import main
from pcb import PCB
from pcb_manager import PCBManager
from scheduler import schedule_fcfs, schedule_rr


ROOT = Path(__file__).resolve().parents[1]
# The official Phase 3 Round-Robin run (quantum 3) at the 78-column cap.
OFFICIAL_78 = [
    "0 CS 1 P0 4 CS 5 P1 8 CS 9 P2 10 CS 11 P3 14 CS 15 P4 18 CS 19 P5 22",
    "22 CS 23 P0 26 CS 27 P1 30 CS 31 P4 32 CS 33 P5 34 CS 35 P0 37 CS 38 P1 40",
]


class StyleTests(unittest.TestCase):
    def test_redirected_output_has_no_escape_codes_or_pause(self):
        with redirect_stdout(io.StringIO()) as output:
            ui.screen("View", 2, "Loaded 2 PCBs")
            ui.message("Error: Example", "error")
            with patch("builtins.input") as read:
                ui.pause()
                read.assert_not_called()
        self.assertNotIn("\033", output.getvalue())
        self.assertIn("Current PCBs: 2", output.getvalue())

    def test_colors_reset_and_no_color_is_respected(self):
        with patch.object(ui, "terminal_effects", return_value=True):
            with patch.dict(os.environ, {}, clear=True):
                self.assertEqual(ui.styled("Exit", "error"), "\033[1;31mExit\033[0m")
            with patch.dict(os.environ, {"NO_COLOR": "1"}):
                self.assertEqual(ui.styled("Exit", "error"), "Exit")

    def test_dumb_terminal_has_no_effects(self):
        with patch.object(ui, "interactive", return_value=True):
            with patch.dict(os.environ, {"TERM": "dumb"}):
                self.assertFalse(ui.terminal_effects())

    def test_screen_clear_can_be_disabled(self):
        with patch.object(ui, "terminal_effects", return_value=True):
            with redirect_stdout(io.StringIO()) as output:
                ui.screen("Menu")
            self.assertIn("\033[2J\033[H", output.getvalue())
            with patch.object(ui, "CLEAR_SCREENS", False):
                with redirect_stdout(io.StringIO()) as output:
                    ui.screen("Menu")
            self.assertNotIn("\033[2J", output.getvalue())

    def test_interactive_menu_pauses_and_remembers_actual_result(self):
        with patch.object(ui, "interactive", return_value=True):
            with patch.object(ui, "terminal_effects", return_value=False):
                # View an empty collection, acknowledge it, then exit.
                with patch("builtins.input", side_effect=["2", "", "7"]) as read:
                    with redirect_stdout(io.StringIO()) as output:
                        main()
        self.assertEqual(read.call_count, 3)
        self.assertIn("Previous action: View: Displayed 0 PCB(s).", output.getvalue())

    def test_failed_action_is_not_reported_as_success(self):
        with patch("builtins.input", side_effect=["3", "cat", "7"]):
            with redirect_stdout(io.StringIO()) as output:
                main()
        self.assertIn("Previous action: Add: Error: All PCB fields must be integers.",
                      output.getvalue())

    def test_narrow_table_keeps_every_field(self):
        pcb = PCB(1, 2000, 0, 4, 3, 1)
        with patch("cli_style.shutil.get_terminal_size", return_value=os.terminal_size((40, 24))):
            with redirect_stdout(io.StringIO()) as output:
                ui.pcb_table([pcb])
        for text in ["ID: 1", "Memory: 2000", "Arrival: 0", "CPU Required: 4",
                     "Quantum: 3", "CS Penalty: 1"]:
            self.assertIn(text, output.getvalue())

    def render(self, function, argument, width):
        # Fix the terminal width so wrapping and fallbacks are predictable.
        with patch("cli_style.shutil.get_terminal_size",
                   return_value=os.terminal_size((width, 30))):
            with redirect_stdout(io.StringIO()) as output:
                function(argument)
        return output.getvalue()

    def official_rr(self):
        manager = PCBManager()
        manager.load_from_file(ROOT / "data/phase3_official.txt")
        return schedule_rr(manager.get_pcbs(), 3)

    def test_timeline_caps_width_at_78(self):
        slices = self.official_rr()["slices"]
        self.assertEqual(self.render(ui.timeline, slices, 500).splitlines(), OFFICIAL_78)
        self.assertEqual(self.render(ui.timeline, slices, 78).splitlines(), OFFICIAL_78)

    def test_timeline_marks_idle_and_continuing_slices(self):
        manager = PCBManager()
        manager.load_from_file(ROOT / "data/phase2_idle.txt")
        text = self.render(ui.timeline, schedule_fcfs(manager.get_pcbs())["slices"], 78)
        self.assertEqual(text, "0 idle 5 CS 6 P1 8 idle 12 CS 13 P2 14\n")
        lone = schedule_rr([PCB(1, 1, 0, 7, 3, 1)], 3)["slices"]
        self.assertEqual(self.render(ui.timeline, lone, 78), "0 CS 1 P1 4 P1 7 P1 8\n")

    def test_timeline_wraps_between_whole_slices(self):
        slices = self.official_rr()["slices"]
        self.assertEqual(self.render(ui.timeline, slices, 30).splitlines(), [
            "0 CS 1 P0 4 CS 5 P1 8",
            "8 CS 9 P2 10 CS 11 P3 14",
            "14 CS 15 P4 18 CS 19 P5 22",
            "22 CS 23 P0 26 CS 27 P1 30",
            "30 CS 31 P4 32 CS 33 P5 34",
            "34 CS 35 P0 37 CS 38 P1 40",
        ])
        self.assertEqual(self.render(ui.timeline, slices, 78).splitlines(), OFFICIAL_78)

        odd = schedule_rr([PCB(-3, 1, 0, 4, 3, 1), PCB(1000, 1, 0, 4, 3, 1)], 1)
        text = self.render(ui.timeline, odd["slices"], 30)
        tokens = text.split()
        self.assertIn("P-3", tokens)
        self.assertIn("P1000", tokens)
        self.assertNotIn("\033", text)
        for line in text.splitlines():
            self.assertFalse(line.endswith("CS"))
            self.assertLessEqual(len(line), 30)

    def test_results_table_sideways_and_fallback(self):
        rows = self.official_rr()["processes"]
        text = self.render(ui.results_table, rows, 100)
        lines = [line.split() for line in text.splitlines()]
        for expected in [["Process", "0", "1", "2", "3", "4", "5"],
                         ["Arrival", "0", "1", "2", "3", "3", "4"],
                         ["CPU", "8", "8", "1", "3", "4", "4"],
                         ["Completion", "37", "40", "10", "14", "32", "34"],
                         ["Turnaround", "37", "39", "8", "11", "29", "30"]]:
            self.assertIn(expected, lines)
        self.assertNotIn("\033", text)

        many = schedule_fcfs([PCB(i, 1, 0, 1, 3, 1) for i in range(30)])["processes"]
        text = self.render(ui.results_table, many, 100)
        lines = [line.split() for line in text.splitlines()]
        self.assertIn(["ID", "Arrival", "CPU", "Completion", "Turnaround"], lines)
        self.assertEqual(sum(1 for line in lines if len(line) == 5 and line[0].isdigit()), 30)
        self.assertNotIn("\033", text)

        text = self.render(ui.results_table, rows, 20)
        self.assertIn("Turnaround: 37", text)
        self.assertIn("Completion: 40", text)
        self.assertNotIn("\033", text)

if __name__ == "__main__":
    unittest.main()
