"""Checks friendly filenames through both loading and saving."""

import io
import os
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from data_paths import resolve_data_path
from main import load_pcbs_from_input, save_pcbs_from_input
from pcb import PCB
from pcb_manager import PCBManager


class DataPathTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name) / "data"
        self.folder.mkdir()
        self.manager = PCBManager()
        self.manager.add_pcb(PCB(9, 1000, 0, 2, 3, 1))

    def run_prompt(self, function, answers):
        # Redirect both entry points to a temporary data folder. No test
        # writes to or overwrites the student's real process files.
        with patch("data_paths.DATA_FOLDER", self.folder), \
                patch("file_picker.DATA_FOLDER", self.folder), \
                patch("builtins.input", side_effect=answers), \
                redirect_stdout(io.StringIO()) as output:
            function(self.manager)
        return output.getvalue()

    def test_four_forms_save_and_reload_the_same_file(self):
        forms = ["example", "example.txt", "data/example", "data/example.txt"]
        destination = self.folder / "example.txt"
        for name in forms:
            with self.subTest(name=name):
                if destination.exists():
                    destination.unlink()
                output = self.run_prompt(save_pcbs_from_input, [name])
                self.assertIn(f"Saving to: {destination}", output)
                self.assertEqual(destination.read_text(), "9 1000 0 2 3 1\n")
                for load_name in forms:
                    output = self.run_prompt(load_pcbs_from_input, ["M", load_name])
                    self.assertIn(f"Loading from: {destination}", output)
                    self.assertIn("Successfully loaded 1 PCB(s)", output)
                    self.assertEqual(self.manager.get_pcbs()[0].process_id, 9)

    def test_equivalent_name_still_requires_overwrite_confirmation(self):
        destination = self.folder / "example.txt"
        destination.write_text("original contents\n")
        output = self.run_prompt(save_pcbs_from_input, ["data/example", "N"])
        self.assertIn("Save cancelled", output)
        self.assertEqual(destination.read_text(), "original contents\n")
        self.run_prompt(save_pcbs_from_input, ["example", "Y"])
        self.assertEqual(destination.read_text(), "9 1000 0 2 3 1\n")

    def test_explicit_paths_and_extensions_keep_their_locations(self):
        for text, expected in [
            (" example.TXT ", self.folder / "example.TXT"),
            ("example.dat", self.folder / "example.dat"),
            ("other/example", Path("other/example.txt")),
            ("./example", Path("example.txt")),
            ("../example.dat", Path("../example.dat")),
            ("~/example", Path.home() / "example.txt"),
            (str(self.folder.parent / "external"), self.folder.parent / "external.txt")
        ]:
            with self.subTest(text=text):
                self.assertEqual(resolve_data_path(text, self.folder), expected)
        external = self.folder.parent / "external"
        self.run_prompt(save_pcbs_from_input, [str(external)])
        self.assertTrue(external.with_suffix(".txt").is_file())
        self.assertIn("Successfully loaded", self.run_prompt(
            load_pcbs_from_input, ["M", str(external)]))

    def test_project_data_names_work_from_another_working_directory(self):
        original = Path.cwd()
        try:
            elsewhere = self.folder.parent / "elsewhere"
            elsewhere.mkdir()
            os.chdir(elsewhere)
            self.run_prompt(save_pcbs_from_input, ["data/example"])
            self.assertIn("Successfully loaded", self.run_prompt(
                load_pcbs_from_input, ["M", "example.txt"]))
            self.assertFalse((Path.cwd() / "example.txt").exists())
        finally:
            os.chdir(original)

    def test_missing_load_preserves_current_records(self):
        original = self.manager.get_pcbs()
        output = self.run_prompt(load_pcbs_from_input, ["M", "missing"])
        self.assertIn(str(self.folder / "missing.txt"), output)
        self.assertIn("File not found", output)
        self.assertIs(self.manager.get_pcbs(), original)

    def test_blank_directory_and_trailing_slash_do_not_create_files(self):
        for name in ["", "   ", "data", "data/new_folder/"]:
            with self.subTest(name=name):
                self.assertIn("Error:", self.run_prompt(save_pcbs_from_input, [name]))
        output = self.run_prompt(load_pcbs_from_input, ["M", "data/new_folder/", "C"])
        self.assertIn("path ending", output)
        self.assertEqual(list(self.folder.iterdir()), [])
        self.assertFalse(self.folder.with_suffix(".txt").exists())


if __name__ == "__main__":
    unittest.main()
