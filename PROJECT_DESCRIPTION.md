# COM326 — Process Manager and CPU Scheduler

[Phase 1 walkthrough](PHASE1_DESCRIPTION.md) | [Phase 2 walkthrough](PHASE2_DESCRIPTION.md) | [Test evidence](evidence/phase2/README.md)

This project keeps process records and calculates how a single CPU would run them. Phase 1 provides the process manager. Phase 2 adds First-Come, First-Served (FCFS) and Shortest-Job-First (SJF) scheduling. It is a simulation: it calculates clock times rather than launching real operating-system processes.

Both phases are implemented in one application. All **87 automated tests pass**, including the original Phase 1 coverage. The official Phase 2 data produces average turnaround times of **4.40 cycles for FCFS** and **4.20 cycles for SJF**. The separate phase guides explain which work belongs to each phase.

## Start here

Extract the project ZIP and open a terminal in the folder containing `main.py`. Run:

```bash
python3 main.py
```

The application and tests use the Python standard library; no extra package installation is needed. Python 3.8 or later supports the features used here.

| Main-menu choice | Action | Introduced in |
| --- | --- | --- |
| 1 | Load a file, replacing the current process set only after validation succeeds. | Phase 1 |
| 2 | View all six fields of the current records. | Phase 1 |
| 3 | Add a process. | Phase 1 |
| 4 | Save the current definitions; confirm before overwriting. | Phase 1 |
| 5 | Edit one field of a process, keeping the original if validation fails. | Phase 1 |
| 6 | Remove a process after confirmation. | Phase 1 |
| 7 | Exit. | Phase 1 |
| 8 | Choose FCFS or SJF and display the calculated schedule. | Phase 2 |

Exit stays at 7 to preserve the existing controls. To try Phase 2, choose **1 → M**, enter `phase2_official`, and then use **8 → 1** for FCFS or **8 → 2** for SJF. In an interactive terminal, press Enter after each action to return to the menu. **C** cancels algorithm selection. An empty collection gives a message instead of a blank schedule.

Scheduling reads the current records, so a later edit, addition, removal, or load changes the next run. You can run both algorithms without reloading. Each run leaves the records unchanged; Save still writes only the process definitions.

## Easier manual loading and saving

Both **Load → M** and **Save** accept the same short names:

| What you type | File used inside the project |
| --- | --- |
| `phase2_official` | `data/phase2_official.txt` |
| `phase2_official.txt` | `data/phase2_official.txt` |
| `data/phase2_official` | `data/phase2_official.txt` |
| `data/phase2_official.txt` | `data/phase2_official.txt` |

A name by itself goes in the project's `data` folder. The `data/` prefix also refers to that same folder, even if the terminal starts elsewhere. If no extension is supplied, `.txt` is added. Existing extensions such as `.TXT` or `.dat` are preserved.

Explicit paths still work: `other/example` means `other/example.txt` relative to the terminal's current folder; `./example` explicitly selects that current folder. Absolute paths and `~/Documents/example` keep their specified locations. Parent folders must already exist. A blank name or a path ending in `/` is rejected; existing directories remain directory errors.

The interface shows **Loading from:** or **Saving to:** with the chosen location. The same overwrite confirmation applies regardless of which spelling reaches the existing file. The numbered picker remains available, and manager methods used directly in Python continue accepting exact paths without applying shorthand.

### Try the filename shortcuts

1. Run `python3 main.py`. Choose **1 → M**, enter `phase2_official`, and check that five records load.
2. Repeat with `phase2_official.txt`, `data/phase2_official`, and `data/phase2_official.txt`. Each should show the same location and five records.
3. Choose **4. Save**, enter `my_phase2_copy`, and check the destination is `data/my_phase2_copy.txt`.
4. Save again as `data/my_phase2_copy.txt`. Choose **N** at the overwrite prompt to confirm that cancellation protects the saved copy. Repeat and choose **Y** if you want to test confirmed replacement.
5. Load the copy using `my_phase2_copy` or select it from the numbered picker. Try a nonexistent name to see the normal file-not-found message without losing the current records.

Use a fresh copy name if `my_phase2_copy.txt` already exists. Do not overwrite the supplied official dataset for this check.

## What each phase contributed

| Area | Phase 1 | Phase 2 |
| --- | --- | --- |
| PCB (Process Control Block) | A record with six named integer fields and individual checks. | Reuses arrival time and CPU required, which were already stored in this implementation. |
| Process collection | A list with unique IDs, shared-value checks, loading, editing, removal, and saving. | Supplies the current records to the scheduler without changing their order or values. |
| User interface | Menu, file picker, colors, PCB table, narrow-window fallback, and pauses. | Algorithm selection, schedule table, averages, Phase 2 heading, and shared filename shortcuts for manual Load and Save. |
| Scheduling | No simulated execution. | FCFS and SJF, idle gaps, start/finish times, turnaround, and average turnaround. |
| Verification | 58 original tests and three supplied datasets. | 29 additional tests, the revised official dataset, and three small demonstration datasets. |

