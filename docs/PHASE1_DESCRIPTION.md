# COM326 — Project 1, Phase 1: Code Walkthrough

[Overall project](../README.md) | [Phase 2 additions](PHASE2_DESCRIPTION.md)

This guide explains the process-management features introduced in Phase 1 and retained in the current application. Historical details are labeled below: Phase 1 had seven menu options and 58 tests; the current Phase 2 application has eight options and 87 tests. Source links open the current files. See the [Phase 2 guide](PHASE2_DESCRIPTION.md) for scheduling and the [overall guide](../README.md#easier-manual-loading-and-saving) for current filename shortcuts.

This program keeps a collection of Process Control Blocks (PCBs). Each PCB holds the six values describing one process. The text menu allows a process set to be loaded from a file, displayed, added to through manual input, edited, reduced by removing records, and saved for later use.

The four required features and the bonus save feature are implemented.

At a high level, `main.py` handles user interaction, while `PCBManager` keeps a Python list of PCB objects and handles loading, saving, editing, and removal. Each `PCB` stores one process's six values and checks its individual rules. The manager checks rules involving the whole collection, such as unique IDs and matching quantum values. `file_picker.py` handles file selection, and `cli_style.py` provides the shared appearance. This separation keeps the process data and validation independent of the menu's formatting.

## Quick definitions

- **Process:** A program in execution. In this project, each record describes a process; the application does not actually execute it.
- **PCB (Process Control Block):** A record that keeps information about one process together. This project's PCB stores six integers describing that process.
- **Process ID:** The integer that identifies a process. It must be unique within the current collection and is separate from the record's list position.
- **Memory requirement:** The amount of memory a process needs. Phase 1 stores this value but does not allocate memory.
- **Arrival time:** The time at which a process becomes available for scheduling; zero is allowed.
- **CPU required:** The total CPU processing time a process needs to finish.
- **Quantum:** The maximum CPU time allowed in one turn under time-slice scheduling. Phase 1 stores the setting without scheduling; Phase 2 also stores it, but its non-preemptive algorithms do not use time slices.
- **Context-switch penalty:** The time cost of switching the CPU from one process to another. This project stores that cost without simulating a switch.
- **PCB manager:** The object that maintains the current PCB list, checks collection rules, and handles loading, saving, editing, and removal.
- **Scheduling / ready queue:** Scheduling decides which process gets CPU time; a ready queue holds processes waiting for it. Neither behavior is implemented in Phase 1.
- **Saving / loading:** Saving writes records to a file for later use; loading reads and validates a file to replace the current collection.

## Project organization

| File | Purpose |
| --- | --- |
| [main.py](../main.py) | Handles the menu, prompts, table, and messages shown to the user. |
| [cli_style.py](../cli_style.py) | Central theme, colors, headings, table layout, screen clearing, prompts, and result pauses. |
| [file_picker.py](../file_picker.py) | Lists data files nine at a time and handles file selection, navigation, manual paths, and cancel. |
| [pcb.py](../pcb.py) | Defines one PCB and checks its individual values. |
| [pcb_manager.py](../pcb_manager.py) | Stores the PCB collection, checks rules involving other processes, and loads and saves files. |
| [tests/test_requirements.py](../tests/test_requirements.py) | Checks the four scored requirements, field validation through both input paths, and preservation after failed loads. |
| [tests/test_saving.py](../tests/test_saving.py) | Checks saving, reloading, file errors, and the menu flow using Python's built-in testing tools. |
| [tests/test_file_picker.py](../tests/test_file_picker.py) | Checks file selection, page boundaries, navigation, and loading through the picker. |
| [tests/test_editing.py](../tests/test_editing.py) | Checks field edits, removal, rejected changes, cancellation, and saving a revised collection. |
| [tests/test_cli_style.py](../tests/test_cli_style.py) | Checks terminal effects, plain output, result feedback, pauses, and narrow-window formatting. |
| [data/dataset1.txt](../data/dataset1.txt), [dataset2.txt](../data/dataset2.txt), [dataset3.txt](../data/dataset3.txt) | Hold the three separate sample process sets, with 4, 5, and 7 records. |
| [data/invalid_data_test.txt](../data/invalid_data_test.txt) | Provides a malformed record for testing the field-count check. |

The assignment is *Instructions - Project Phase 1.pdf*, and the field rules and original sample sets are in the supplied Moodle data document. Both are kept locally in `Assignment Specifications/Assignment Specifications for Phase 1/`, which is not published to the repository.

Source links below open the relevant files. Function names identify the code to look for without depending on line numbers that change when comments are added.

## Data structures used and why

A data structure is a way of organizing information so a program can work with it. The main design here is **a Python list of PCB objects**: each object groups the details of one process, and the list groups the processes in the current set. The smaller lists, tuples, and dictionaries in the interface help describe menus and formatting.

The process manager uses a list of records. Phase 1 has no scheduling queue. Phase 2 adds temporary lists for scheduling while retaining this same manager; those lists are explained in the [Phase 2 data-structure section](PHASE2_DESCRIPTION.md#data-structures-in-plain-language).

### One process: a PCB object

The `PCB` class in `pcb.py` defines what a process record contains. Calling `PCB(1, 2000, 0, 4, 3, 1)` creates one object with six named attributes:

| Attribute | Example | What it represents |
| --- | ---: | --- |
| `process_id` | 1 | The identifier used to find this process. |
| `memory` | 2000 | The process's stated memory requirement. |
| `arrival_time` | 0 | When the process arrives in the process description. |
| `cpu_required` | 4 | How much CPU time the process needs. |
| `quantum` | 3 | The time slice setting stored for the process set. |
| `context_switch_penalty` | 1 | The time cost of a context switch stored for the process set. |

All six values are integers. Phase 1 stores these descriptions; it does not allocate memory, advance a clock, or run a scheduler. The sample values above are taken from Dataset 1.

The class is the definition, and an object is one record created from that definition. Each PCB has its own attributes. Writing `pcb.memory` names the field directly, which is easier to explain than remembering that memory is at position 1 in a list of six numbers. Keeping the fields together also avoids maintaining six separate lists whose positions would have to stay matched.

`PCB` is a custom record represented by a Python object. It is not a dictionary, although the editing interface briefly uses a dictionary to prepare replacement values. The constructor calls `validate()` to reject invalid values when an object is created. Attributes can still be assigned afterward; the class does not automatically validate every later assignment. The normal Edit action creates and checks a replacement object instead.

### The current process set: a list of PCB objects

`PCBManager.__init__()` creates `self.pcb_list = []`. The brackets create an empty list. A Python list is ordered and mutable: entries have positions, and the program can add, replace, or remove them. Its size can grow as records are added.

Conceptually, a collection could look like this:

```text
manager.pcb_list
    index 0 -> PCB(process_id=20, memory=2000, ...)
    index 1 -> PCB(process_id=7,  memory=1000, ...)
```

An **index** is an entry's position, starting at zero. A **process ID** is a value inside the PCB. In this example, `pcb_list[0].process_id` is 20. Searching for process 20 does not mean reading `pcb_list[20]`; `get_pcb(20)` checks the stored IDs in a loop. Removing the first entry moves the second entry to index 0, but its process ID remains 7.

The list holds references to PCB objects. A reference lets the program reach the existing object instead of making another copy of its six fields. `get_pcbs()` returns the actual list, and `get_pcb()` returns an existing object. Therefore, the menu uses the manager's methods to make changes so it does not bypass collection checks. These are conventions of this program, rather than restrictions enforced by Python.

| Operation | How the list is used |
| --- | --- |
| Add | Check the existing records, then `append(pcb)` at the end. |
| View | Visit each PCB in list order. |
| Find | Compare each record's `process_id` with the requested ID. |
| Edit | Validate a replacement, then assign it to the original list position. |
| Remove | Find the PCB and remove it; later entries shift left. |
| Load | Build a separate valid list, then make it the current list. |
| Save | Visit records in list order and build a text line for each one. |

File order and manual addition order determine the manager's list order. The manager does not sort PCBs by ID, arrival time, or priority. Phase 2 calculates execution order separately without rearranging this stored list.

A list does not enforce unique IDs or matching quantum/penalty values. `add_pcb()` supplies those checks. The first record at index 0 provides the shared quantum and penalty for comparisons. Because the accepted records match, removing that first record still leaves the same shared values in the remaining records. If the list becomes empty, the next added record establishes the values again.

### Why a list is enough for this phase

The supplied datasets contain only 4, 5, and 7 processes. A list with straightforward loops keeps the implementation small and makes loading, displaying, editing, and saving easy to follow. A dictionary keyed by process ID could speed up finding records, but it is not needed for these small sets. Keeping both a list and a separate ID dictionary would also mean updating two collections whenever a record changes.

The tradeoff is that finding an ID or checking for duplicates may require visiting every record. Loading, saving, and editing also repeat these checks while validating a collection. This is manageable for the small supplied datasets and keeps the code easy to follow; a much larger process collection could benefit from a faster ID lookup.

### Temporary collections: check first, then commit the change

Loading creates a temporary `PCBManager` with its own empty list. Incoming lines become new PCB objects in that list. If any line fails validation, the method raises an error before replacing the current list. After every line passes, `self.pcb_list = temporary_manager.pcb_list` makes the validated list current. This assignment does not merge the lists or copy their entries one by one.

Editing follows the same idea. The menu prepares a new PCB, and `update_pcb()` builds a temporary list containing the other existing PCBs and the proposed replacement. Those existing PCBs are referenced, not copied or modified. Once the candidate collection passes, the replacement takes the original record's position in the current list. Reusing the manager's checks keeps the validation rules in one place.

Saving uses a temporary manager to check the current collection and a separate `lines` list containing formatted strings. This finishes data validation before opening the output file. These extra lists exist for the operation; they are not additional permanent process stores.

### Supporting lists, tuples, and dictionaries

A **tuple** groups related items in fixed positions, such as `("memory", "Memory")`. Unlike a list, a tuple does not allow its individual entries to be replaced. A **dictionary** associates a key with a value, such as `"memory": 2000`, so the value can be accessed by name instead of by numbered position.

| Location | Structure | Purpose |
| --- | --- | --- |
| `pcb_manager.py`: loader `values` | List of strings | Holds the six text fields from one line before conversion to integers. This is different from the list of complete PCBs. |
| `pcb_manager.py`: saver `lines` | List of strings | Holds one correctly formatted output line per process. |
| `main.py`: editor `fields` | List of two-item tuples | Keeps menu order and pairs each attribute name with its readable label. |
| `main.py`: editor `values` | Dictionary of names to integers | Prepares the proposed six values without changing the original PCB. |
| `main.py`: `actions` | Dictionary of strings to strings | Looks up a screen label from a menu choice, such as `"1"` to `"Load"`. |
| `file_picker.py`: `files` and `page_files` | Lists of `Path` objects | Hold available file locations and the current page's selection. They do not hold the files' contents. |
| `file_picker.py`: sort key | Two-item tuple | Sorts by lowercase filename first, then by original filename to break ties. |
| `cli_style.py`: `COLORS` | Dictionary of strings to strings | Looks up a terminal color code by a name such as `"error"`. |
| `cli_style.py`: `PCB_COLUMNS` | List of three-item tuples | Keeps column order and groups the attribute name, heading, and minimum width. |
| `cli_style.py`: `widths` | List of integers | Holds the calculated display width for each column. |

For an edit, `values = {name: getattr(pcb, name) for name, label in fields}` creates a dictionary containing the current six integers. `values[attribute] = value` changes only the selected dictionary entry. `PCB(**values)` passes those entries as named constructor arguments; for example, the `"memory"` entry supplies the `memory` argument. Because these values are integers, changing a dictionary entry does not modify the original PCB.

The picker uses a list slice to select one page. Slicing creates a new list containing references to the selected `Path` objects, leaving the full list intact. The table code uses `zip()` to pair each column description with its calculated width. Small lists such as `["Y", "YES"]` simply group accepted input responses for membership checks.

### Keeping the implementation appropriate for Phase 1

The core design uses two classes, built-in collections, and ordinary loops. The three main files have clear responsibilities: `main.py` asks the user what to do, `pcb.py` defines and checks one record, and `pcb_manager.py` manages the collection. No custom linked list, database, inheritance hierarchy, or scheduling framework is needed for the current operations.

For example, adding a process follows this path: `main.py` collects text and converts it to integers, `PCB(...)` checks the individual fields, and `manager.add_pcb(...)` checks the record against the current list before appending it. Viewing follows a shorter path: `main.py` gets that same list from the manager and passes it to `cli_style.py` for display. Loading reaches the same PCB and manager checks after `file_picker.py` supplies a file location. This is how the interface and data classes work together without putting user prompts inside the data classes.

The file picker, colors, removal option, and overwrite protection go beyond the minimum load/check/view/add functionality. They add code, but each serves an existing user-facing feature. In particular, temporary-file replacement during an overwrite protects an existing save if writing fails. The interface helpers are kept in their own files so the core process structure remains easy to identify. The data-structure explanation does not require a code redesign or new dependencies.

## Starting the program and storing the data

Run the following from the project folder in a terminal (Python 3.8 or later):

```bash
python3 main.py
```

In [main.py, `main()`](../main.py), one `PCBManager` is created before the menu loop. Keeping the same manager allows loaded and manually added records to stay available between menu choices. The `if`/`elif` blocks call the function for the selected option. Choosing Exit uses `break` to leave the loop; an unrecognized choice prints an error.

The Phase 1 menu options were **1. Load**, **2. View**, **3. Add**, **4. Save**, **5. Edit**, **6. Remove**, and **7. Exit**. These remain in the current application, which adds **8. Run CPU scheduler**.

In [pcb.py, `PCB.__init__()`](../pcb.py), each PCB stores `process_id`, `memory`, `arrival_time`, `cpu_required`, `quantum`, and `context_switch_penalty`. The constructor runs when a PCB is created and immediately calls `validate()`.

In [pcb_manager.py, `PCBManager.__init__()`](../pcb_manager.py), `self.pcb_list` starts as an empty Python list. Each list entry is a complete PCB object, keeping the six related values together. This list holds the current process set; it is not a scheduling queue.

## Requirement 1 — Load PCB data (25 pts)

The menu calls [main.py, `load_pcbs_from_input()`](../main.py). This function calls [file_picker.py, `choose_data_file()`](../file_picker.py) to select a path, then passes that path to the manager. The picker handles choosing a file; the manager handles reading and checking its contents.

The picker lists `.txt` files directly inside the project's `data` folder, sorted alphabetically without treating uppercase and lowercase differently. Subfolders are excluded. A file appearing here does not mean its contents are valid; the regular validation still runs when it is selected.

| Key | Action |
| --- | --- |
| **1–9** | Select the corresponding file on the current page. |
| **N** | Show the next nine files, when another page exists. |
| **P** | Return to the previous page, when available. |
| **M** | Type a file path manually, including files outside `data` or with other extensions. |
| **C** | Cancel loading and keep the current PCB collection. |

Letter choices accept either case. Numbers restart at 1 on each page, and the heading shows the current page and total pages. Invalid choices leave the picker open. A blank manual filename shows an error and returns to the file list.

In `choose_data_file()`, `FILES_PER_PAGE` sets the page size to nine. The `page` variable starts at zero, and `start = page * FILES_PER_PAGE` finds the first file for that page. The list slice `files[start:start + FILES_PER_PAGE]` selects only the visible files. This keeps the navigation separate from PCB validation.

The picker finds the project's `data` folder even when the program starts from another working directory. In Phase 1, `DATA_FOLDER` was defined in `file_picker.py` and manually entered relative paths started from the terminal's current folder. In the current application, `data_paths.py` supplies the folder and shared filename rules: a short name such as `dataset1` selects `data/dataset1.txt`; an explicit path such as `./example.txt` stays relative to the terminal's current folder. The list refreshes whenever Load is opened, so newly saved `.txt` files in `data` appear next time. Files added while the picker is already open appear after cancelling and reopening it.

An empty, missing, or unreadable data folder still leaves manual entry and cancel available. If a selected file disappears or contains invalid data, the loader reports the error and keeps the current collection.

[pcb_manager.py, `load_from_file()`](../pcb_manager.py) handles the actual reading:

1. Creates a temporary manager to hold the incoming records.
2. Opens the file using `with`, which closes it automatically afterward.
3. Reads each line and tracks its number with `enumerate(..., start=1)`.
4. Skips blank lines and uses `split()` to separate values at whitespace.
5. Requires exactly six fields and converts them with `int()`.
6. Creates a PCB and calls the temporary manager's `add_pcb()` to check it against the other incoming records.

For example, `1 2000 0 4 3 1` means process ID 1, memory 2000, arrival time 0, CPU required 4, quantum 3, and context-switch penalty 1. Input files contain records only, without headings such as “Data Set 1.”

The [replacement block](../pcb_manager.py) runs only after the entire file succeeds. This prevents a bad record near the end of a file from leaving the current collection partly replaced. A successful load replaces the old set because the supplied datasets are separate sets whose IDs restart.

The loader returns the number of records for the success message. Invalid record errors include a line number. The interface catches `OSError` for file problems, including missing files, directories, and denied permissions. It also catches `ValueError` for invalid data. Files are read using UTF-8, matching the save method.

## Requirement 2 — Check the data (25 pts)

Validation is divided between checks for one PCB and checks that need the whole collection.

[pcb.py, `PCB.validate()`](../pcb.py) checks the individual fields:

| Field | Individual rule |
| --- | --- |
| Process ID | Integer |
| Memory | Integer greater than 0 |
| Arrival time | Integer greater than or equal to 0 |
| CPU required | Integer greater than 0 |
| Quantum | Integer greater than 0 |
| Context-switch penalty | Integer greater than 0 |

Process IDs do not have a positivity check because the supplied rules require an integer and uniqueness, without stating that IDs must be positive.

[pcb_manager.py, `add_pcb()`](../pcb_manager.py) first checks that the supplied item is a PCB. The loop over existing records rejects duplicate IDs. The following two blocks compare quantum and context-switch penalty with the first PCB. This means the first accepted PCB establishes those values for the set. The final `append()` runs only after these checks succeed.

Both file loading and manual entry create a PCB and then use `add_pcb()`. This gives both entry methods the same validation rules. A failed check raises `ValueError`, which carries a message back to the interface for display.

Memory is stored and must be positive. The implementation does not enforce a total-memory limit or allocate memory. The Phase 2 test-data handout explicitly assumes plenty of memory.

## Requirement 3 — Show the PCB list (25 pts)

[main.py, `display_pcbs()`](../main.py) gets the current list through [pcb_manager.py, `get_pcbs()`](../pcb_manager.py). If the list is empty, it prints a message and returns.

Otherwise, the function calls `cli_style.pcb_table()` to print all six fields. The style module controls headings and column widths. Large values widen the columns; a window too narrow for the table uses labeled fields for each record instead. The final `len(pcbs)` in `display_pcbs()` shows the total number of records.

[pcb.py, `PCB.__str__()`](../pcb.py) provides the readable record description shown before removal. The menu's table uses `display_pcbs()` instead.

## Requirement 4 — Add a new PCB (25 pts)

[main.py, `add_pcb_from_input()`](../main.py) prompts for each of the six fields. Its first `try` block converts responses into integers. If conversion fails, it prints “All PCB fields must be integers” and returns to the menu.

The second `try` block creates the PCB and calls `manager.add_pcb(pcb)`. This checks the individual values, duplicate IDs, and shared quantum/penalty before adding the record. A validation error prints its message; a successful addition prints the process ID.

This function uses the same manager as file loading, so a loaded set can be extended manually. For example, after loading Dataset 1, entering `5`, `1000`, `4`, `3`, `3`, and `1` at the prompts adds Process 5 to that collection.

## Editing and removing current PCBs

Editing addresses the assignment's request to update active process information. Removal is an additional convenience for managing the current set.

Both options use [main.py, `select_pcb_from_input()`](../main.py) to show the current list and request a process ID. The ID identifies the process, rather than its position in the table. Unknown IDs and non-integer responses show errors and allow another attempt. An empty collection returns to the main menu without asking for an ID. **C** cancels selection.

### Editing one field

[main.py, `edit_pcb_from_input()`](../main.py) shows six numbered fields with their current values. Select one field, then enter its new integer value. **C** cancels at either prompt. Blank input, `cat`, `_`, and decimal values are rejected and leave the value prompt open. Blank input does not mean zero or silently change the field.

The function copies the current six values into a dictionary and replaces only the selected value. `PCB(**values)` passes these named values into a new PCB, which runs the existing individual validation. The original object is not changed during this step.

[pcb_manager.py, `update_pcb()`](../pcb_manager.py) finds the original through `get_pcb()`, rechecks the replacement, and adds the other PCBs to a temporary manager. It then checks the replacement against those records using `add_pcb()`. Leaving the original out of this check allows its ID to stay the same, but another process's ID is still rejected. Only after all checks pass does the replacement take the original's position in the list.

Memory, CPU required, quantum, and penalty must remain positive; arrival time must remain nonnegative. Quantum and penalty must also match the other processes. When only one PCB remains, either shared value can change to any positive integer because there are no other PCBs to disagree with it. The next added PCB must match the new values. Invalid edits preserve the original record and allow another attempt.

### Removing a process

[main.py, `remove_pcb_from_input()`](../main.py) displays the selected PCB and asks for confirmation. Only **Y** or **yes** removes it. **N**, **no**, **C**, or Enter cancels; other responses ask again. Letter commands accept either case.

[pcb_manager.py, `remove_pcb()`](../pcb_manager.py) finds the selected object with `get_pcb()` and removes it from the list. Other processes keep their IDs and order. A removed ID can be reused. Removing the last record leaves an empty collection, so the next PCB added establishes a new quantum and penalty.

### Revising a previously saved collection

Load the saved file, edit or remove the desired records, and use **4. Save** with the same filename. Confirm with **Y** to replace the saved contents, or use a new filename to keep both versions. Editing and removing affect the loaded collection only; they do not automatically change the original file. Exiting or successfully loading another set before saving discards these unsaved changes.

## Bonus Feature — Save and reload PCB data (+10 pts)

Menu option 4 calls [main.py, `save_pcbs_from_input()`](../main.py). This function asks for a filename, rejects a blank response, and calls the manager. If a file already exists, it shows the destination and current PCB count and asks whether to overwrite. Only **Y** or **yes** confirms; **N**, **no**, **C**, or Enter cancels without changing the file. Other responses ask again. Directories, missing folders, permission problems, and validation errors produce messages. Success is reported only after saving finishes.

[pcb_manager.py, `save_to_file()`](../pcb_manager.py) handles the file contents:

1. Rechecks each PCB and uses a temporary manager to recheck collection rules. This matters because PCB values can be changed after creation.
2. Builds one line per PCB in the same six-field order expected by the loader. Each line ends with a newline; no headings or debugging text are included.
3. By default, opens a new UTF-8 file using mode `"x"`, which refuses to overwrite an existing path. The interface catches that error to request confirmation. The parent folder must already exist.
4. After confirmation, the interface calls `save_to_file(filename, overwrite=True)`. This writes a temporary file in the destination folder, closes it, and then uses `os.replace()` to replace the destination. The original stays intact if writing or replacement fails. A `finally` block removes any leftover temporary file.
5. Returns the count after success. Saving leaves the current collection unchanged.

An empty collection produces an empty file and a count of zero. Loading that file replaces the current collection with an empty list. For a brand-new filename, a failed write may leave a partial new file. Confirmed overwrites use the temporary-file approach above to protect the existing save. Confirming an overwrite of an empty collection intentionally replaces the file with an empty one; the confirmation shows a count of zero.

This addresses both parts of the bonus: the current PCB list can be written to a file, and that file can be loaded through the existing import option. File handling stays in the manager and user interaction stays in `main.py`, so another interface could reuse the same save method later.

## Automated test coverage

Run the tests from the project folder:

```bash
python3 -m unittest discover -s tests -v
```

The Phase 1 suite contained **58 test methods**, listed below as the historical baseline. Running the command above in this Phase 2 project runs **87 tests**, including the retained Phase 1 coverage. The current counts are in the [overall verification table](../README.md#verification). Several methods use multiple cases to check each field or boundary value. Tests use temporary files for generated data and do not overwrite the supplied datasets.

| Test file | Phase 1 methods | Coverage |
| --- | ---: | --- |
| [test_requirements.py](../tests/test_requirements.py) | 12 | Exact sample records, replacement loading, field counts, integer conversion, numeric bounds, duplicate IDs, quantum/penalty consistency, manual addition, display, and failed-load preservation. |
| [test_saving.py](../tests/test_saving.py) | 17 | Save/reload round trips, exact format, overwrite confirmation/cancellation, fresh-process reload, empty lists, and file-error handling. |
| [test_editing.py](../tests/test_editing.py) | 12 | All editable fields, invalid changes, selection/cancellation, removal, and saving revised collections. |
| [test_file_picker.py](../tests/test_file_picker.py) | 10 | Filtering/sorting, page boundaries, navigation, manual paths, cancellation, and file/folder errors. |
| [test_cli_style.py](../tests/test_cli_style.py) | 7 | Color controls, plain output, screen clearing, result feedback, pauses, and narrow tables. |

Permission, disk-write, and replacement failures are simulated where needed so these cases can be checked without changing real permissions or filling a disk. The overwrite round-trip test starts a fresh Python process to confirm that edited and added records are read from the saved file.

## Central CLI style and screen flow

[cli_style.py](../cli_style.py) controls the appearance for both the main menu and the file picker. `PROJECT_TITLE`, `COLORS`, `PCB_COLUMNS`, and `CLEAR_SCREENS` are the main settings to change when adjusting the interface. No extra packages are required.

| Style | Used for |
| --- | --- |
| Bold cyan | Project title and input prompts |
| Bold blue | Headings, Load/View choices, and file choices |
| Bold green | Add/Save choices and successful actions |
| Bold yellow | Edit, navigation/cancel choices, and notices |
| Bold red | Remove/Exit choices and error messages |
| Gray | Separators and the previous-action summary |

`styled()` surrounds text with terminal color codes and resets the color afterward. `heading()`, `option()`, `ask()`, and `message()` provide shared formatting so individual menus do not need their own color codes. Labels and error text still convey meaning when colors are disabled.

`screen()` clears the visible terminal and draws the project title, current section, and PCB count. `main()` calls it when opening the menu or starting an action. The menu also shows the previous choice and its result, including failures and cancellations. The count is refreshed on each screen draw. The full PCB list remains available through View and during Edit/Remove selection.

After an action, `pause()` waits for Enter so results and tables can be read before returning to the menu. During multi-step entry, prompts remain together so the entered values and validation errors stay visible. The file picker redraws when navigating pages and carries any invalid-choice notice onto the next draw. Screen clearing leaves terminal scrollback available.

The style module checks whether input and output are connected to a terminal. Redirected output and automated tests receive plain text, with no screen clearing or extra Enter prompts. A terminal marked `TERM=dumb` also avoids color and clearing. `NO_COLOR` disables colors; setting `CLEAR_SCREENS = False` in the style file keeps earlier screens visible. There are no animation delays.

To see the styled interface, run in the VS Code integrated terminal or a normal terminal:

```bash
python3 main.py
```

The menu shows the current PCB count and the previous action result. Press Enter after an action to return to the menu.

To try the same interface without colors:

```bash
NO_COLOR=1 python3 main.py
```

## Phase 1 scope

Phase 1 stores and validates process definitions. Phase 2 adds simulated CPU scheduling, as described in the [Phase 2 guide](PHASE2_DESCRIPTION.md). The manager's PCB collection remains a list of records. Neither phase launches real processes, performs actual context switches, or allocates memory.

