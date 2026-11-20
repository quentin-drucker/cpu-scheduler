# Phase 4 — Contiguous Memory Allocation and Compaction

[Overall project](../README.md) | [Phase 1 baseline](PHASE1_DESCRIPTION.md) | [Phase 2 scheduling](PHASE2_DESCRIPTION.md) | [Phase 3 Round-Robin](PHASE3_DESCRIPTION.md)

Phase 4 adds a memory manager to the Phase 3 scheduler. Memory has 15,000 locations. Each arriving process gets one contiguous block of exactly the size it asks for (variable partitions), placed by **First-Fit** or **Worst-Fit**. When a process finishes, its block becomes a hole and neighbouring holes are merged. When no single hole can fit a waiting process but the free total can, memory is **compacted**. Everything from Phases 1–3 still works. All **125 tests pass**.

Results on the three official Phase 4 data sets (penalty 1 cycle, quantum 3):

| Data set | Algorithm | Average turnaround | Context switches | Compaction at cycle |
| --- | --- | ---: | ---: | ---: |
| 1 | FCFS | 11.25 | 4 | 11 |
| 1 | SJF | 11.25 | 4 | 11 |
| 1 | Round-Robin | 17.25 | 7 | 17 |
| 2 | FCFS | 8.60 | 5 | 7 |
| 2 | SJF | 8.60 | 5 | 7 |
| 2 | Round-Robin | 11.00 | 7 | 6 |
| 3 | FCFS | 21.43 | 7 | 12 |
| 3 | SJF | 20.14 | 7 | 12 |
| 3 | Round-Robin | 35.43 | 15 | 30 |

