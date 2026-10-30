# Phase 3 — Round-Robin Scheduling and Context-Switch Penalties

[Overall project](../README.md) | [Phase 1 baseline](PHASE1_DESCRIPTION.md) | [Phase 2 scheduling](PHASE2_DESCRIPTION.md)

Phase 3 adds Round-Robin (RR) scheduling with an adjustable time quantum. It also applies and counts the context-switch penalty in all three algorithms: FCFS, SJF and RR. Everything from Phases 1 and 2 still works. All **100 tests pass**.

On the official Phase 3 data (penalty 1 cycle):

| Algorithm | Average turnaround | Context switches |
| --- | ---: | ---: |
| FCFS | 20.17 cycles | 6 |
| SJF | 16.83 cycles | 6 |
| Round-Robin, quantum 3 | 25.67 cycles | 12 |

## Requirements and where they are met

| Assignment requirement | Where it is met |
| --- | --- |
| Keep the Phase 1 and Phase 2 features working | The manager and validation are unchanged. FCFS and SJF now run on the shared loop in [scheduler.py](../scheduler.py). All Phase 1 and 2 tests still pass, with the Phase 2 expected values updated for the penalty. |
| Let the user choose FCFS, SJF or Round-Robin | Menu choice 8, then `1`, `2` or `3`, in `run_scheduler_from_input()` in [main.py](../main.py). |
| Quantum from the data file or the UI, validated as a positive number | `ask_quantum()` in [main.py](../main.py) offers the file's quantum as the default. `schedule_rr()` in [scheduler.py](../scheduler.py) rejects anything that is not a positive whole number. |
| Track each process's remaining CPU time | `remaining_time` on the PCB ([pcb.py](../pcb.py)), updated after every slice by `_run()`. |
| Account for the penalty before each start or resume, in all three algorithms | `_run()` adds the penalty to the clock before the chosen process runs, whenever it is a different process from the last one. |
| A clear timeline string with the start and finish of each run or slice, showing the context switches and penalties | `timeline()` in [cli_style.py](../cli_style.py). |
| Each process's turnaround, the average turnaround, and the number of context switches | `results_table()` in [cli_style.py](../cli_style.py), `average_turnaround()` in [scheduler.py](../scheduler.py), and the `Context switches:` line in [main.py](../main.py). |

## Scheduling rules

### Confirmed by the assignment and the professor

1. The context-switch penalty applies to **FCFS, SJF and Round-Robin**, so the Phase 2 averages (4.40 and 4.20) change, to 7.40 and 7.20.
2. The penalty is paid **before** a process runs: whenever a process is started (including the very first one at time 0) or resumed, meaning it replaces the process that was running.
3. **No penalty** is paid when the same process keeps running after its quantum expires because no other process takes over.
4. When a new arrival and a quantum expiry happen at the same moment, either order is allowed as long as it is documented. **We chose:** the new arrival enters the ready queue *before* the process being requeued.
5. The quantum may come from the data file or the user interface, and it must be a positive whole number of clock cycles.
6. Turnaround = Completion − Arrival, with all penalties included in the completion times.
7. Every run shows the execution order, the start and finish of every run or slice, the context switches and their penalties in the timeline, each process's turnaround, the average turnaround, and the total number of context switches.

### Our own documented assumptions

These are decisions we made where the assignment leaves the choice open. They are not rulings from the professor.

- **The first start counts as a context switch.** The reported count is the number of penalties paid, so count × penalty = the total time the penalties add.
- **FCFS and SJF choose the next process before its penalty.** A shorter job that arrives during that penalty waits for the next choice.
- **Idle CPU.** When nothing is ready, the clock jumps to the next arrival. Starting that process still costs a penalty (rule 2). The timeline shows the gap as `idle`.
- **Records that disagree on quantum or penalty** are rejected when loaded or added, as in Phase 1, so every run has one quantum and one penalty.
- **The quantum comes from the UI, with the data file as the default.** The prompt shows the file's quantum. Enter keeps it, a positive whole number overrides it for that run only, and `C` cancels. The saved records never change. The penalty always comes from the data file.
- **Ties** keep the Phase 2 rules: earlier arrival first, then file/addition order. SJF compares CPU required, then arrival, then queue order. The process ID is never a priority.
- **`remaining_time` is added to the PCB.** It starts equal to CPU required and is runtime state only: it is not saved, shown in View, or validated as input. The scheduler changes it only on its own copies.
- **Consecutive quanta of the same process stay separate slices** in the timeline (`1 P1 4 P1 7`), because each quantum is a time slice the assignment asks us to show.
- **The timeline is plain ASCII** (`CS`, `idle`, `P<id>`), because special block characters can crash some Windows consoles.

## Data structures

**The updated PCB.** [pcb.py](../pcb.py) keeps the six saved fields (ID, memory, arrival, CPU required, quantum, penalty) and adds `remaining_time`, the CPU time the process still needs. It starts at `cpu_required`, goes down after each slice, and the process is finished when it reaches 0.

