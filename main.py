"""Runs the text menu and connects user choices to the PCB manager."""

from pcb import PCB
from pcb_manager import PCBManager
from file_picker import choose_data_file
from data_paths import resolve_data_path
from scheduler import schedule_fcfs, schedule_sjf, schedule_rr, average_turnaround
import cli_style as ui


def display_pcbs(manager):
    """Shows the current records, or a message if the list is empty."""

    # This is the manager's list, so display does not keep a second copy.
    pcbs = manager.get_pcbs()

    # Return early so an empty collection does not produce a blank table.
    if len(pcbs) == 0:
        ui.message("\nNo PCBs are currently loaded.", "warning")
        return

    ui.heading("\nCurrent PCB List")
    # Column spacing and narrow-window handling stay in the style file.
    ui.pcb_table(pcbs)

    print(f"Total PCBs: {len(pcbs)}")


def load_pcbs_from_input(manager):
    """Chooses a file and reports whether its records loaded successfully."""

    ui.heading("\nLoad PCB Data")

    # Choosing the path is separate from reading and validating its contents.
    filename = choose_data_file(pcb_count=len(manager.get_pcbs()))
    if filename is None:
        ui.message("\nLoading cancelled.", "warning")
        return

    try:
        print(f"Loading from: {filename}")
        number_loaded = manager.load_from_file(filename)

    # File problems, such as a missing path or denied permission, return to the menu.
    except OSError as error:
        ui.message(f"\nError: {error}", "error")
        return

    # Show the validation message instead of ending the program with a traceback.
    except ValueError as error:
        ui.message(f"\nError: {error}", "error")
        return

    ui.message(f"\nSuccessfully loaded {number_loaded} PCB(s).", "success")


def add_pcb_from_input(manager):
    """Collects six values and adds the PCB if all checks pass."""

    ui.heading("\nAdd New PCB")

    try:
        # Prompts return text. int() rejects non-integers, including blank input.
        process_id = int(ui.ask("Process ID: "))
        memory = int(ui.ask("Memory: "))
        arrival_time = int(ui.ask("Arrival time: "))
        cpu_required = int(ui.ask("CPU required: "))
        quantum = int(ui.ask("Quantum: "))
        context_switch_penalty = int(
            ui.ask("Context-switch penalty: ")
        )

    except ValueError:
        ui.message("\nError: All PCB fields must be integers.", "error")
        return

    try:
        # Creating the PCB checks its own values before the manager checks the set.
        pcb = PCB(
            process_id,
            memory,
            arrival_time,
            cpu_required,
            quantum,
            context_switch_penalty
        )

        # Use the manager so duplicate IDs and shared values are checked too.
        manager.add_pcb(pcb)

    # Show the validation message instead of ending the program with a traceback.
    except ValueError as error:
        ui.message(f"\nError: {error}", "error")
        return

    ui.message(f"\nProcess {process_id} added successfully.", "success")


def save_pcbs_from_input(manager):
    """Saves the current list, asking before replacing an existing file."""

    ui.heading("\nSave PCB Data")
    print("Example: my_processes (.txt and data/ are optional).")
    print("Existing files require overwrite confirmation.")
    # strip() removes spaces around the path; an empty path is rejected below.
    filename = ui.ask("Enter file name: ").strip()

    if filename == "":
        ui.message("\nError: A file name is required.", "error")
        return

    try:
        # Expand the user's short name before checking for an existing file,
        # so all accepted spellings get the same overwrite protection.
        filename = resolve_data_path(filename)
        print(f"Saving to: {filename}")
        # The inner try handles an existing file. The outer try handles errors
        # from either the first save or the confirmed overwrite.
        try:
            number_saved = manager.save_to_file(filename)
        except FileExistsError:
            print(ui.styled(f"File already exists: {filename}", "warning"))
            print(f"Replace its contents with the current {len(manager.get_pcbs())} PCB(s)?")
            # Only Y or yes confirms replacement. Empty input cancels.
            while True:
                choice = ui.ask("Overwrite? (Y/N, Enter to cancel): ").strip().upper()
                if choice in ["N", "NO", "C", ""]:
                    ui.message("Save cancelled. Existing file unchanged.", "warning")
                    return
                if choice in ["Y", "YES"]:
                    number_saved = manager.save_to_file(filename, overwrite=True)
                    break
                print(ui.styled("Error: Enter Y to overwrite, or N to cancel.", "error"))

    # File problems, such as a missing path or denied permission, return to the menu.
    except OSError as error:
        ui.message(f"\nError: Could not save PCB data: {error}", "error")
        return

    # Show the validation message instead of ending the program with a traceback.
    except ValueError as error:
        ui.message(f"\nError: {error}", "error")
        return

    ui.message(f"\nSuccessfully saved {number_saved} PCB(s) to {filename}.", "success")


