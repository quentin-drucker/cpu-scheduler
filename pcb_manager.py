"""Manages process records and file operations without asking for user input."""

import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from pcb import PCB


class PCBManager:
    """Keeps the current list and checks rules shared by its processes."""

    def __init__(self):
        """Starts with an empty list of PCB objects."""

        # My main data structure is a Python list: an ordered collection that
        # can grow or shrink. Each item refers to one complete PCB object.
        # I keep file/addition order; this list is not sorted by arrival or ID.
        # A list is enough for these small datasets, so I search it with loops
        # instead of keeping an extra dictionary of process IDs in sync.
        self.pcb_list = []

    def add_pcb(self, pcb):
        """Checks a newly created PCB against the current set before adding it."""

        # Reject unrelated objects before trying to read their PCB fields.
        if not isinstance(pcb, PCB):
            raise ValueError("Only PCB objects can be added to the PCB list.")

        # IDs must be unique within the currently loaded set.
        # A list allows duplicates, so this rule needs an explicit check.
        for existing_pcb in self.pcb_list:
            if existing_pcb.process_id == pcb.process_id:
                raise ValueError(
                    f"Process ID {pcb.process_id} already exists."
                )

        # The first PCB supplies the shared value; later records must match it.
        if len(self.pcb_list) > 0:
            expected_quantum = self.pcb_list[0].quantum

            if pcb.quantum != expected_quantum:
                raise ValueError(
                    f"Quantum must be {expected_quantum} for this process set."
                )

        # The first PCB supplies the shared value; later records must match it.
        if len(self.pcb_list) > 0:
            expected_penalty = self.pcb_list[0].context_switch_penalty

            if pcb.context_switch_penalty != expected_penalty:
                raise ValueError(
                    "Context-switch penalty must be "
                    f"{expected_penalty} for this process set."
                )

        # append runs only after all collection checks have passed.
        self.pcb_list.append(pcb)

    def load_from_file(self, filename):
        """Validates a whole file before replacing the current process set."""

        # Build the candidate collection separately. A failed check must not
        # leave the real collection partly changed.
        temporary_manager = PCBManager()

        try:
            # with closes the file when reading finishes, even if an error occurs.
            with open(filename, "r", encoding="utf-8") as file:

                # enumerate starts at 1 so error messages match the file
                # line numbers, including blank lines.
                for line_number, line in enumerate(file, start=1):

                    # Remove surrounding whitespace, then skip completely blank lines.
                    line = line.strip()

                    if line == "":
                        continue

                    # split() accepts spaces or tabs and makes a temporary list
                    # of strings, e.g. ["1", "2000", "0", "4", "3", "1"].
                    # These six positions are fields of ONE process, unlike
                    # pcb_list, whose items are complete process objects.
                    values = line.split()

                    # Missing or extra fields would make the record ambiguous.
                    if len(values) != 6:
                        raise ValueError(
                            f"Line {line_number}: expected 6 values, "
                            f"but found {len(values)}."
                        )

                    try:
                        # Convert the six fields in the order used by the supplied datasets.
                        process_id = int(values[0])
                        memory = int(values[1])
                        arrival_time = int(values[2])
                        cpu_required = int(values[3])
                        quantum = int(values[4])
                        context_switch_penalty = int(values[5])

                    except ValueError:
                        raise ValueError(
                            f"Line {line_number}: all PCB values "
                            "must be integers."
                        )

                    try:
                        # The PCB constructor checks the individual rules.
                        pcb = PCB(
                            process_id,
                            memory,
                            arrival_time,
                            cpu_required,
                            quantum,
                            context_switch_penalty
                        )

                        # The temporary manager checks IDs, quantum, and penalty
                        # against the other incoming records.
                        temporary_manager.add_pcb(pcb)

                    # Attach the file line number to the original validation message.
                    except ValueError as error:
                        raise ValueError(
                            f"Line {line_number}: {error}"
                        )

        except FileNotFoundError:
            raise FileNotFoundError(
                f"File not found: {filename}"
            )

        # Replace the real list only after the entire file succeeds.
        # Loading selects a new process set; it does not merge two sets.
        self.pcb_list = temporary_manager.pcb_list

        # The interface uses this count in its load-success message.
        return len(self.pcb_list)

    def save_to_file(self, filename, overwrite=False):
        """Writes loadable records; existing files require overwrite=True."""

        # Check every record before opening a destination. Values may have
        # changed since creation, so saving checks both individual and shared rules.
        checked_manager = PCBManager()
        # This separate list holds output strings, not PCBs. Building it first
        # lets validation finish before we create or replace the destination.
        lines = []
        for pcb in self.pcb_list:
            if not isinstance(pcb, PCB):
                raise ValueError("Only PCB objects can be saved.")
            pcb.validate()
            checked_manager.add_pcb(pcb)

            # Keep the loader's six-field order. \n ends each record on its own line;
            # table headings and debugging descriptions do not belong in the file.
            lines.append(
                f"{pcb.process_id} {pcb.memory} {pcb.arrival_time} "
                f"{pcb.cpu_required} {pcb.quantum} "
                f"{pcb.context_switch_penalty}\n"
            )

        # Path makes folder and filename operations easier to read.
        destination = Path(filename)
        if destination.is_dir():
            raise IsADirectoryError("Choose a file name, not a directory.")

        if not overwrite:
            # Mode x creates a new file, raising FileExistsError if it already exists.
            # The interface uses that error to request overwrite confirmation.
            with open(destination, "x", encoding="utf-8") as file:
                file.writelines(lines)
        else:
            # For overwriting, write a temporary file beside the destination.
            # The existing save remains available until the replacement is ready.
            temporary_path = None
            try:
                # delete=False keeps the temporary file after closing so it can be moved.
                with NamedTemporaryFile(
                    mode="w", encoding="utf-8", dir=destination.parent,
                    prefix=".pcb-save-", suffix=".tmp", delete=False
                ) as file:
                    temporary_path = Path(file.name)
                    file.writelines(lines)

                # Replace the destination only after the full temporary file is closed.
                # Keeping both paths on the same disk allows this replacement as one step.
                os.replace(temporary_path, destination)
            # finally runs after success or failure. missing_ok allows for the
            # temporary path already being moved by os.replace().
            finally:
                if temporary_path is not None:
                    temporary_path.unlink(missing_ok=True)

        # An empty collection saves an empty file and returns zero.
        return len(lines)

    def get_pcb(self, process_id):
        """Finds a process by ID, or raises an error if the ID is missing."""
        # This is a linear search: inspect records until an ID matches.
        # An ID is a stored value, not a list index. Process 20 could be at index 0.
        for pcb in self.pcb_list:
            if pcb.process_id == process_id:
                return pcb
        raise ValueError(f"Process ID {process_id} was not found.")

    def update_pcb(self, process_id, replacement):
        """Checks a replacement PCB before changing the original record."""
        original = self.get_pcb(process_id)
        if not isinstance(replacement, PCB):
            raise ValueError("The replacement must be a PCB object.")
        # Recheck the replacement in case it was changed after being constructed.
        replacement.validate()

        # Build the candidate collection separately. A failed check must not
        # leave the real collection partly changed.
        temporary_manager = PCBManager()
        for pcb in self.pcb_list:
            # is compares the objects themselves. Leave out the old record so
            # keeping its ID does not look like a duplicate.
            if pcb is not original:
                temporary_manager.add_pcb(pcb)
        # Check against the other PCBs, including when editing the first record.
        temporary_manager.add_pcb(replacement)

        # Replace in place so the process stays at the same position in the list.
        index = self.pcb_list.index(original)
        self.pcb_list[index] = replacement

    def remove_pcb(self, process_id):
        """Removes the selected process without changing the other IDs."""
        pcb = self.get_pcb(process_id)
        # Other IDs stay unchanged; a removed ID can be used again.
        self.pcb_list.remove(pcb)

    def get_pcbs(self):
        """Returns the current list for display and other menu operations."""

        # This returns the actual list, not a copy. Another variable can refer
        # to the same list; changing it directly would bypass manager checks.
        # Menu code therefore uses manager methods for changes.
        return self.pcb_list
