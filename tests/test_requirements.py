import io
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from main import add_pcb_from_input, display_pcbs, load_pcbs_from_input
from pcb import PCB
from pcb_manager import PCBManager


PROJECT_FOLDER = Path(__file__).resolve().parents[1]
FIELDS = ["process_id", "memory", "arrival_time", "cpu_required",
          "quantum", "context_switch_penalty"]


class RequirementTests(unittest.TestCase):
    def setUp(self):
        self.folder = TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "input.txt"
        self.manager = PCBManager()
        self.manager.add_pcb(PCB(90, 1000, 0, 1, 3, 1))

    def run_prompt(self, function, answers):
        with patch("builtins.input", side_effect=answers):
            with redirect_stdout(io.StringIO()) as output:
                function(self.manager)
        return output.getvalue()

    def assert_file_rejected(self, bad_line, expected):
        # A valid first record must not partly replace the existing collection.
        self.path.write_text("1 2000 0 4 3 1\n" + bad_line + "\n", encoding="utf-8")
        original = self.manager.get_pcbs()
        with self.assertRaisesRegex(ValueError, "Line 2:.*" + expected):
            self.manager.load_from_file(self.path)
        self.assertIs(self.manager.get_pcbs(), original)
        self.assertEqual([p.process_id for p in original], [90])

    def test_supplied_datasets_have_exact_expected_records(self):
        # Independent expected values detect accidental changes to sample files.
        expected = [
            [(1,2000,0,4,3,1), (2,4000,1,5,3,1), (3,12000,2,2,3,1), (4,500,3,6,3,1)],
            [(1,2000,0,4,3,1), (2,4000,1,1,3,1), (3,12000,2,2,3,1), (4,500,3,2,3,1), (5,500,4,4,3,1)],
            [(1,2000,0,6,3,1), (2,4000,1,4,3,1), (3,12000,2,5,3,1), (4,500,3,5,3,1), (5,500,4,4,3,1), (6,500,6,9,3,1), (7,500,7,4,3,1)]
        ]
        for number, rows in enumerate(expected, start=1):
            with self.subTest(dataset=number):
                count = self.manager.load_from_file(PROJECT_FOLDER / "data" / f"dataset{number}.txt")
                self.assertEqual(count, len(rows))
                self.assertEqual([tuple(getattr(p, f) for f in FIELDS)
                                  for p in self.manager.get_pcbs()], rows)

    def test_loading_replaces_set_and_establishes_new_shared_values(self):
        self.path.write_text("90 1 0 1 7 2\n", encoding="utf-8")
        self.assertEqual(self.manager.load_from_file(self.path), 1)
        self.manager.add_pcb(PCB(91, 1, 0, 1, 7, 2))
        self.assertEqual(self.manager.get_pcb(90).quantum, 7)

    def test_file_rejects_nonintegers_in_every_field(self):
        for index in range(6):
            for invalid in ["cat", "_", "1.5"]:
                with self.subTest(field=FIELDS[index], value=invalid):
                    values = ["2", "2000", "1", "4", "3", "1"]
                    values[index] = invalid
                    self.assert_file_rejected(" ".join(values), "must be integers")

    def test_file_rejects_wrong_field_counts(self):
        for line in ["2 2000 1 4 3", "2 2000 1 4 3 1 99"]:
            with self.subTest(line=line):
                self.assert_file_rejected(line, "expected 6 values")

    def test_file_rejects_all_numeric_bounds(self):
        for index, value in [(1,0), (1,-1), (2,-1), (3,0), (3,-1),
                             (4,0), (4,-1), (5,0), (5,-1)]:
            with self.subTest(field=FIELDS[index], value=value):
                values = [2, 2000, 1, 4, 3, 1]
                values[index] = value
                self.assert_file_rejected(" ".join(map(str, values)), "must be")

    def test_file_rejects_duplicate_id_and_shared_value_mismatches(self):
        for line, message in [("1 2000 1 4 3 1", "already exists"),
                              ("2 2000 1 4 4 1", "Quantum must be 3"),
                              ("2 2000 1 4 3 2", "penalty must be 1")]:
            with self.subTest(line=line):
                self.assert_file_rejected(line, message)

    def test_whitespace_blanks_and_actual_line_numbers(self):
        self.path.write_text("\n  1\t2000 0 4 3 1  \n\n2 500 1 2 3 1\n", encoding="utf-8")
        self.assertEqual(self.manager.load_from_file(self.path), 2)
        self.path.write_text("\n1 2000 0 4 3 1\n\ninvalid\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Line 4:"):
            self.manager.load_from_file(self.path)
        self.assertEqual(len(self.manager.get_pcbs()), 2)

    def test_missing_file_reports_error_without_losing_data(self):
        output = self.run_prompt(load_pcbs_from_input, ["M", str(self.path)])
        self.assertIn("File not found", output)
        self.assertEqual(self.manager.get_pcb(90).memory, 1000)

    def test_manual_add_rejects_nonintegers_at_every_prompt(self):
        for index in range(6):
            for invalid in ["cat", "_", "", "1.5"]:
                with self.subTest(field=FIELDS[index], value=invalid):
                    answers = ["2", "2000", "1", "4", "3", "1"][:index] + [invalid]
                    output = self.run_prompt(add_pcb_from_input, answers)
                    self.assertIn("All PCB fields must be integers", output)
                    self.assertEqual(len(self.manager.get_pcbs()), 1)

    def test_manual_add_rejects_bounds_duplicates_and_mismatches(self):
        for index, value in [(0,90), (1,0), (1,-1), (2,-1), (3,0), (3,-1),
                             (4,0), (4,-1), (4,4), (5,0), (5,-1), (5,2)]:
            with self.subTest(field=FIELDS[index], value=value):
                values = [2, 2000, 1, 4, 3, 1]
                values[index] = value
                output = self.run_prompt(add_pcb_from_input, list(map(str, values)))
                self.assertIn("Error:", output)
                self.assertEqual([p.process_id for p in self.manager.get_pcbs()], [90])

    def test_valid_boundary_values_and_no_total_memory_limit(self):
        self.manager = PCBManager()
        for process_id in [0, -1]:
            output = self.run_prompt(add_pcb_from_input,
                                     [str(process_id), "20000", "0", "1", "1", "1"])
            self.assertIn("added successfully", output)
        self.assertEqual(len(self.manager.get_pcbs()), 2)

    def test_display_empty_and_full_collection(self):
        self.manager = PCBManager()
        self.assertIn("No PCBs", self.run_prompt(display_pcbs, []))
        self.manager.add_pcb(PCB(90, 1234, 8, 7, 6, 5))
        output = self.run_prompt(display_pcbs, [])
        for value in ["ID", "Memory", "Arrival", "CPU Required", "Quantum",
                      "CS Penalty", "90", "1234", "8", "7", "6", "5", "Total PCBs: 1"]:
            self.assertIn(value, output)


if __name__ == "__main__":
    unittest.main()
