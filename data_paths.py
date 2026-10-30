"""Applies the same convenient filename rules to manual loading and saving."""

from pathlib import Path


# Find the project's data folder from this file, not from where the terminal
# happened to start. Both the picker and Save use this same default location.
DATA_FOLDER = Path(__file__).resolve().parent / "data"


def resolve_data_path(filename, data_folder=None):
    """Turns a short name or explicit path into the file location to use."""

    text = str(filename).strip()
    if not text:
        raise ValueError("A file name is required.")

    folder = Path(data_folder) if data_folder is not None else DATA_FOLDER
    # expanduser allows a path such as ~/Documents/processes.txt.
    path = Path(text).expanduser()
    if not path.is_absolute() and path.parts and path.parts[0] == "data":
        # data/example and example both refer to this project's data folder.
        # Drop the existing data prefix so it is not added twice.
        path = folder.joinpath(*path.parts[1:])
    elif "/" not in text and not text.startswith("~") and text not in (".", ".."):
        path = folder / path
    # Other paths keep their location. For example, ./example is relative
    # to the terminal's current folder; /tmp/example is an absolute path.

    # Keep directory inputs as directories so the existing file operations
    # report an error instead of accidentally writing a nearby folder.txt.
    if text.endswith("/"):
        raise ValueError("Choose a file name, not a path ending in '/'.")
    if path.is_dir() or text in (".", ".."):
        return path

    # Add .txt only when no extension was supplied. An explicit .dat, .TXT,
    # or other extension stays as written; no second extension is added.
    if not path.suffix:
        path = path.with_suffix(".txt")
    return path
