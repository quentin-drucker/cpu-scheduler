import io
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from file_picker import choose_data_file
from main import load_pcbs_from_input
from pcb import PCB
from pcb_manager import PCBManager


class FilePickerTests(unittest.TestCase):
    def setUp(self):
        # Test files stay separate from the project's real data folder.
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)

    def make_files(self, count):
        for number in range(1, count + 1):
            (self.folder / f"file{number:02}.txt").write_text(
                f"{number} 2000 0 4 3 1\n", encoding="utf-8"
            )

    def pick(self, answers, folder=None):
        output = io.StringIO()
        with patch("builtins.input", side_effect=answers):
            with redirect_stdout(output):
                selected = choose_data_file(folder or self.folder)
        return selected, output.getvalue()

    def test_sorted_text_files_only(self):
        for name in ["z.txt", "B.TXT", "a.txt", "notes.md"]:
            (self.folder / name).touch()
        (self.folder / "folder.txt").mkdir()
        selected, output = self.pick(["2"])
        self.assertEqual(selected, self.folder / "B.TXT")
        self.assertIn("1. a.txt", output)
        self.assertIn("3. z.txt", output)
        self.assertNotIn("notes.md", output)
        self.assertNotIn("folder.txt", output)

    def test_page_boundaries_and_number_mapping(self):
        # Include exact multiples of nine and partly filled final pages.
        for count, pages, key in [(9, 1, "9"), (10, 2, "1"),
                                  (18, 2, "9"), (19, 3, "1")]:
            with self.subTest(count=count):
                folder = self.folder / str(count)
                folder.mkdir()
                for number in range(1, count + 1):
                    (folder / f"file{number:02}.txt").touch()
                selected, output = self.pick(["n"] * (pages - 1) + [key], folder)
                self.assertEqual(selected, folder / f"file{count:02}.txt")
                self.assertIn(f"Page {pages} of {pages}", output)
                self.assertNotIn("10. ", output)

    def test_previous_page_returns_to_first_files(self):
        self.make_files(10)
        selected, output = self.pick(["n", " p ", "1"])
        self.assertEqual(selected, self.folder / "file01.txt")
        self.assertEqual(output.count("Page 1 of 2"), 2)

    def test_invalid_choices_and_page_limits_keep_picker_open(self):
        self.make_files(10)
        selected, output = self.pick(["p", "", "0", "10", "hello",
                                      "n", "n", "2", "1"])
        self.assertEqual(selected, self.folder / "file10.txt")
        self.assertIn("Already on the first page", output)
        self.assertIn("Already on the last page", output)
        self.assertIn("Error: Choose a displayed number", output)

    def test_empty_and_missing_folders_allow_manual_entry(self):
        for folder in [self.folder, self.folder / "missing"]:
            with self.subTest(folder=folder):
                selected, output = self.pick(["m", "external.dat"], folder)
                self.assertEqual(selected, folder / "external.dat")
                self.assertIn("No .txt files", output)

    def test_listing_permission_error_still_allows_cancel(self):
        with patch("file_picker.Path.iterdir", side_effect=PermissionError("denied")):
            selected, output = self.pick(["c"])
        self.assertIsNone(selected)
        self.assertIn("Could not list the data folder", output)

    def test_blank_manual_path_returns_to_picker(self):
        selected, output = self.pick(["M", "   ", "C"])
        self.assertIsNone(selected)
        self.assertIn("A file name is required", output)

    def test_file_list_refreshes_when_reopened(self):
        self.make_files(1)
        self.pick(["C"])
        self.make_files(2)
        selected, _ = self.pick(["2"])
        self.assertEqual(selected, self.folder / "file02.txt")

    def test_numbered_load_and_cancel_preserve_expected_state(self):
        self.make_files(10)
        manager = PCBManager()
        output = io.StringIO()
        with patch("file_picker.DATA_FOLDER", self.folder):
            with patch("builtins.input", side_effect=["N", "1", "C"]):
                with redirect_stdout(output):
                    load_pcbs_from_input(manager)
                    original = manager.get_pcbs()
                    load_pcbs_from_input(manager)
        self.assertEqual(original[0].process_id, 10)
        self.assertIs(manager.get_pcbs(), original)
        self.assertIn("Successfully loaded 1 PCB(s)", output.getvalue())
        self.assertIn("Loading cancelled", output.getvalue())

    def test_bad_or_disappeared_file_preserves_loaded_collection(self):
        self.make_files(1)
        manager = PCBManager()
        manager.add_pcb(PCB(99, 2000, 0, 4, 3, 1))
        original = manager.get_pcbs()
        path = self.folder / "file01.txt"
        path.write_text("not valid PCB data", encoding="utf-8")
        with patch("file_picker.DATA_FOLDER", self.folder):
            with patch("builtins.input", return_value="1"):
                with redirect_stdout(io.StringIO()) as output:
                    load_pcbs_from_input(manager)
        self.assertIn("Error:", output.getvalue())
        self.assertIs(manager.get_pcbs(), original)

        # A file can disappear between displaying the list and selecting it.
        def remove_then_select(prompt):
            path.unlink()
            return "1"

        with patch("file_picker.DATA_FOLDER", self.folder):
            with patch("builtins.input", side_effect=remove_then_select):
                with redirect_stdout(io.StringIO()) as output:
                    load_pcbs_from_input(manager)
        self.assertIn("File not found", output.getvalue())
        self.assertIs(manager.get_pcbs(), original)


if __name__ == "__main__":
    unittest.main()