The [Phase 1 guide](PHASE1_DESCRIPTION.md) explains the retained process-management features and labels the original menu and test counts as historical. Its code links open the current files. The [Phase 2 guide](PHASE2_DESCRIPTION.md) identifies new functions and explains their calculations with examples.

## How the files fit together

| File | Responsibility |
| --- | --- |
| [pcb.py](pcb.py) | Stores one process and checks its individual fields. |
| [pcb_manager.py](pcb_manager.py) | Manages the list, collection checks, loading, saving, editing, and removal. |
| [main.py](main.py) | Collects menu input, calls the manager or scheduler, and reports results. |
| [scheduler.py](scheduler.py) | Calculates FCFS/SJF results and average turnaround. It does not print, prompt, or save. |
| [cli_style.py](cli_style.py) | Formats screens, PCB/schedule tables, messages, and pauses. |
| [data_paths.py](data_paths.py) | Shared short-name and optional-extension rules for manual Load and Save. |
| [file_picker.py](file_picker.py) | Lists files under `data/`, nine at a time, and supports manual paths. |
| [tests/](tests/) | Checks Phase 1 behavior, scheduling calculations, display, and menu integration. |

For example, choosing SJF follows this path: `main.py` gets the current list from the manager, `scheduler.py` calculates the run, and `cli_style.py` displays the returned rows. The manager's saved data does not become a running queue. The scheduler uses temporary lists to decide who is ready and who has finished.

## Process data and rules

Each nonblank input line contains six integers in this order:

```text
process_id memory arrival_time cpu_required quantum context_switch_penalty
0          2000   0            2            3       1
```

The first line above explains the fields; actual loadable files contain only the numeric records. Load [data/phase2_official.txt](data/phase2_official.txt), not the explanatory Moodle handout.

- IDs must be unique integers. Zero and negative IDs are allowed; IDs are labels, not list positions or priorities.
- Memory, CPU required, quantum, and context-switch penalty must be positive integers.
- Arrival time must be an integer at least zero.
- All processes in a set share the same quantum and penalty. The first accepted record establishes them.
- Total memory is not limited in this phase, following the official test-data handout.

Loading and editing validate a candidate set before replacing the original. Saving rechecks the data, writes the same six fields, and requires confirmation before replacing an existing file. The existing detailed explanations are in the Phase 1 guide.

