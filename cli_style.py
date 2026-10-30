"""Keeps colors, table formatting, and screen behavior in one place."""

import os
import shutil
import sys
import textwrap


# Theme settings live here so the screens keep the same appearance.
PROJECT_TITLE = "\n\n\nCOM326 | PROJECT PHASE 3"
# These are terminal color codes. The leading 1 requests bold text.
# This dictionary looks up a color-code string by a readable name such as "error".
COLORS = {
    "title": "1;36", "heading": "1;34", "success": "1;32",
    "error": "1;31", "warning": "1;33", "muted": "90",
    "prompt": "1;36", "text": "0", "schedule": "1;35"
}
CLEAR_SCREENS = True
# The menu reads this after an action to display its most recent outcome.
last_result = ""
# Each entry gives the PCB attribute, visible label, and minimum column width.
# A list keeps column order, and each tuple groups one column's three settings.
# This describes the table layout; it is not another collection of process data.
PCB_COLUMNS = [
    ("process_id", "ID", 6), ("memory", "Memory", 10),
    ("arrival_time", "Arrival", 10), ("cpu_required", "CPU Required", 15),
    ("quantum", "Quantum", 10), ("context_switch_penalty", "CS Penalty", 12)
]


def interactive():
    """Checks whether input and output are connected to a real terminal."""

    # isatty() checks for a terminal. Tests and redirected output should
    # not clear screens or stop to request an extra Enter.
    return sys.stdin.isatty() and sys.stdout.isatty()


def terminal_effects():
    """Allows screen effects only when the terminal can support them."""

    # TERM=dumb describes a terminal without these screen effects.
    return interactive() and os.environ.get("TERM") != "dumb"


def styled(text, tone="text"):
    """Adds the chosen color when enabled; otherwise returns plain text."""

    # NO_COLOR lets the user disable color without changing the code.
    if terminal_effects() and "NO_COLOR" not in os.environ:
        # \033 begins a terminal command; the final 0m resets the color
        # so following text does not accidentally keep the previous style.
        return f"\033[{COLORS[tone]}m{text}\033[0m"
    return str(text)


def rule():
    """Prints a separator that fits within the terminal width."""

    width = min(78, shutil.get_terminal_size().columns)
    print(styled("-" * width, "muted"))


def heading(text):
    """Prints a section title with a separator underneath."""

    print(styled(text, "heading"))
    rule()


def option(key, label, tone="heading"):
    """Formats a numbered or lettered menu choice."""

    print(styled(f"{key}. {label}", tone))


def ask(prompt):
    """Uses the shared prompt color and returns the text entered."""

    return input(styled(prompt, "prompt"))


def pcb_table(pcbs):
    """Displays all six values in columns, or vertically in a narrow window."""

    # Use the largest of the minimum width, heading width, and value widths.
    # getattr reads a field by name; the extra two spaces separate columns.
    # The default of zero also allows an empty list.
    # widths is a list of integers in the same column order as PCB_COLUMNS.
    widths = [max(width, len(label) + 2,
                  max((len(str(getattr(pcb, name))) + 2 for pcb in pcbs), default=0))
              for name, label, width in PCB_COLUMNS]
    # If columns would wrap, show labeled fields one record at a time.
    if sum(widths) > shutil.get_terminal_size().columns:
        for pcb in pcbs:
            for name, label, width in PCB_COLUMNS:
                print(f"{styled(label, 'heading')}: {getattr(pcb, name)}")
            rule()
        return

    # zip pairs each column with its calculated width. The < formatting
    # left-aligns the text, and join combines the pieces into one line.
    labels = "".join(f"{label:<{width}}"
                     for (_, label, _), width in zip(PCB_COLUMNS, widths))
    print(styled(labels, "heading"))
    rule()
    for pcb in pcbs:
        row = "".join(f"{getattr(pcb, name):<{width}}"
                      for (name, _, _), width in zip(PCB_COLUMNS, widths))
        print(row)
    rule()


# The per-process result values, in display order, with their short labels.
RESULT_COLUMNS = [
    ("process_id", "ID"), ("arrival_time", "Arrival"), ("cpu_required", "CPU"),
    ("completion_time", "Completion"), ("turnaround_time", "Turnaround")
]