def select_pcb_from_input(manager):
    """Finds a process by ID for editing or removal; None means no selection."""
    display_pcbs(manager)
    if len(manager.get_pcbs()) == 0:
        return None

    # Retry a missing or non-integer ID without changing the collection.
    while True:
        choice = ui.ask("Process ID (C to cancel): ").strip()
        if choice.upper() == "C":
            ui.message("Selection cancelled.", "warning")
            return None
        try:
            process_id = int(choice)
        except ValueError:
            ui.message("Error: Process ID must be an integer.", "error")
            continue
        try:
            return manager.get_pcb(process_id)
        except ValueError as error:
            ui.message(f"Error: {error}", "error")


def edit_pcb_from_input(manager):
    """Changes one field while keeping the original PCB until validation passes."""
    ui.heading("\nEdit PCB")
    pcb = select_pcb_from_input(manager)
    if pcb is None:
        return

    # This is a list of tuples. The list keeps the six menu fields in order;
    # each tuple groups an attribute name with its readable label.
    # A tuple is a fixed grouping: its items cannot be replaced individually.
    # These pairs describe the fields; the actual process values stay in pcb.
    fields = [
        ("process_id", "Process ID"),
        ("memory", "Memory"),
        ("arrival_time", "Arrival time"),
        ("cpu_required", "CPU required"),
        ("quantum", "Quantum"),
        ("context_switch_penalty", "Context-switch penalty")
    ]
    while True:
        print(f"\nEditing Process {pcb.process_id}")
        # getattr(pcb, attribute) reads the field whose name is stored as text.
        for number, (attribute, label) in enumerate(fields, start=1):
            ui.option(number, f"{label}: {getattr(pcb, attribute)}")
        choice = ui.ask("Choose a field 1-6 (C to cancel): ").strip().upper()
        if choice == "C":
            ui.message("Editing cancelled.", "warning")
            return
        if choice not in ["1", "2", "3", "4", "5", "6"]:
            ui.message("Error: Choose a field from 1 to 6, or C.", "error")
            continue

        # Menu numbers start at 1, but list positions start at 0.
        attribute, label = fields[int(choice) - 1]
        break

    while True:
        text = ui.ask(f"New {label} (C to cancel): ").strip()
        if text.upper() == "C":
            ui.message("Editing cancelled.", "warning")
            return
        try:
            value = int(text)
        except ValueError:
            ui.message("Error: The new value must be an integer.", "error")
            continue

        # Copy the values first so a rejected edit leaves the original PCB alone.
        # This dictionary stores each field name alongside its current value.
        # A dictionary uses keys instead of numbered positions, for example
        # values["memory"]. Updating this entry does not change pcb.memory.
        # Here the copied values are integers, so no nested objects need copying.
        values = {name: getattr(pcb, name) for name, label in fields}
        values[attribute] = value
        try:
            # **values passes the dictionary entries as named arguments to PCB.
            replacement = PCB(**values)
            manager.update_pcb(pcb.process_id, replacement)
        except ValueError as error:
            ui.message(f"Error: {error}", "error")
            continue

        ui.message(f"\nProcess {replacement.process_id} updated successfully.", "success")
        print("Use Save to keep the revised list; overwriting requires confirmation.")
        return


def remove_pcb_from_input(manager):
    """Shows the selected PCB and asks before removing it."""
    ui.heading("\nRemove PCB")
    pcb = select_pcb_from_input(manager)
    if pcb is None:
        return

    # Show the complete record before asking for permission to remove it.
    print(f"\nSelected: {pcb}")
    while True:
        choice = ui.ask(f"Remove Process {pcb.process_id}? (Y/N): ").strip().upper()
        if choice in ["N", "NO", "C", ""]:
            ui.message("Removal cancelled.", "warning")
            return
        if choice in ["Y", "YES"]:
            manager.remove_pcb(pcb.process_id)
            ui.message(f"\nProcess {pcb.process_id} removed successfully.", "success")
            print("Use Save to keep the revised list; overwriting requires confirmation.")
            return
        ui.message("Error: Enter Y to remove, or N to cancel.", "error")


def ask_quantum(default):
    """Asks for this run's quantum; returns None if the user cancels."""

    # The data file's quantum is the default. A typed value only applies to
    # this run, so the saved records never change.
    while True:
        text = ui.ask(f"Time quantum in cycles (Enter for {default} from the data file, "
                      "C to cancel): ").strip()
        if text == "":
            return default
        if text.upper() == "C":
            return None
        try:
            quantum = int(text)
        except ValueError:
            quantum = 0     # not a whole number, so reject it below
        if quantum > 0:
            return quantum
        ui.message("Error: Quantum must be a whole number greater than 0.", "error")


