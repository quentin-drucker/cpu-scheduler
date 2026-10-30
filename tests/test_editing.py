import io
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from main import edit_pcb_from_input, remove_pcb_from_input, main
from pcb import PCB
from pcb_manager import PCBManager


class EditingTests(unittest.TestCase):
    def setUp(self):
        self.manager = PCBManager()
        self.manager.add_pcb(PCB(1, 2000, 0, 5, 3, 1))
        self.manager.add_pcb(PCB(2, 4000, 1, 2, 3, 1))

    def run_prompt(self, function, answers):
        output = io.StringIO()
        with patch("builtins.input", side_effect=answers):
            with redirect_stdout(output):
                function(self.manager)
        return output.getvalue()

    def test_edit_cpu_changes_only_selected_field_and_keeps_order(self):
        other = self.manager.get_pcb(2)
        self.run_prompt(edit_pcb_from_input, ["1", "4", "4"])
        self.assertEqual(vars(self.manager.get_pcb(1)), {
            "process_id": 1, "memory": 2000, "arrival_time": 0,
            "cpu_required": 4, "quantum": 3, "context_switch_penalty": 1,
            "remaining_time": 4
        })
        self.assertIs(self.manager.get_pcbs()[1], other)

    def test_each_field_accepts_valid_values(self):
        for field, attribute, value in [
            (1, "process_id", -1), (2, "memory", 1000),
            (3, "arrival_time", 2), (4, "cpu_required", 4),
            (5, "quantum", 3), (6, "context_switch_penalty", 1)
        ]:
            with self.subTest(field=field):
                self.setUp()
                self.run_prompt(edit_pcb_from_input, ["1", str(field), str(value)])
                self.assertEqual(getattr(self.manager.get_pcbs()[0], attribute), value)

    def test_invalid_numeric_values_leave_original_untouched(self):
        # Test each individual bound and both collection-wide shared values.
        for field, value in [(1, 2), (2, 0), (2, -1), (3, -1),
                             (4, 0), (4, -1), (5, 0), (5, -1), (5, 4),
                             (6, 0), (6, -1), (6, 2)]:
            with self.subTest(field=field, value=value):
                original = self.manager.get_pcb(1)
                before = vars(original).copy()
                output = self.run_prompt(
                    edit_pcb_from_input, ["1", str(field), str(value), "C"]
                )
                self.assertIn("Error:", output)
                self.assertIs(self.manager.get_pcb(1), original)
                self.assertEqual(vars(original), before)

    def test_text_and_blank_values_rejected_for_every_field(self):
        for field in range(1, 7):
            with self.subTest(field=field):
                original = self.manager.get_pcb(1)
                output = self.run_prompt(
                    edit_pcb_from_input,
                    ["1", str(field), "cat", "_", "", "   ", "1.5", "C"]
                )
                self.assertEqual(output.count("new value must be an integer"), 5)
                self.assertIs(self.manager.get_pcb(1), original)

    def test_bad_selection_can_be_corrected(self):
        output = self.run_prompt(
            edit_pcb_from_input, ["cat", "", "999", "1", "0", "x", "4", "4"]
        )
        self.assertIn("was not found", output)
        self.assertEqual(self.manager.get_pcb(1).cpu_required, 4)

    def test_cancel_at_each_edit_prompt(self):
        for answers in [["C"], ["1", "C"], ["1", "4", "c"]]:
            original = self.manager.get_pcb(1)
            self.run_prompt(edit_pcb_from_input, answers)
            self.assertIs(self.manager.get_pcb(1), original)

    def test_manager_rejects_invalid_replacement_and_missing_id(self):
        original = self.manager.get_pcb(1)
        invalid = PCB(1, 2000, 0, 4, 3, 1)
        invalid.cpu_required = "cat"
        for replacement in [invalid, "not a PCB", PCB(2, 1, 0, 1, 3, 1)]:
            with self.assertRaises(ValueError):
                self.manager.update_pcb(1, replacement)
        with self.assertRaises(ValueError):
            self.manager.update_pcb(999, original)
        with self.assertRaises(ValueError):
            self.manager.remove_pcb(999)
        self.assertIs(self.manager.get_pcb(1), original)

    def test_shared_values_for_last_remaining_pcb_can_change(self):
        self.manager.remove_pcb(2)
        self.run_prompt(edit_pcb_from_input, ["1", "5", "4"])
        self.run_prompt(edit_pcb_from_input, ["1", "6", "2"])
        self.assertEqual(self.manager.get_pcb(1).quantum, 4)
        self.assertEqual(self.manager.get_pcb(1).context_switch_penalty, 2)
        with self.assertRaises(ValueError):
            self.manager.add_pcb(PCB(3, 1, 0, 1, 3, 1))

    def test_remove_requires_yes(self):
        for response in ["N", "no", "", "C"]:
            self.run_prompt(remove_pcb_from_input, ["1", response])
            self.assertEqual(len(self.manager.get_pcbs()), 2)
        self.run_prompt(remove_pcb_from_input, ["1", "cat", "yes"])
        self.assertEqual([p.process_id for p in self.manager.get_pcbs()], [2])

    def test_remove_allows_id_reuse_and_empty_set_new_shared_values(self):
        self.manager.remove_pcb(1)
        self.manager.add_pcb(PCB(1, 1, 0, 1, 3, 1))
        self.manager.remove_pcb(1)
        self.manager.remove_pcb(2)
        self.assertEqual(self.manager.get_pcbs(), [])
        self.manager.add_pcb(PCB(1, 1, 0, 1, 7, 2))
        self.assertEqual(self.manager.get_pcb(1).quantum, 7)

    def test_empty_collection_needs_no_input(self):
        self.manager = PCBManager()
        for function in [edit_pcb_from_input, remove_pcb_from_input]:
            self.assertIn("No PCBs", self.run_prompt(function, []))

    def test_menu_edit_remove_save_reload_preserves_original_file(self):
        with TemporaryDirectory() as folder:
            source = Path(folder) / "original.txt"
            destination = Path(folder) / "revised.txt"
            self.manager.save_to_file(source)
            original_text = source.read_text()
            answers = ["1", "M", str(source), "5", "1", "4", "4",
                       "6", "2", "Y", "4", str(destination),
                       "1", "M", str(destination), "2", "7"]
            with patch("builtins.input", side_effect=answers):
                with redirect_stdout(io.StringIO()) as output:
                    main()
            self.assertIn("Total PCBs: 1", output.getvalue())
            self.assertEqual(source.read_text(), original_text)
            reloaded = PCBManager()
            reloaded.load_from_file(destination)
            self.assertEqual(len(reloaded.get_pcbs()), 1)
            self.assertEqual(reloaded.get_pcb(1).cpu_required, 4)


if __name__ == "__main__":
    unittest.main()
