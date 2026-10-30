import io
import os
from contextlib import redirect_stdout
import unittest
from unittest.mock import patch

import cli_style as ui
from main import main
from pcb import PCB


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

    def test_schedule_table_wide_and_narrow_keep_all_values(self):
        # Distinct numbers make swapped or missing fields easy to notice.
        result = {"process_id": 90, "arrival_time": 3, "cpu_required": 5,
                  "start_time": 8, "finish_time": 13, "turnaround_time": 10}
        for width in [100, 35]:
            with self.subTest(width=width):
                with patch("cli_style.shutil.get_terminal_size",
                           return_value=os.terminal_size((width, 30))):
                    with redirect_stdout(io.StringIO()) as output:
                        ui.schedule_table([result])
                text = output.getvalue()
                self.assertNotIn("\033", text)
                if width == 100:
                    self.assertIn("Order", text)
                    row = next(line for line in text.splitlines() if line.startswith("1 "))
                    self.assertEqual(row.split(), ["1", "90", "3", "5", "8", "13", "10"])
                else:
                    for field in ["Order: 1", "ID: 90", "Arrival: 3", "CPU Required: 5",
                                  "Start: 8", "Finish: 13", "Turnaround: 10"]:
                        self.assertIn(field, text)

    def test_schedule_table_large_values_trigger_vertical_fallback(self):
        result = {"process_id": 12345678901234567890, "arrival_time": 1000000000,
                  "cpu_required": 1, "start_time": 1000000000,
                  "finish_time": 1000000001, "turnaround_time": 1}
        with patch("cli_style.shutil.get_terminal_size",
                   return_value=os.terminal_size((80, 30))):
            with redirect_stdout(io.StringIO()) as output:
                ui.schedule_table([result])
        self.assertIn("ID: 12345678901234567890", output.getvalue())
        self.assertIn("Finish: 1000000001", output.getvalue())


if __name__ == "__main__":
    unittest.main()
