# COM326 — Process Manager, CPU Scheduler and Memory Allocator

[Phase 1 walkthrough](docs/PHASE1_DESCRIPTION.md) | [Phase 2 walkthrough](docs/PHASE2_DESCRIPTION.md) | [Phase 3 walkthrough](docs/PHASE3_DESCRIPTION.md) | [Phase 4 walkthrough](docs/PHASE4_DESCRIPTION.md)

This project keeps process records and calculates how a single CPU would run them. Phase 1 provides the process manager. Phase 2 adds First-Come, First-Served (FCFS) and Shortest-Job-First (SJF) scheduling. Phase 3 adds Round-Robin (RR) scheduling with an adjustable time quantum, and applies and counts context-switch penalties in all three algorithms. Phase 4 adds contiguous memory allocation: a 15,000-location memory, First-Fit or Worst-Fit placement, merging of adjacent holes, and Compaction when needed. It is a simulation: it calculates clock times rather than launching real operating-system processes.

All four phases are implemented in one application. All **125 automated tests pass**, including the original Phase 1 coverage. On official Phase 4 Data Set 1, FCFS with either First-Fit or Worst-Fit averages **11.25 cycles**, with **one Compaction at cycle 11**. Process 3 (12000) waits for memory until then. The separate phase guides explain which work belongs to each phase.

## Start here

Clone the repository (or extract the project ZIP) and open a terminal in the folder containing `main.py`. Run:

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
| 8 | Choose FCFS, SJF or Round-Robin, then First-Fit or Worst-Fit, and display the timeline, run order with memory locations, memory events and Compactions, turnaround times and context switches. | Phase 2 (RR in Phase 3, memory in Phase 4) |

Exit stays at 7 to preserve the existing controls. To try Phase 4, choose **1 → M**, enter `phase4_set1` (or `phase4_set2`, `phase4_set3`), and then use **8**. Choose **1** for FCFS, **2** for SJF, or **3** for Round-Robin, then **1** for First-Fit or **2** for Worst-Fit. Round-Robin first asks for the time quantum: press Enter to keep the data file's value, or type a positive whole number to use it for that run only. In an interactive terminal, press Enter after each action to return to the menu. **C** cancels algorithm, quantum or memory-allocation selection. An empty collection gives a message instead of a blank schedule.

Scheduling reads the current records, so a later edit, addition, removal, or load changes the next run. You can run all three algorithms without reloading. Each run leaves the records unchanged; Save still writes only the process definitions.

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

| Area | Phase 1 | Phase 2 | Phase 3 | Phase 4 |
| --- | --- | --- | --- | --- |
| PCB (Process Control Block) | A record with six named integer fields and individual checks. | Reuses arrival time and CPU required, which were already stored in this implementation. | Adds `remaining_time`, the CPU time a process still needs (runtime state only, never saved). | Memory is now limited to 15000 or less (the whole memory). |
| Process collection | A list with unique IDs, shared-value checks, loading, editing, removal, and saving. | Supplies the current records to the scheduler without changing their order or values. | Unchanged. Scheduling works on copies, so the records are never modified. | Unchanged. |
| User interface | Menu, file picker, colors, PCB table, narrow-window fallback, and pauses. | Algorithm selection, schedule table, averages, Phase 2 heading, and shared filename shortcuts for manual Load and Save. | Round-Robin choice, quantum prompt, wrapped timeline string, sideways results table, and context-switch count. | Memory-allocation prompt, run-order table with memory locations, memory event log with Compactions, Memory and Location result rows. |
| Scheduling | No simulated execution. | FCFS and SJF, idle gaps, start/finish times, turnaround, and average turnaround. | One shared ready-queue loop for FCFS, SJF and Round-Robin, with the context-switch penalty paid before each start or resume. | A process may run only while it holds memory; waiting processes keep their queue place. |
| Verification | 58 original tests and three supplied datasets. | 29 additional tests, the revised official dataset, and three small demonstration datasets. | 13 more tests (100 in total), the official Phase 3 dataset, and updated expected values that include the penalty. | 25 more tests (125 in total) and the three official Phase 4 data sets. |

The [Phase 1 guide](docs/PHASE1_DESCRIPTION.md) explains the retained process-management features and labels the original menu and test counts as historical. Its code links open the current files. The [Phase 2 guide](docs/PHASE2_DESCRIPTION.md) identifies new functions and explains their calculations with examples. The [Phase 3 guide](docs/PHASE3_DESCRIPTION.md) explains Round-Robin, the penalty rules, and a worked trace of the official run. The [Phase 4 guide](docs/PHASE4_DESCRIPTION.md) explains memory allocation, hole merging, Compaction and a worked trace of Data Set 1.