def timeline(slices):
    """Prints the run as one wrapped line of times: 0 CS 1 P0 4 CS 5 P1 8 ..."""

    # Only this function knows the timeline layout, so it can be swapped for
    # a different display later without touching the scheduler or the menu.
    # Each unit is one slice: an idle gap if the CPU waited, the penalty if
    # one was paid, then the process and the time it stopped.
    units = []
    last = 0
    for piece in slices:
        first_moment = piece["start_time"] if piece["switch_start"] is None else piece["switch_start"]
        unit = ""
        if first_moment > last:
            unit += f" idle {first_moment}"
        if piece["switch_start"] is not None:
            unit += f" CS {piece['start_time']}"
        unit += f" P{piece['process_id']} {piece['finish_time']}"
        units.append((unit, piece["finish_time"]))
        last = piece["finish_time"]

    # Break lines only between whole units, so a CS always stays with its run.
    # A new line repeats the last time printed so the reader keeps their place.
    width = min(78, shutil.get_terminal_size().columns)
    line, has_unit, last = "0", False, 0
    for unit, finish in units:
        if has_unit and len(line) + len(unit) > width:
            print(line)
            line = str(last)
        line += unit
        has_unit, last = True, finish
    # Plain text on purpose: the timeline is ASCII only, with no color codes.
    print(line)


def results_table(processes):
    """Shows each process's results sideways: one column per process."""

    # Sideways keeps a handful of processes compact; each row is one value.
    labels = ["Process"] + [label for name, label in RESULT_COLUMNS[1:]]
    rows = [[str(row[name]) for row in processes] for name, label in RESULT_COLUMNS]
    label_width = len("Turnaround") + 2
    # Every process column has the same width, set by the longest value.
    column = max((len(value) for row in rows for value in row), default=0) + 2

    if label_width + column * len(processes) > shutil.get_terminal_size().columns:
        # Too many processes to fit sideways: use one row per process instead.
        _upright_results(processes)
        return

    for index, (label, row) in enumerate(zip(labels, rows)):
        # The > formatting right-aligns numbers so their digits line up.
        values = "".join(f"{value:>{column}}" for value in row)
        if index == 0:
            print(styled(f"{label:<{label_width}}{values}", "heading"))
            rule()
        else:
            print(f"{styled(f'{label:<{label_width}}', 'heading')}{values}")
    rule()


def _upright_results(processes):
    """Shows one row per process, or labeled records in a narrow window."""

    labels = [label for name, label in RESULT_COLUMNS]
    # These are display strings; nothing is added to the saved PCB data.
    rows = [[str(row[name]) for name, label in RESULT_COLUMNS] for row in processes]

    # Include the headings and largest values when finding each column width.
    # This also handles long process IDs and large clock values.
    widths = []
    for index, label in enumerate(labels):
        value_width = max((len(row[index]) for row in rows), default=0)
        widths.append(max(len(label), value_width) + 2)

    if sum(widths) > shutil.get_terminal_size().columns:
        # Labeled records keep every value visible when columns would wrap.
        for row in rows:
            for label, value in zip(labels, row):
                print(f"{styled(label, 'heading')}: {value}")
            rule()
        return

    print(styled("".join(f"{label:<{width}}"
                         for label, width in zip(labels, widths)), "heading"))
    rule()
    for row in rows:
        print("".join(f"{value:<{width}}" for value, width in zip(row, widths)))
    rule()


def message(text, tone="text"):
    """Displays a result and remembers it for the next menu screen."""

    # global updates the module's shared result instead of creating a local one.
    global last_result
    last_result = text.strip()
    print(styled(text, tone))


def screen(section, count=None, previous=""):
    """Draws the project heading, current section, and available session details."""

    if CLEAR_SCREENS and terminal_effects():
        # Clear the visible screen and move the cursor to the top-left.
        # This does not request deletion of terminal scrollback.
        print("\033[2J\033[H", end="")
    print(styled(PROJECT_TITLE, "title"))
    summary = section
    if count is not None:
        summary += f"  |  Current PCBs: {count}"
    print(styled(summary, "heading"))
    rule()
    if previous:
        width = max(20, min(78, shutil.get_terminal_size().columns))
        # Wrap long previous-action messages so they stay readable.
        print(styled(textwrap.fill(f"Previous action: {previous}", width), "muted"))
        print()


def pause():
    """Keeps results visible until Enter is pressed in an interactive session."""

    # Leave time to read the result before the next screen replaces it.
    if interactive():
        ask("\nPress Enter to return to the menu...")
