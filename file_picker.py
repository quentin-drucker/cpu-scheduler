"""Lets the user choose a data file without typing its full path each time."""

from pathlib import Path
import cli_style as ui
from data_paths import DATA_FOLDER, resolve_data_path


# The shared DATA_FOLDER is based on the project location, not the terminal.
FILES_PER_PAGE = 9


def choose_data_file(data_folder=None, pcb_count=None):
    """Returns a selected path, or None if cancelled. Tests can supply a folder."""

    if data_folder is None:
        data_folder = DATA_FOLDER

    # Carry a message onto the next screen so clearing does not hide an error.
    notice = ""

    try:
        # Scan again each time the picker opens, so new saved files appear.
        # Only text files directly in this folder belong in the numbered list.
        # This list holds Path objects (file locations), not file contents or PCBs.
        files = [
            path for path in Path(data_folder).iterdir()
            if path.is_file() and path.suffix.lower() == ".txt"
        ]
        # The lambda supplies a sorting key: ignore case first, then use the
        # original name to keep ordering consistent when names differ only by case.
        files.sort(key=lambda path: (path.name.lower(), path.name))
    # If listing fails, manual entry and cancel should still be available.
    except OSError as error:
        notice = f"Could not list the data folder: {error}"
        # An empty list still leaves manual entry and cancel available.
        files = []

    # Adding eight before integer division rounds up for a partial page.
    # At least one page is needed for manual entry and cancel, even with no files.
    page_count = max(1, (len(files) + FILES_PER_PAGE - 1) // FILES_PER_PAGE)
    page = 0

    while True:
        # page starts at zero. This slice selects at most nine files for that page.
        # Slicing makes a new list of references to the selected Path objects;
        # it does not remove entries from the full files list.
        start = page * FILES_PER_PAGE
        page_files = files[start:start + FILES_PER_PAGE]
        ui.screen(f"Data Files — Page {page + 1} of {page_count}", pcb_count)
        if notice:
            print(ui.styled(notice, "warning"))
            notice = ""

        if not files:
            print("No .txt files are available in the data folder.")

        # Display numbers start at 1 again on each page.
        for number, path in enumerate(page_files, start=1):
            ui.option(number, path.name)

        if page < page_count - 1:
            ui.option("N", "Next page", "warning")
        if page > 0:
            ui.option("P", "Previous page", "warning")
        ui.option("M", "Enter a file name or path", "warning")
        ui.option("C", "Cancel loading", "warning")
        # Ignore surrounding spaces and accept either uppercase or lowercase letters.
        choice = ui.ask("Choose a file or option: ").strip().upper()

        if choice == "C":
            return None

        if choice == "M":
            print("Example: phase2_official (.txt and data/ are optional).")
            # Use the same name rules as Save. Explicit paths still let the
            # user choose another folder, while short names use data.
            filename = ui.ask("Enter file name: ").strip()
            if filename:
                try:
                    return resolve_data_path(filename, data_folder)
                except ValueError as error:
                    notice = f"Error: {error}"
            else:
                notice = "Error: A file name is required."

        elif choice == "N":
            if page < page_count - 1:
                page += 1
            else:
                notice = "Already on the last page."

        elif choice == "P":
            if page > 0:
                page -= 1
            else:
                notice = "Already on the first page."

        # Accept only a number actually shown on this page. Subtract 1 to find
        # its list position; the loader still checks the selected file's contents.
        elif choice in [str(number) for number in range(1, len(page_files) + 1)]:
            return page_files[int(choice) - 1]

        else:
            notice = "Error: Choose a displayed number, N, P, M, or C."