## How the files fit together

| File | Responsibility |
| --- | --- |
| [pcb.py](pcb.py) | Stores one process and checks its individual fields. |
| [pcb_manager.py](pcb_manager.py) | Manages the list, collection checks, loading, saving, editing, and removal. |
| [main.py](main.py) | Collects menu input, calls the manager or scheduler, and reports results. |
| [scheduler.py](scheduler.py) | Calculates FCFS, SJF and Round-Robin schedules, context switches, and average turnaround, with memory allocation when a fit is given. It does not print, prompt, or save. |
| [memory_manager.py](memory_manager.py) | Tracks the 15000 locations as blocks and holes: First-Fit, Worst-Fit, release with hole merging, and Compaction. |
| [cli_style.py](cli_style.py) | Formats screens, the PCB table, the schedule timeline, run order, memory events and results table, messages, and pauses. |
| [data_paths.py](data_paths.py) | Shared short-name and optional-extension rules for manual Load and Save. |
| [file_picker.py](file_picker.py) | Lists files under `data/`, nine at a time, and supports manual paths. |
| [tests/](tests/) | Checks Phase 1 behavior, scheduling and memory calculations, display, and menu integration. |

For example, choosing Round-Robin follows this path: `main.py` gets the current list from the manager and asks for the quantum and the memory-allocation rule, `scheduler.py` calculates the run while a `MemoryManager` places each process, and `cli_style.py` displays the returned timeline and results. The manager's saved data does not become a running queue. The scheduler copies the records into its own ready queue to decide who runs next and who has finished.

## Process data and rules

Each nonblank input line contains six integers in this order:

```text
process_id memory arrival_time cpu_required quantum context_switch_penalty
0          2000   0            2            3       1
```

The first line above explains the fields; actual loadable files contain only the numeric records. Load [data/phase4_set1.txt](data/phase4_set1.txt), [phase4_set2.txt](data/phase4_set2.txt) or [phase4_set3.txt](data/phase4_set3.txt) (the three Phase 4 data sets), not the explanatory Moodle handout.

- IDs must be unique integers. Zero and negative IDs are allowed; IDs are labels, not list positions or priorities.
- Memory, CPU required, quantum, and context-switch penalty must be positive integers.
- Memory must be 15000 or less (Phase 4): a larger process could never be placed in memory.
- Arrival time must be an integer at least zero.
- All processes in a set share the same quantum and penalty. The first accepted record establishes them.

Loading and editing validate a candidate set before replacing the original. Saving rechecks the data, writes the same six fields, and requires confirmation before replacing an existing file. The existing detailed explanations are in the Phase 1 guide.

Phase 3 scheduling rules, in short:

- FCFS and SJF stay **non-preemptive**: a selected process runs to completion. Round-Robin gives each ready process up to one quantum, then moves it to the back of the ready queue if it still needs CPU time.
- The **context-switch penalty is paid before a process runs**, every time a process is started (including the very first one) or resumed. It applies to all three algorithms, so the Phase 2 averages change from 4.40/4.20 to 7.40/7.20 on the Phase 2 data.
- **No penalty** is paid when the same process simply keeps running after its quantum expires because no other process is waiting.
- When a new arrival and a quantum expiry happen at the same moment, the **new arrival joins the ready queue first**.
- Turnaround = Completion − Arrival, with all penalties included.