For Phase 2, **non-preemptive** means that a selected process finishes before another starts. Quantum does not split its CPU time, and context-switch penalties add no time. FCFS uses arrival order. SJF chooses the shortest job that has already arrived. Ties use the documented [Phase 2 rules](PHASE2_DESCRIPTION.md#choosing-the-next-process).

## Terminal behavior

The schedule shows execution order, ID, arrival, CPU required, start, finish, and turnaround, followed by the average. Times are CPU clock cycles. Narrow terminals use labeled records instead of wrapping table columns.

The Phase 2 guide also includes [worked Gantt charts and calculations](PHASE2_DESCRIPTION.md#worked-scheduling-timelines-and-performance-measures) for both algorithms, with explanations of waiting time and throughput alongside the required turnaround measures.

The normal interface pauses after an action so the result can be read. Colors require both input and output to be connected to a terminal, `TERM` not to be `dumb`, and `NO_COLOR` to be unset. Use `NO_COLOR=1 python3 main.py` to disable colors. Redirected input or output disables colors, screen clearing, and extra pauses. Setting `CLEAR_SCREENS = False` in `cli_style.py` retains earlier screens. Very narrow terminals can still wrap longer explanation sentences; the result fields remain present.

## Verification

Run from the project root:

```bash
python3 -m unittest discover -s tests -v
```

The completed implementation passes **87 test methods**:

| Test file | Count | Main coverage |
| --- | ---: | --- |
| `test_requirements.py` | 12 | Phase 1 records, validation, loading, adding, and viewing. |
| `test_saving.py` | 17 | Save/reload, overwrite handling, failures, and existing menu flow. |
| `test_editing.py` | 12 | Editing, removal, cancellation, and preservation after rejected changes. |
| `test_data_paths.py` | 6 | All four filename forms through load/save, explicit paths, other working directories, overwrite protection, and invalid input. |
| `test_file_picker.py` | 10 | File listing, navigation, manual paths, and errors. |
| `test_cli_style.py` | 9 | Existing terminal behavior plus wide/narrow scheduling tables and large values. |
| `test_scheduler.py` | 14 | Exact schedules, arrivals, ties, idle time, non-preemption, repeatability, and unchanged records. |
| `test_scheduling_ui.py` | 7 | Algorithm selection, current-data changes, full menu runs, and pause/result feedback. |

Real interactive checks cover the official runs, result pauses, unchanged View data, and narrow/no-color output. [Captured CLI evidence](evidence/phase2/README.md) records actual program output and explains how to reproduce it. See the Phase 2 guide for the official calculations and demonstration steps.

## Assignment sources and submission

The current specification and revised handout are local:

- [Phase 2 instructions](Assignment%20Specifications%20for%20Phase%202/Instructions%20-%20Project%20Phase%202.pdf)
- [Revised official test-data handout](Assignment%20Specifications%20for%20Phase%202/From%20moodle%20-%20Project%20Phase%202%20Official%20Test%20Data%20File.txt)

The application follows the handout's rules: matching quantum values, non-preemptive algorithms, ignored switch penalties, and plenty of memory.

The [evidence index](evidence/phase2/README.md#screenshot-checklist) lists the 16 captured terminal screenshots. Their completed report includes actions, expected results, and observed results. The worked charts explain the calculations; the screenshots document actual application runs.

The intended outer submission ZIP has four deliverables, following the Phase 1 submission structure:

1. **Coversheet List Of Contributors.pdf:** the standalone author/contributor statement.
2. **QD_Phase 2/** or **QD_Phase 2.zip:** the complete runnable project, with the contents listed below. Preserve the folder structure so data files, tests, and documentation links work after extraction.
3. **Visual Showcase and Documentation/**: the completed `Phase 2 Screenshot Documentation Report.pdf` and a `Screenshots/` folder containing the actual captures. The report labels each figure and explains its input, expected result, observed result, and purpose.
4. **Phase 2 Project Overview.pdf:** the standalone explanation of the PCB, main data structures, architecture, and scheduling implementation.

The screenshot report is complete in both Word and PDF form. Keep editable Word files as working copies and use the final PDFs for submission. The standalone coversheet belongs outside the runnable project; omit its working Markdown copy, `PHASE2_COVERSHEET.md`, from the code package. Screenshot images and their report belong together in `Visual Showcase and Documentation/` and need not be duplicated inside the code package.

### Recommended code-package contents

| Include | Reason |
| --- | --- |
| All seven application files: `main.py`, `pcb.py`, `pcb_manager.py`, `scheduler.py`, `cli_style.py`, `file_picker.py`, and `data_paths.py` | These files work together to run the application. |
| `PROJECT_DESCRIPTION.md`, `PHASE1_DESCRIPTION.md`, and `PHASE2_DESCRIPTION.md` | Startup instructions, the retained Phase 1 features, and the Phase 2 explanation. |
| `tests/` containing the eight `test_*.py` files | Lets the reader rerun the 87 automated tests. Omit its cache folder. |
| `data/` containing the nine files listed below | Supplies the test inputs and documented examples. |
| `docs/phase2-scheduling-gantt.svg` | The Phase 2 guide embeds and links to this worked chart. |
| `evidence/phase2/` | Contains the linked test explanations, text transcripts, replay inputs, and saved-data example. It supplements the separate screenshot report. |
| Both `Assignment Specifications for Phase 1/` and `Assignment Specifications for Phase 2/`, each with its PDF and test-data TXT file | Keeps the original requirements and data references available through the guides' links. These are reference materials, not runtime dependencies. |

Keep these files in `data/`:

- `dataset1.txt`, `dataset2.txt`, and `dataset3.txt`: the original Phase 1 sets, also used by automated tests.
- `invalid_data_test.txt`: the deliberately malformed file described in the Phase 1 guide.
- `phase2_official.txt`: the unchanged numeric records from the Phase 2 handout.
- `phase2_idle.txt`, `phase2_nonpreemptive.txt`, and `phase2_ties.txt`: the additional scheduling cases used by tests and evidence.
- `phase2_submission_demo.txt`: the saved result of the screenshot editing demonstration, with process 0's CPU requirement changed to 1.

The older saved examples `phase1_demo.txt`, `phase1_demo2.txt`, `saved_processes.txt`, `saved_processes2.txt`, and `test2.txt` can be left out of the submission copy. The automated tests and documented Phase 2 runs do not load them. Earlier captures may show them in the file picker; the picker numbers can change when files are omitted, so the walkthroughs select files by name.

Leave `phase2_plan.md`, `PHASE2_COVERSHEET.md`, and the duplicate `screenshots/` folder out of the code package. Also exclude all `__pycache__/` folders, `.pyc` files, `.DS_Store` files, `__MACOSX/` folders, Word lock files whose names begin with `~$`, and temporary placeholder notes. Python recreates its cache files when needed; they are not part of the source. Apply these exclusions to the submission copy while keeping any useful working materials in the development folder.
