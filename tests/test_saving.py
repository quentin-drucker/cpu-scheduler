import io
import subprocess
import sys
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from main import main, load_pcbs_from_input, save_pcbs_from_input
from pcb import PCB
from pcb_manager import PCBManager


PROJECT_FOLDER = Path(__file__).resolve().parents[1]


def records(manager):
    # Compare all six values, rather than just comparing record counts.
    return [
        (pcb.process_id, pcb.memory, pcb.arrival_time, pcb.cpu_required,
         pcb.quantum, pcb.context_switch_penalty)
        for pcb in manager.get_pcbs()
    ]


class SavingTests(unittest.TestCase):
    def setUp(self):
        # Each test gets a temporary folder, leaving the real datasets alone.
        self.folder = TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.destination = Path(self.folder.name) / "saved.txt"
        self.manager = PCBManager()

    def run_prompt(self, function, answers):
        # Supply keyboard responses and capture the messages for checking.
        output = io.StringIO()
        with patch("builtins.input", side_effect=answers):
            with redirect_stdout(output):
                function(self.manager)
        return output.getvalue()

    def test_all_datasets_can_be_saved_and_reloaded(self):
        for number, count in [(1, 4), (2, 5), (3, 7)]:
            with self.subTest(dataset=number):
                source = PROJECT_FOLDER / "data" / f"dataset{number}.txt"
                self.manager.load_from_file(source)
                # Adding a record checks that saving includes manual additions.
                self.manager.add_pcb(PCB(99, 1000, 8, 3, 3, 1))
                before = records(self.manager)
                destination = self.destination.with_name(f"set{number}.txt")
                self.assertEqual(self.manager.save_to_file(destination), count + 1)

                reloaded = PCBManager()
                self.assertEqual(reloaded.load_from_file(destination), count + 1)
                self.assertEqual(records(reloaded), before)
                self.assertEqual(records(self.manager), before)

    def test_exact_file_format_and_nonpositive_ids(self):
        # Zero and negative IDs are allowed by the stated assignment rules.
        self.manager.add_pcb(PCB(0, 2000, 0, 4, 3, 1))
        self.manager.add_pcb(PCB(-1, 500, 2, 6, 3, 1))
        self.manager.save_to_file(self.destination)
        self.assertEqual(
            self.destination.read_text(encoding="utf-8"),
            "0 2000 0 4 3 1\n-1 500 2 6 3 1\n"
        )
        reloaded = PCBManager()
        reloaded.load_from_file(self.destination)
        self.assertEqual(records(reloaded), records(self.manager))

    def test_empty_collection_round_trip(self):
        self.assertEqual(self.manager.save_to_file(self.destination), 0)
        self.assertEqual(self.destination.read_bytes(), b"")
        reloaded = PCBManager()
        reloaded.add_pcb(PCB(1, 1, 0, 1, 1, 1))
        self.assertEqual(reloaded.load_from_file(self.destination), 0)
        self.assertEqual(records(reloaded), [])

    def test_existing_file_is_preserved(self):
        self.destination.write_text("Keep this file.\n", encoding="utf-8")
        self.manager.add_pcb(PCB(1, 2000, 0, 4, 3, 1))
        before = records(self.manager)
        output = self.run_prompt(save_pcbs_from_input, [str(self.destination), "N"])
        self.assertIn("Save cancelled", output)
        self.assertNotIn("Successfully saved", output)
        self.assertEqual(self.destination.read_text(), "Keep this file.\n")
        self.assertEqual(records(self.manager), before)

    def test_blank_filename_does_not_attempt_save(self):
        with patch.object(self.manager, "save_to_file") as save:
            output = self.run_prompt(save_pcbs_from_input, ["   "])
        self.assertIn("A file name is required", output)
        save.assert_not_called()

    def test_overwrite_defaults_to_rejecting_existing_file(self):
        self.destination.write_text("original", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            self.manager.save_to_file(self.destination)
        self.assertEqual(self.destination.read_text(), "original")

    def test_overwrite_cancel_choices_preserve_file(self):
        self.destination.write_text("original", encoding="utf-8")
        for choice in ["", "n", "NO", "C"]:
            with self.subTest(choice=choice):
                output = self.run_prompt(save_pcbs_from_input, [str(self.destination), choice])
                self.assertIn("Save cancelled", output)
                self.assertEqual(self.destination.read_text(), "original")

    def test_confirmed_overwrite_reloads_in_fresh_python_process(self):
        self.manager.add_pcb(PCB(1, 2000, 0, 5, 3, 1))
        self.manager.save_to_file(self.destination)
        self.manager.load_from_file(self.destination)
        self.manager.update_pcb(1, PCB(1, 2000, 0, 4, 3, 1))
        self.manager.add_pcb(PCB(2, 500, 1, 2, 3, 1))
        output = self.run_prompt(
            save_pcbs_from_input, [str(self.destination), "maybe", "yes"]
        )
        self.assertIn("Enter Y to overwrite", output)
        self.assertIn("Successfully saved 2 PCB(s)", output)
        code = (
            "import sys; from pcb_manager import PCBManager; "
            "m=PCBManager(); m.load_from_file(sys.argv[1]); "
            "assert len(m.get_pcbs()) == 2; "
            "assert m.get_pcb(1).cpu_required == 4; "
            "assert m.get_pcb(2).memory == 500"
        )
        subprocess.run([sys.executable, "-c", code, str(self.destination)],
                       cwd=PROJECT_FOLDER, check=True, capture_output=True)
        self.assertEqual(list(self.destination.parent.glob(".pcb-save-*")), [])

    def test_failed_replacement_preserves_original_and_cleans_temp_file(self):
        self.destination.write_text("original", encoding="utf-8")
        with patch("pcb_manager.os.replace", side_effect=PermissionError("denied")):
            output = self.run_prompt(save_pcbs_from_input, [str(self.destination), "Y"])
        self.assertIn("Could not save PCB data", output)
        self.assertNotIn("Successfully saved", output)
        self.assertEqual(self.destination.read_text(), "original")
        self.assertEqual(list(self.destination.parent.glob(".pcb-save-*")), [])

    def test_failed_temporary_write_preserves_original(self):
        self.destination.write_text("original", encoding="utf-8")
        temporary = self.destination.parent / ".pcb-save-test.tmp"
        temporary.write_text("partial", encoding="utf-8")
        with patch("pcb_manager.NamedTemporaryFile") as create:
            file = create.return_value.__enter__.return_value
            file.name = str(temporary)
            file.writelines.side_effect = OSError("Disk full")
            with self.assertRaises(OSError):
                self.manager.save_to_file(self.destination, overwrite=True)
        self.assertEqual(self.destination.read_text(), "original")
        self.assertFalse(temporary.exists())

    def test_empty_overwrite_and_invalid_data_protection(self):
        self.destination.write_text("original", encoding="utf-8")
        pcb = PCB(1, 1, 0, 1, 1, 1)
        self.manager.add_pcb(pcb)
        pcb.memory = 0
        with self.assertRaises(ValueError):
            self.manager.save_to_file(self.destination, overwrite=True)
        self.assertEqual(self.destination.read_text(), "original")
        self.manager.remove_pcb(1)
        self.assertEqual(self.manager.save_to_file(self.destination, overwrite=True), 0)
        self.assertEqual(self.destination.read_text(), "")
        self.assertEqual(self.manager.load_from_file(self.destination), 0)

    def test_missing_parent_folder_reports_error(self):
        destination = self.destination.parent / "missing" / "saved.txt"
        output = self.run_prompt(save_pcbs_from_input, [str(destination)])
        self.assertIn("Error:", output)
        self.assertNotIn("Successfully saved", output)
        self.assertFalse(destination.exists())

    def test_directory_destination_reports_error(self):
        output = self.run_prompt(
            save_pcbs_from_input, [str(self.destination.parent)]
        )
        self.assertIn("Error:", output)
        self.assertNotIn("Successfully saved", output)

    def test_permission_and_write_failures_report_error(self):
        # Simulate these failures so the test works regardless of permissions.
        for error in [PermissionError("Permission denied"), OSError("Disk full")]:
            with self.subTest(error=type(error).__name__):
                with patch.object(self.manager, "save_to_file", side_effect=error):
                    output = self.run_prompt(
                        save_pcbs_from_input, [str(self.destination)]
                    )
                self.assertIn("Could not save PCB data", output)
                self.assertNotIn("Successfully saved", output)

    def test_changed_invalid_records_are_not_saved(self):
        # Objects are currently editable, so saving checks their values again.
        for field, value in [("memory", 0), ("process_id", 1),
                             ("quantum", 4), ("context_switch_penalty", 2)]:
            with self.subTest(field=field):
                self.manager = PCBManager()
                self.manager.add_pcb(PCB(1, 2000, 0, 4, 3, 1))
                changed = PCB(2, 500, 1, 2, 3, 1)
                self.manager.add_pcb(changed)
                setattr(changed, field, value)
                with self.assertRaises(ValueError):
                    self.manager.save_to_file(self.destination)
                self.assertFalse(self.destination.exists())

    def test_loading_directory_reports_error_and_preserves_records(self):
        self.manager.add_pcb(PCB(1, 2000, 0, 4, 3, 1))
        before = records(self.manager)
        output = self.run_prompt(
            load_pcbs_from_input, ["M", str(self.destination.parent)]
        )
        self.assertIn("Error:", output)
        self.assertEqual(records(self.manager), before)

    def test_full_menu_load_add_save_reload_view_exit(self):
        source = PROJECT_FOLDER / "data" / "dataset1.txt"
        answers = [
            "1", "M", str(source),
            "3", "5", "1000", "4", "3", "3", "1",
            "4", str(self.destination),
            "1", "M", str(self.destination), "2", "9", "7"
        ]
        output = io.StringIO()
        with patch("builtins.input", side_effect=answers):
            with redirect_stdout(output):
                main()
        text = output.getvalue()
        self.assertIn("Successfully saved 5 PCB(s)", text)
        self.assertIn("Successfully loaded 5 PCB(s)", text)
        self.assertIn("Total PCBs: 5", text)
        self.assertIn("Please enter a choice from 1 to 8", text)
        self.assertIn("Exiting Process Manager", text)
        reloaded = PCBManager()
        reloaded.load_from_file(self.destination)
        self.assertEqual(records(reloaded)[-1], (5, 1000, 4, 3, 3, 1))


if __name__ == "__main__":
    unittest.main()