**The ready queue.** The scheduler uses a `collections.deque`: a list that is fast to take from the front and add to the back, which is exactly how a ready queue is used. A second deque holds the processes that have not arrived yet, sorted by arrival time.

**Copies, not the real records.** The scheduler works on `copy.copy()` of each PCB, so changing `remaining_time` during a run never touches the manager's records. View and Save show the same data before and after any run.

**The result.** Every algorithm returns the same dictionary:

```python
{
  "slices": [   # one per time slice, in execution order
    {"process_id": 0, "switch_start": 0,   # None when no penalty came before this slice
     "start_time": 1, "finish_time": 4, "remaining": 5},   # CPU left after this slice
    ...
  ],
  "processes": [   # one per process, in the original collection order
    {"process_id": 0, "arrival_time": 0, "cpu_required": 8,
     "completion_time": 37, "turnaround_time": 37},
    ...
  ],
  "context_switches": 12,   # penalties paid, including the first start
  "penalty": 1,
  "quantum": 3,             # None for FCFS and SJF
}
```

The menu prints the explanation lines. [cli_style.py](../cli_style.py) turns `slices` into the timeline and `processes` into the results table.

## How the shared loop works

FCFS, SJF and Round-Robin all use one function, `_run(pcbs, quantum, choose)` in [scheduler.py](../scheduler.py). They differ in only two ways: which ready process is picked (`choose`), and whether a quantum cuts a run short (`quantum`, which is `None` for FCFS and SJF).

1. Copy the PCBs, sort the copies by arrival (keeping file order for ties), and set each `remaining_time` to its CPU requirement.
2. **Admit:** move every process that has arrived by the current clock to the back of the ready queue.
3. If the ready queue is empty, jump the clock to the next arrival and go back to step 2.
4. **Choose** the next process. FCFS and RR take the front of the queue; SJF takes the shortest job.
5. **Penalty:** if this process is not the one that ran last, record the switch, add the penalty to the clock, and count one context switch. Then admit anything that arrived during the penalty.
6. **Run:** the slice length is the whole remaining time (FCFS and SJF), or at most one quantum (RR). Advance the clock, subtract from `remaining_time`, and record the slice.
7. **Admit again** before requeueing, so a process that arrives at this exact moment goes ahead of the one whose quantum just expired (rule 4).
8. If the process still needs CPU time, put it at the back of the queue. Otherwise, record its completion time.
9. Repeat until no processes are left waiting or arriving. Then build each process's turnaround as completion − arrival.

Rule 3 happens naturally. If a process's quantum expires and the queue is otherwise empty, the same process is chosen again. It is the one that ran last, so no penalty is paid.

## Worked trace: official data, Round-Robin, quantum 3

The data ([data/phase3_official.txt](../data/phase3_official.txt)): P0 arrives at 0 needing 8, P1 at 1 needing 8, P2 at 2 needing 1, P3 at 3 needing 3, P4 at 3 needing 4, and P5 at 4 needing 4. The penalty is 1 for all of them.

| # | Penalty | Runs | CPU left | Ready queue afterwards | Note |
| ---: | --- | --- | ---: | --- | --- |
| 1 | 0–1 | P0 1–4 | 5 | P1 P2 P3 P4 P5 P0 | P1 arrives during the penalty. P2–P4 arrive while P0 runs. P5 arrives at 4, exactly when P0's quantum expires, so it goes ahead of P0. |
| 2 | 4–5 | P1 5–8 | 5 | P2 P3 P4 P5 P0 P1 | |
| 3 | 8–9 | P2 9–10 | done | P3 P4 P5 P0 P1 | P2 completes at 10, turnaround 10 − 2 = 8. |
| 4 | 10–11 | P3 11–14 | done | P4 P5 P0 P1 | Completes at 14, turnaround 11. |
| 5 | 14–15 | P4 15–18 | 1 | P5 P0 P1 P4 | |
| 6 | 18–19 | P5 19–22 | 1 | P0 P1 P4 P5 | |
| 7 | 22–23 | P0 23–26 | 2 | P1 P4 P5 P0 | |
| 8 | 26–27 | P1 27–30 | 2 | P4 P5 P0 P1 | |
| 9 | 30–31 | P4 31–32 | done | P5 P0 P1 | Completes at 32, turnaround 29. |
| 10 | 32–33 | P5 33–34 | done | P0 P1 | Completes at 34, turnaround 30. |
| 11 | 34–35 | P0 35–37 | done | P1 | Completes at 37, turnaround 37. |
| 12 | 37–38 | P1 38–40 | done | (empty) | Completes at 40, turnaround 39. |

The program shows the same run as:

