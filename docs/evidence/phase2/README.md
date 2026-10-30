# Phase 2 test evidence

[Phase 2 explanation](../../PHASE2_DESCRIPTION.md) | [Overall guide](../../../README.md)

The Phase 2 evidence includes actual Terminal screenshots and a completed captioned report, plus the earlier `.txt` transcripts below. Those transcripts were captured by running `main.py` with keyboard responses supplied through standard input. They include menus and plain output; files ending in `_input.txt` contain the responses used.

## Captured cases

| Transcript | Input and check | Observed result |
| --- | --- | --- |
| [official_fcfs.txt](official_fcfs.txt) | Official data; View, then FCFS. | Five unchanged records; order 0,1,2,3,4; average 4.40. |
| [official_sjf.txt](official_sjf.txt) | Official data; SJF. | Order 0,2,1,3,4; average 4.20. |
| [idle.txt](idle.txt) | `data/phase2_idle.txt`; both algorithms. | Starts 5 and 12; finishes 7 and 13; average 1.50. |
| [nonpreemptive.txt](nonpreemptive.txt) | `data/phase2_nonpreemptive.txt`; SJF. | The eight-cycle job finishes before the later short jobs; average 8.33. |
| [ties.txt](ties.txt) | `data/phase2_ties.txt`; SJF. | Equal CPU times use arrival and then collection order; average 4.25. |
| [invalid_edit.txt](invalid_edit.txt) | Official data; reject process 0 arrival −1, cancel, run FCFS. | Original schedule remains; average 4.40. |
| [edit_save_reload.txt](edit_save_reload.txt) | Official data; set process 0 CPU to 1, schedule, save/reload/view/schedule. | Average 3.40 before and after reload. Only the chosen CPU value changes. |

The full expected official timing tables and explanations are in the Phase 2 guide. Generated save data is kept here as [edited_processes.txt](edited_processes.txt); it does not replace the official input.

## Reproduce the text captures

From the project root, for example:

```bash
python3 main.py < evidence/phase2/official_fcfs_input.txt
```

The edit/save/reload input includes `Y` because `evidence/phase2/edited_processes.txt` already exists. That replay overwrites only this demonstration save with the same expected records. Use a different destination for personal edits.

For screenshots, run `python3 main.py` interactively and follow the same actions, pressing Enter at the pauses. The saved input files omit those extra Enter responses because redirected input does not pause. The file picker accepts **M** for the paths shown in the guide, avoiding dependence on file-list numbering.

## Screenshot checklist

**Complete:** 16 genuine Terminal-window captures were taken on October 14, 2026. The screenshot report includes an action/input description, expected result, and observed-result caption for every figure. Its editable Word version and PDF are in the submission's `Visual Showcase and Documentation/` folder, with the PNGs under `Screenshots/`.

Working copies of the captures are also under `screenshots/phase2/` in the development project. The screenshots use the normal colored interface; the test-suite summary uses plain terminal output. Application source and all pre-existing datasets were preserved.

| Figure | Screenshot filename | Observed result |
| ---: | --- | --- |
| 1 | `0-Main_CLI_Menu.png` | The main menu shows all eight options and an empty collection. Option 8 provides the Phase 2 scheduler while the Phase 1 actions remain available. |
| 2 | `1-Automated_tests.png` | The terminal reports “Ran 87 tests” and “OK.” The -q option keeps the summary compact while running the same complete test suite. |
| 3 | `2-Load_And_Display_Official_Data.png` | The load-success message and table show all five official records with the expected six values. This establishes the input used by the next two scheduling runs. |
| 4 | `3-Official_FCFS.png` | The displayed FCFS order is 0, 1, 2, 3, 4. All five start/finish intervals and turnaround values match the expected schedule; the average is 4.40 cycles. |
| 5 | `4-Official_SJF.png` | The displayed SJF order is 0, 2, 1, 3, 4, with average turnaround 4.20 cycles. P2 starts at clock 2, demonstrating selection of the shortest job that is ready at that time. |
| 6 | `5-Records_Unchanged_After_Scheduling.png` | View still shows the five original records in the same order with unchanged values. The previous-action message confirms that this view follows the SJF run. |
| 7 | `6.1-Idle_FCFS.png` | FCFS starts the jobs at 5 and 12 and finishes them at 7 and 13. The 1.50-cycle average confirms that the idle time before arrival is not included in each process’s turnaround. |
| 8 | `6.2-Idle_SJF.png` | SJF produces the same two intervals and 1.50-cycle average. The CPU waits when no process is ready rather than starting a job before arrival. |
| 9 | `7-Nonpreemptive_SJF.png` | P10 finishes at 8 despite shorter jobs arriving earlier. P30 then runs before P20, and the average is 8.33 cycles, confirming non-preemptive SJF behavior. |
| 10 | `8-SJF_Ties.png` | The result is 30, 20, 10, 40 with average 4.25 cycles. Earlier arrival wins a CPU-time tie; the complete tie between P30 and P20 preserves their file order. |
| 11 | `9.1-Reject_Negative_Arrival.png` | Entering -1 produces “Arrival time must be 0 or greater.” The editor remains at the value prompt and offers cancellation instead of accepting the invalid value. |
| 12 | `9.2-Schedule_After_Rejected_Edit.png` | After cancelling the rejected edit, FCFS still shows the original schedule and 4.40-cycle average. The invalid arrival did not change the process definitions. |
| 13 | `10.1-Schedule_After_CPU_Edit.png` | With P0’s CPU requirement changed to 1, its finish is 1. The displayed turnaround values are 1, 2, 2, 4, 8, giving the expected 3.40-cycle average. |
| 14 | `10.2-Save_Edited_Collection.png` | The success message confirms that five process definitions were saved to the separate phase2_submission_demo.txt file. The official input file was preserved. |
| 15 | `10.3-Reload_Edited_Collection.png` | After exiting and restarting, the loaded table shows P0 with CPU required 1 and the other four records unchanged. This confirms that the edited values were read from the saved file. |
| 16 | `10.4-FCFS_After_Reload.png` | The fresh session reproduces the edited FCFS schedule and 3.40-cycle average. The calculation uses the reloaded definitions and agrees with the run before saving. |

The automated test screenshot uses `python3 -m unittest discover -s tests -q` to fit the command and complete summary in one frame. It runs the same 87 tests as the documented verbose (`-v`) command. The screenshot run passed all 87 tests.

The save/reload sequence created `data/phase2_submission_demo.txt` as a separate demonstration file. Process 0's CPU requirement is 1 in that file; the official dataset still has 2. The report shows the edited 3.40-cycle FCFS average before saving and again after loading the file in a fresh application session.

The earlier text transcripts predate the filename-shortcut update, so their prompts omit the current filename hints and resolved-path messages. Their scheduling results remain valid. The screenshots show the current application.