def run_scheduler_from_input(manager):
    """Chooses FCFS, SJF or Round-Robin and shows its results for the current set."""

    # Read the current collection each time. An edit, addition, removal, or
    # new file load must be reflected in the very next scheduling run.
    pcbs = manager.get_pcbs()
    if not pcbs:
        ui.message("\nNo PCBs are currently loaded. Load a file or add a PCB first.",
                   "warning")
        return

    ui.heading("\nRun CPU Scheduler")
    ui.option("1", "First-Come, First-Served (FCFS)")
    ui.option("2", "Shortest-Job-First (SJF)")
    ui.option("3", "Round-Robin (RR)")
    ui.option("C", "Cancel", "warning")

    while True:
        choice = ui.ask("Choose an algorithm (1, 2, 3, or C): ").strip().upper()
        if choice == "C":
            ui.message("Scheduling cancelled.", "warning")
            return
        if choice == "1":
            name = "FCFS"
            schedule = schedule_fcfs(pcbs)
            break
        if choice == "2":
            name = "SJF"
            schedule = schedule_sjf(pcbs)
            break
        if choice == "3":
            # Every PCB shares one quantum, so the first record supplies the default.
            quantum = ask_quantum(pcbs[0].quantum)
            if quantum is None:
                ui.message("Scheduling cancelled.", "warning")
                return
            name = "Round-Robin"
            schedule = schedule_rr(pcbs, quantum)
            break
        ui.message("Error: Choose 1, 2, 3, or C.", "error")

    # Calculations stay in scheduler.py; the menu supplies the explanation,
    # and cli_style.py handles layout. All times are simulated clock cycles.
    penalty = schedule["penalty"]
    switches = schedule["context_switches"]
    ui.heading(f"\n{name} Schedule")
    print(f"Context-switch penalty: {penalty} cycle(s) before each process starts or resumes.")
    if schedule["quantum"] is not None:
        print(f"Time quantum: {schedule['quantum']} cycles.")
    print("Timeline in CPU clock cycles (CS = context-switch penalty):")
    ui.timeline(schedule["slices"])
    ui.results_table(schedule["processes"])
    average = average_turnaround(schedule["processes"])
    print(f"Average Turnaround Time: {average:.2f} cycles")
    # Every penalty paid counts as a switch, so count x penalty is the time they add.
    print(f"Context switches: {switches} ({switches} x {penalty} = {switches * penalty} "
          "penalty cycles, including the first start)")

    # The main loop remembers this result and supplies the usual Enter pause.
    # Scheduling does not save or change any of the original process records.
    ui.message(f"{name} completed for {len(schedule['processes'])} processes. "
               f"Average turnaround: {average:.2f} cycles. "
               f"Context switches: {switches}.", "success")


def display_menu():
    """Lists the available actions using the shared color settings."""

    ui.heading("\nChoose an action")
    ui.option("1", "Load PCB data from file", "heading")
    ui.option("2", "View PCB list", "heading")
    ui.option("3", "Add new PCB", "success")
    ui.option("4", "Save PCB data to file", "success")
    ui.option("5", "Edit a PCB", "warning")
    ui.option("6", "Remove a PCB", "error")
    ui.option("7", "Exit", "error")
    ui.option("8", "Run CPU scheduler", "schedule")


# ---------------------------------------------------------------------------------------
# ------------------------------------ MAIN LOOP ----------------------------------------
# ---------------------------------------------------------------------------------------


def main():
    """Keeps the same process collection available throughout the menu loop."""

    # Create the manager once, outside the loop, so menu choices share the same list.
    manager = PCBManager()

    previous = "Ready. Load a file or add a PCB to begin."
    # This dictionary maps input strings (keys) to action labels (values).
    # For example, actions["1"] is "Load". It supplies screen labels;
    # the if/elif statements below still decide which function to run.
    actions = {"1": "Load", "2": "View", "3": "Add", "4": "Save",
               "5": "Edit", "6": "Remove", "7": "Exit", "8": "Schedule"}

    while True:
        ui.screen("Process Manager", len(manager.get_pcbs()), previous)
        display_menu()

        choice = ui.ask("\nEnter choice: ").strip()

        # Clear the previous result so cancelled actions cannot reuse an old success.
        ui.last_result = ""
        action = actions.get(choice, "Menu")
        ui.screen(action, len(manager.get_pcbs()), previous)

        if choice == "1":
            load_pcbs_from_input(manager)

        elif choice == "2":
            display_pcbs(manager)
            ui.last_result = f"Displayed {len(manager.get_pcbs())} PCB(s)."

        elif choice == "3":
            add_pcb_from_input(manager)

        elif choice == "4":
            save_pcbs_from_input(manager)

        elif choice == "5":
            edit_pcb_from_input(manager)

        elif choice == "6":
            remove_pcb_from_input(manager)

        elif choice == "7":
            print("\nExiting Process Manager.")
            break

        elif choice == "8":
            run_scheduler_from_input(manager)

        else:
            ui.message("\nError: Please enter a choice from 1 to 8.", "error")

        # Keep the outcome for the next screen, then pause before clearing this one.
        previous = f"{action}: {ui.last_result or 'Cancelled; no changes made.'}"
        ui.pause()


# Run the menu only when this file is started directly. Tests can import it
# without opening an interactive menu.
if __name__ == "__main__":
    main()