```text
0 CS 1 P0 4 CS 5 P1 8 CS 9 P2 10 CS 11 P3 14 CS 15 P4 18 CS 19 P5 22
22 CS 23 P0 26 CS 27 P1 30 CS 31 P4 32 CS 33 P5 34 CS 35 P0 37 CS 38 P1 40
```

Average turnaround = (37 + 39 + 8 + 11 + 29 + 30) / 6 = 154 / 6 = **25.67 cycles**. Every slice was preceded by a penalty, so there were **12 context switches**, adding 12 × 1 = 12 cycles.

## FCFS and SJF with penalties

FCFS and SJF stay non-preemptive: a chosen process runs to completion. The only change is the penalty before each start.

FCFS on the official Phase 3 data, average 121 / 6 = **20.17 cycles**, 6 switches:

```text
0 CS 1 P0 9 CS 10 P1 18 CS 19 P2 20 CS 21 P3 24 CS 25 P4 29 CS 30 P5 34
```

SJF, average 101 / 6 = **16.83 cycles**, 6 switches. At clock 9, every other process has arrived. The short jobs P2, P3, P4 and P5 go before P1, which needs 8 cycles:

```text
0 CS 1 P0 9 CS 10 P2 11 CS 12 P3 15 CS 16 P4 20 CS 21 P5 25 CS 26 P1 34
```

On the Phase 2 data, the same penalty raises the averages from 4.40 and 4.20 to **7.40** (FCFS) and **7.20** (SJF): five penalties of 1 cycle, each delaying every later process.

## Demo walkthrough

1. Run `python3 main.py`.
2. Choose **1 → M** and type `phase3_official`. Six records load. Choose **2** to view them.
3. Choose **8 → 1** (FCFS), then **8 → 2** (SJF). Note the averages of 20.17 and 16.83, with 6 switches each.
4. Choose **8 → 3** and press Enter to keep the file's quantum of 3. The timeline matches the trace above: 25.67 cycles and 12 switches.
5. Choose **8 → 3** again and type `2`. The average becomes 27.50 with 15 switches. With `1` it becomes 35.83 with 28 switches. A smaller quantum means more switches, and every switch costs a penalty.
6. Try typing `0`, `abc` or `2.5` at the quantum prompt: each shows an error and asks again. `C` cancels the run.
7. Choose **2** again: the records, including the quantum of 3, are unchanged.

To see an idle CPU, load `phase2_idle` and run any algorithm: `0 idle 5 CS 6 P1 8 idle 12 CS 13 P2 14`.

## Tests and what they prove

Run `python3 -m unittest discover -s tests -v`. All 100 tests pass.

| Test group | What it proves |
| --- | --- |
| Official Phase 3 runs ([test_scheduler.py](../tests/test_scheduler.py)) | FCFS, SJF and RR with quanta 3, 2 and 1 match hand-calculated slices, turnarounds, averages and switch counts. |
| Phase 2 data with penalties | FCFS and SJF give 7.40 and 7.20, the expected change from 4.40 and 4.20. |
| Penalty rules | The same process continuing pays no new penalty. A lone survivor finishes without one. An arrival at the moment of a quantum expiry queues first. SJF chooses before the penalty. |
| Edge cases | Idle gaps at the start and middle, a huge idle jump, all processes arriving together, unsorted input, ties by arrival and file order, and an empty set. |
| Consistency checks | Every schedule is checked for no overlaps, full-length penalties, each process getting exactly its CPU time, slices no longer than the quantum, and turnaround = completion − arrival. RR with a very large quantum equals FCFS. |
| Quantum validation | `schedule_rr` rejects 0, −1, `"3"` and 2.5. The menu re-asks after `0`, `-2`, `abc` and `2.5`, accepts ` 2 `, and leaves the stored quantum at 3 ([test_scheduling_ui.py](../tests/test_scheduling_ui.py)). |
| Records unchanged | Running any algorithm leaves the PCB objects, their order, `remaining_time` and the saved file exactly as they were. |
| Display ([test_cli_style.py](../tests/test_cli_style.py)) | The timeline matches the official run, wraps only between whole slices at widths 30 and 78, shows `idle` and continuing slices, and keeps IDs like `P-3` and `P1000` intact. The results table falls back to rows, then to labeled records, when it does not fit. |
| Menu integration | The three choices show the exact headings, penalty line, timeline, average and switch count. Cancelling at either prompt keeps the records. Edits, additions, removals and loads affect the next run. |

## Known limit

The loop takes one pass per slice. With quantum 1 and a process needing millions of cycles, the run would be slow and the timeline enormous. That is fine for classroom-sized data. The code marks this with a `shortcut:` comment in [scheduler.py](../scheduler.py).

## Display note

The program uses a compact timeline string ("Option A"), as shown above. The alternative ("Option B") would show one table row per slice, with the columns `#`, `Proc`, `Switch`, `Run` and `CPU left`. Only `timeline()` in [cli_style.py](../cli_style.py) knows the layout, so switching would change that one function and its tests, and nothing else.