First-Fit and Worst-Fit give the same CPU results on these sets, because each needs exactly one Compaction at the same cycle. In Data Sets 1 and 2, every placement before that Compaction has only one hole to choose from, so the layouts are the same too. **Data Set 3 with FCFS or SJF places processes differently.** P7 arrives at cycle 7, just as P1 frees 0–1999. First-Fit puts P7 at 0, so Compaction at cycle 12 moves three processes. Worst-Fit puts P7 at 7500, so Compaction moves four. The Phase 2 official data (`phase2_official`) shows a stronger difference: First-Fit merges three holes and avoids Compaction, while Worst-Fit needs one at cycle 6. See [First-Fit vs Worst-Fit](#first-fit-vs-worst-fit).

## Requirements and where they are met

| Assignment requirement | Where it is met |
| --- | --- |
| Keep earlier features working; the PCB includes the memory required | `memory` was already one of the six PCB fields ([pcb.py](../pcb.py)). Load, View, Add, Edit, Remove and Save are unchanged. All Phase 1–3 tests still pass. |
| Validate memory | `PCB.validate()` now also rejects memory above 15000, because such a process could never be placed. |
| Choose FCFS, SJF or Round-Robin **and** First-Fit or Worst-Fit | Menu choice 8: algorithm (and quantum for RR), then `ask_fit()` in [main.py](../main.py). |
| Memory of 15,000 locations, initial hole of 15,000, exact-size contiguous blocks | `MemoryManager` in [memory_manager.py](../memory_manager.py). |
| First-Fit and Worst-Fit | `MemoryManager.find_hole()`. |
| Merge adjacent holes before Compaction | `MemoryManager.release()` merges neighbours every time a block is freed, so holes are always merged before Compaction is considered. |
| Detect when Compaction is needed and perform it | `MemoryManager.needs_compaction()` and `compact()`, called by `place()` in `_run()` in [scheduler.py](../scheduler.py). |
| Show which process ran, when it started and stopped (in schedule order), and where it lives in memory | The timeline plus the run-order table (`run_order()` in [cli_style.py](../cli_style.py)): `starts at 500, size 12000`. |
| Show context switches | The `CS` entries in the timeline, the Penalty column of the run-order table, and the `Context switches:` line. |
| Report each Compaction: the clock cycle, the triggering process, and the updated locations of all processes | `COMPACTION #n` in the memory event log (`memory_events()` in [cli_style.py](../cli_style.py)), with every move and the full new layout, plus the `Compactions:` total line. |
| Turnaround for each process, average turnaround, and each process's memory location | The results table (now with Memory and Location rows) and `Average Turnaround Time:`. |

## Memory rules

### From the assignment and the professor

1. Memory is one space of **15,000 locations** (0–14999), starting as a single hole of 15,000.
2. Each process gets **one contiguous block of exactly its requested size**.
3. **First-Fit** places a process in the first hole that is large enough. **Worst-Fit** places it in the largest hole.
4. **Adjacent holes are consolidated before Compaction.**
5. Compaction is reported with the clock cycle at which it was performed, based on a process arriving at the Ready Queue, together with the updated locations of all processes.
6. **Smaller processes that fit may go before a larger process that is waiting for memory** (professor's answer).
7. **Compaction costs no clock time**, but it should run **only when needed**, not after every release (professor's answer).

### Our own documented assumptions

These are decisions we made where the assignment leaves the choice open. They are not rulings from the professor.

- **A waiting process still joins the Ready Queue.** A process that does not fit when it arrives enters the Ready Queue straight away, keeping its arrival position, but it **cannot be chosen to run until it holds memory**. This follows the professor's remark that a large process does not have to wait outside the queue. In Data Set 1 with FCFS, P3 therefore runs before P4 once it gets memory at cycle 11. If the other reading is wanted (join the queue only once memory is given), only `admit()` in [scheduler.py](../scheduler.py) needs to change.
- **When Compaction is needed:** a process needs a block, no single hole is large enough, *and* the total free memory is enough. If the total is not enough either, Compaction could not help, so the process keeps waiting.
- **When memory is retried:** a process tries for memory when it arrives. Memory only becomes free when a process finishes, so waiting processes retry only then, in Ready Queue order. Any process that fits is placed, even if an earlier one is still waiting. Compaction therefore happens either at a process's arrival or at the cycle when another process finishes.
- **Order at the same instant:** when a process finishes at cycle *t*, these steps happen in order:
  1. Arrivals during its run get memory first, as memory was during the run.
  2. The finished block is freed and merged with its neighbours.
  3. Waiting processes retry.
  4. Processes arriving exactly at *t* try for memory.
- **A process keeps its block until it finishes.** Round-Robin preemption does not free memory; there is no swapping.
- **Compaction direction:** every block slides down towards address 0 in its current address order, leaving one hole at the top.
- **Worst-Fit tie:** when two holes are equally large, the lower address wins.
- **Memory over 15000 is rejected** when a record is loaded, added or edited. Such a process could never be placed, so the run could never finish. Before Phase 4, memory only had to be positive.
- **Phase 3 behaviour is still available in code.** Calling `schedule_fcfs(pcbs)` etc. without a fit ignores memory exactly as in Phase 3. The menu always asks for a fit.

Phase 3's scheduling rules are unchanged. The penalty is paid before every start or resume, including the first. A new arrival is queued before a preempted process. Ties use earlier arrival and then file order. See the [Phase 3 guide](PHASE3_DESCRIPTION.md#scheduling-rules).

## Data structures

**The PCB.** [pcb.py](../pcb.py) keeps the same six saved fields. `memory` was always stored and validated as positive; Phase 4 adds the upper limit of 15000. The saved file format is unchanged, so every earlier file still loads (unless a record asks for more than 15000).

**Blocks and holes.** [memory_manager.py](../memory_manager.py) describes memory with two lists, both kept in address order:

```python
blocks = [{"process_id": 4, "start": 0,   "size": 500},
          {"process_id": 3, "start": 500, "size": 12000}]   # who is where
holes  = [{"start": 12500, "size": 2500}]                     # free ranges
```

Together they cover every location exactly once. No two holes are ever side by side, because `release()` merges them immediately. A list fits this job: there are only a handful of entries, they need to stay in address order for First-Fit and Compaction, and they grow and shrink as processes come and go.

**Ready queue and memory.** The scheduler still uses Phase 3's `deque` ready queue on copies of the PCBs. Each time it picks the next process, it considers only the ready processes that hold a block (`runnable`). A waiting process stays in place in the queue.

**The result.** The Phase 3 result dictionary gains memory information:

```python
{
  "slices": [ {..., "memory_start": 500, "memory_size": 12000}, ... ],  # where it ran
  "processes": [ {..., "memory": 500, "memory_starts": [6000, 0]}, ... ],  # every address it had
  "fit": "First-Fit",
  "memory_size": 15000,
  "events": [   # in time order
    {"kind": "allocate", "time": 3, "process_id": 4, "start": 6000, "size": 500},
    {"kind": "wait", "time": 2, "process_id": 3, "size": 12000, "free": 9000, "largest": 9000},
    {"kind": "release", "time": 11, "process_id": 2, "holes": [...]},   # holes after merging
    {"kind": "compact", "time": 11, "process_id": 3, "size": 12000, "free": 14500,
     "largest": 8500, "moves": [{"process_id": 4, "from": 6000, "to": 0}], "layout": {...}},
  ],
  "compactions": [ ... ],   # the compact events only
  ...                       # slices, context_switches, penalty, quantum as in Phase 3
}
```

## Architecture

```text
main.py ──asks──> algorithm, quantum, First-Fit/Worst-Fit
   │
   └─calls──> scheduler.py  _run(pcbs, quantum, choose, fit)
                  │  ready queue, clock, penalties (Phase 3)
                  └─uses──> memory_manager.py  MemoryManager(fit)
                                 allocate / release (+merge) / needs_compaction / compact
   <──result dictionary──
main.py ──passes it to──> cli_style.py  timeline, run_order, memory_events, results_table
```

The memory manager does not know about clocks or processes beyond their IDs and sizes. The scheduler decides *when* to ask for memory. `cli_style.py` only formats. As before, no module except `main.py` asks for input, and nothing changes the manager's stored PCBs.

## Algorithms

**Allocation (`allocate`).**
1. Collect the holes that are large enough.
2. First-Fit takes the first of them, which is the lowest address. Worst-Fit takes the largest, and on a tie the lowest address.
3. The block takes the front of the hole; the rest stays a hole, and a hole of size 0 is removed.

**Release and merging (`release`).**
1. Remove the block and add its range as a hole.
2. Sort the holes by address.
3. Walk through them, joining any hole that starts exactly where the previous one ends.

**Placing a process (`place` in the scheduler).**
1. If `needs_compaction(size)`, meaning no hole fits but the free total does, compact first and record the event.
2. Then allocate.
3. If there is still no room, the process waits.

**Compaction (`compact`).** Walk the blocks in address order with a running `next_start`. Move each block whose start differs to `next_start`, then add its size. The remaining space becomes one hole at the top.

**Scheduling with memory.** This is the Phase 3 loop with three changes:

- Arrivals try for memory.
- Only processes with memory can be chosen.
- A finished process releases its block and waiting processes retry.

If processes are ready but none holds memory, the clock jumps to the next arrival. With every process at 15000 or less this cannot leave a process stuck, because a run with no blocks held has all 15000 locations free. The code still raises a clear error instead of looping.

## Worked example: Data Set 1, FCFS, First-Fit

Data: P1 2000 @0 CPU 4, P2 4000 @1 CPU 5, P3 12000 @2 CPU 2, P4 500 @3 CPU 6. Quantum 3, penalty 1.

| Cycle | Event | Holes afterwards |
| ---: | --- | --- |
| 0 | P1 arrives, placed at 0–1999. Penalty 0–1, runs 1–5. | 2000–14999 |
| 1 | P2 arrives, placed at 2000–5999. | 6000–14999 |
| 2 | P3 arrives needing 12000; only 9000 free. **Waits** (stays in the Ready Queue). | 6000–14999 |
| 3 | P4 arrives, fits at 6000–6499 (a smaller process going first). | 6500–14999 |
| 5 | P1 finishes, frees 0–1999. 10500 free in total, still not enough for P3. P2 runs 6–11. | 0–1999, 6500–14999 |
| 11 | P2 finishes, frees 2000–5999, merged with 0–1999 into **0–5999**. 14500 free, but the largest hole is 8500 → **Compaction #1**: P4 moves 6000 → 0. P3 is placed at 500–12499. | 12500–14999 |
| 11–14 | P3 (first in the queue) penalty 11–12, runs 12–14. | |
| 14–21 | P4 penalty 14–15, runs 15–21 at its new location 0. | |

Turnarounds: 5, 10, 12, 18. Average **11.25** cycles, **4** context switches, **1** Compaction at cycle 11. Worst-Fit gives the same result here. Every placement before cycle 5 has only one hole to choose from, and the merge at cycle 11 leaves the same two holes either way.

## First-Fit vs Worst-Fit

**Data Set 3, FCFS.** At cycle 7, P1 finishes and frees 0–1999, and then P7 (500) arrives. The holes are 0–1999 and 7500–14999.

- First-Fit places P7 at 0–499. When P2 ends at 12, holes 500–1999 and 2000–5999 merge into 500–5999. With 7500–14999 that is 13000 free, but no single hole fits 12000, so Compaction moves P4 6000→500, P5 6500→1000 and P6 7000→1500. P7 stays at 0.
- Worst-Fit places P7 at 7500–7999. At 12 the holes are 0–5999 and 8000–14999. Compaction moves all four small processes: P4→0, P5→500, P6→1000, P7→1500.
- Either way, P3 is placed at 2000–13999 and the CPU results are identical.

**Phase 2 official data.**

On `phase2_official` (P0 2000 @0, P1 4000 @1, P2 12000 @2, P3 500 @3, P4 500 @3), at cycle 3 P0 has just freed 0–1999, and P2 is still waiting:

- **First-Fit** puts P3 and P4 in the old P0 hole, at 0 and 500. When P1 (2000–5999) ends at cycle 6, its block merges with the holes on both sides (1000–1999 and 6000–14999) into one hole 1000–14999. P2 fits at 1000, so **no Compaction is needed**. Merging adjacent holes is what makes room.
- **Worst-Fit** puts P3 and P4 in the larger hole, at 6000 and 6500. At cycle 6 the holes are 0–5999 and 7000–14999 (6000 + 8000). That's 14000 free but no single hole fits, so **Compaction** at cycle 6 moves P3 → 0 and P4 → 500, and P2 is placed at 1000.

## Interface changes

- Main-menu choice 8 is now *Run CPU scheduler with memory allocation*. After the algorithm (and quantum) it asks: `1. First-Fit`, `2. Worst-Fit`, `C. Cancel`. Invalid input is rejected and asked again; `C` cancels without changing anything.
- Each run prints the memory rule, the Phase 3 timeline, then:
  - **Run order**: one row per slice with the penalty cycles, start, finish, length and `starts at X, size Y`.
  - **Memory events**: allocations, waits (with the largest hole and free total), releases (with the holes after merging), and each `COMPACTION #n` with every move and the full `Memory now:` layout.
  - The results table gains **Memory** and **Location** rows. `6000->0` means Compaction moved the process.
  - `Compactions: n (at cycle …)` after the context-switch line, and in the success message.
- The screen title reads `COM326 | PROJECT PHASE 4`.

## Data

- [data/phase4_set1.txt](../data/phase4_set1.txt), [phase4_set2.txt](../data/phase4_set2.txt) and [phase4_set3.txt](../data/phase4_set3.txt) are the three data sets from the Phase 4 Moodle data file, one loadable file each. They have the same values as the older `dataset1–3.txt`.
- `data/official/` holds an unchanged local copy of the Moodle data file for reference. It sits in a subfolder so the file picker does not list it (it is not loadable as-is), and it is git-ignored like the other handouts.

## Test coverage

25 new tests (125 in total). The expected values are worked out by hand, not copied from program output.

| Test file | Count | What it checks |
| --- | ---: | --- |
| `test_memory_manager.py` | 10 | One initial 15000 hole; First-Fit picks the lowest fitting hole; Worst-Fit picks the largest, lowest on a tie; exact fit removes the hole; merging on both sides and on one side; Compaction is needed only when the total fits but no hole does; Compaction moves blocks down in order and leaves one hole; layouts are snapshots; invalid rule/release rejected. After each change, blocks and holes must cover memory exactly once with no touching holes. |
| `test_phase4_scheduler.py` | 11 | Data Set 1 FCFS (both fits) and RR: every slice, memory address, turnaround, Compaction cycle, moves and layout. A smaller process is placed while a larger one waits. First-Fit avoids Compaction by merging three holes where Worst-Fit compacts. Data Set 3, where the two rules place P7 differently and compact different processes. A small case where the two rules pick different holes. SJF never picks a process without memory. A replay check on every data set × algorithm × fit (no overlapping blocks, no needless Compaction, each process allocated and released once). Stored PCBs are never changed. No fit means Phase 3 results. Memory that all fits gives Phase 3 results. Memory over 15000 is rejected on load. |
| `test_phase4_ui.py` | 4 | Through the real menu: Data Set 1's run-order rows, wait/allocate/release lines, the Compaction report with moves and new layout, Location row, totals and success message. First-Fit vs Worst-Fit on the Phase 2 data. Round-Robin asking for quantum then fit. The fit menu, the menu label and the Phase 4 title. |

Changed existing tests:

- The Phase 1 boundary test now checks that 15000 is accepted and 15001 is rejected. It previously checked that there was no memory limit.
- The Phase 3 scheduler test that used memory 30000 now uses 15000.
- The menu tests answer the new memory prompt. The Phase 3 menu tests give each record 1000 locations so memory never delays a run and their hand-checked Phase 3 values still apply.
- The full-menu test on the Phase 2 data now expects SJF to average 7.40 instead of 7.20, because P2 must wait for memory until cycle 6.