Phase 4 memory rules, in short (details in the [Phase 4 guide](docs/PHASE4_DESCRIPTION.md#memory-rules)):

- Memory has 15000 locations (0-14999). Each process gets one contiguous block of exactly its size when it arrives, and keeps it until it finishes.
- **First-Fit** uses the lowest hole that is large enough; **Worst-Fit** uses the largest hole (lowest address on a tie).
- A process that does not fit still joins the ready queue but is **skipped until it has memory**. Smaller processes that fit can run first.
- When a process finishes, its block becomes a hole and **adjacent holes are merged** at once.
- **Compaction** happens only when no single hole fits a waiting process but the free total does. It slides every block down to address 0 and costs no clock time.

FCFS uses arrival order. SJF chooses the shortest job that has already arrived. Ties use the documented [Phase 2 rules](docs/PHASE2_DESCRIPTION.md#choosing-the-next-process). The [Phase 3 guide](docs/PHASE3_DESCRIPTION.md#scheduling-rules) separates the rules confirmed by the assignment and professor from our own documented assumptions.

## Terminal behavior

Each run prints the penalty (and the quantum for Round-Robin) and the memory-allocation rule, then a timeline string such as:

```text
0 CS 1 P0 4 CS 5 P1 8 CS 9 P2 10 CS 11 P3 14 CS 15 P4 18 CS 19 P5 22
22 CS 23 P0 26 CS 27 P1 30 CS 31 P4 32 CS 33 P5 34 CS 35 P0 37 CS 38 P1 40
```

Read it left to right as clock times with what happened in between: `CS` is a context-switch penalty, `P0` is process 0 running, and `idle` means the CPU waited for the next arrival. Lines are at most 78 characters and break only between whole slices; each new line repeats the last time. A sideways results table follows, with one column per process (arrival, CPU, completion, turnaround), then the average turnaround and the context-switch count. Phase 4 adds, between the timeline and the results: a **run-order table** (each slice's penalty, start, finish, length and memory block, e.g. `starts at 500, size 12000`) and a **memory event log** (allocations, waits, releases with merged holes, and each `COMPACTION #n` with the moves and the new layout). The results table gains Memory and Location rows; `6000->0` means Compaction moved the process. A final line counts the Compactions and their cycles. Too many processes to fit sideways use one row per process; very narrow terminals use labeled records. Times are CPU clock cycles.

The Phase 2 guide also includes [worked Gantt charts and calculations](docs/PHASE2_DESCRIPTION.md#worked-scheduling-timelines-and-performance-measures) for both algorithms, with explanations of waiting time and throughput alongside the required turnaround measures.

The normal interface pauses after an action so the result can be read. Colors require both input and output to be connected to a terminal, `TERM` not to be `dumb`, and `NO_COLOR` to be unset. Use `NO_COLOR=1 python3 main.py` to disable colors. Redirected input or output disables colors, screen clearing, and extra pauses. Setting `CLEAR_SCREENS = False` in `cli_style.py` retains earlier screens. Very narrow terminals can still wrap longer explanation sentences; the result fields remain present.

## Verification

Run from the project root:

```bash
python3 -m unittest discover -s tests -v
```

The completed implementation passes **125 test methods**:

| Test file | Count | Main coverage |
| --- | ---: | --- |
| `test_requirements.py` | 12 | Phase 1 records, validation, loading, adding, and viewing. |
| `test_saving.py` | 17 | Save/reload, overwrite handling, failures, and existing menu flow. |
| `test_editing.py` | 12 | Editing, removal, cancellation, and preservation after rejected changes. |
| `test_data_paths.py` | 6 | All four filename forms through load/save, explicit paths, other working directories, overwrite protection, and invalid input. |
| `test_file_picker.py` | 10 | File listing, navigation, manual paths, and errors. |
| `test_cli_style.py` | 11 | Existing terminal behavior plus timeline wrapping, idle and continuing slices, and results-table fallbacks. |
| `test_scheduler.py` | 24 | Exact FCFS/SJF/RR slices with penalties, quantum 1/2/3, arrival-before-requeue, no repeat penalty, ties, idle time, quantum validation, and unchanged records. |
| `test_scheduling_ui.py` | 8 | Three algorithm choices, quantum and memory prompt validation and cancel, current-data changes, full menu runs, and pause/result feedback. |
| `test_memory_manager.py` | 10 | First-Fit, Worst-Fit and its tie rule, exact fits, merging holes on one or both sides, when Compaction is needed, and Compaction moves. |
| `test_phase4_scheduler.py` | 11 | Hand-calculated Data Set 1 runs (FCFS and RR), Compaction times and layouts, First-Fit vs Worst-Fit placement (including Data Set 3), merging avoiding Compaction, SJF skipping a waiting process, memory validity on every data set, unchanged records, and the 15000 limit. |
| `test_phase4_ui.py` | 4 | Run-order table, memory events, Compaction report, Location row, both fits and Round-Robin through the menu. |

Real interactive checks cover the official runs, result pauses, unchanged View data, and narrow/no-color output. Screenshots for each phase are provided separately in that phase's submission documentation rather than duplicated inside the runnable source package.

## Repository layout

| Path | Contents |
| --- | --- |
| `*.py` | The application (see [How the files fit together](#how-the-files-fit-together)). |
| `data/` | Loadable process datasets used by the tests and walkthroughs. |
| `tests/` | The automated `unittest` suite. |
| `docs/` | The Phase 1, Phase 2, Phase 3, and Phase 4 Markdown walkthroughs. |

The Moodle handouts and official test-data attachments for Phases 1 to 4 are kept locally under `Assignment Specifications/` for reference, with a local copy of the Phase 4 data file in `data/official/` (not published). They are not runtime dependencies; the loadable numeric datasets are under `data/`.
