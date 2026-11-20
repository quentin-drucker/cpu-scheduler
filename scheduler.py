"""Calculates CPU schedules, with optional memory allocation, without changing the PCBs."""

from collections import deque
import copy

from memory_manager import MemoryManager


# The pcb manager supplies validated PCB objects. These functions only read them;
# they do not ask for input, print tables, or save files. This lets the menu
# and the tests use the same calculations.
# FCFS, SJF and Round-Robin share one CPU loop built around a ready queue.
# They differ in only two ways: which ready process is picked next, and
# whether a quantum cuts a run short. Every algorithm pays the context-switch
# penalty before a process starts or resumes.
# Phase 4: when a memory-allocation rule (fit) is given, a process may run only
# while it holds a block of memory. Without a fit, runs are exactly Phase 3.


def _run(pcbs, quantum, choose, fit=None):
    """Runs the shared CPU loop; quantum None means each job runs to completion."""

    # Work on copies, so remaining_time changes never reach the manager's records.
    # sorted is stable: equal arrivals keep their file/addition order.
    arrivals = deque(sorted((copy.copy(pcb) for pcb in pcbs),
                            key=lambda pcb: pcb.arrival_time))
    for pcb in arrivals:
        pcb.remaining_time = pcb.cpu_required
    # PCBManager already makes every process share one penalty value.
    penalty = pcbs[0].context_switch_penalty if pcbs else 0

    # A deque is a list that is fast to take from the front and add to the back,
    # which is exactly how a ready queue is used.
    ready = deque()
    clock = 0
    last = None           # the process that used the CPU most recently
    slices = []
    completion = {}
    switches = 0

    memory = MemoryManager(fit) if fit else None
    events = []        # memory events in time order: allocate, wait, release, compact
    locations = {}     # process ID -> every start address it has had

    def place(pcb, time):
        """Gives pcb a block now if possible, compacting only when that is the only way."""
        compaction = None
        if memory.needs_compaction(pcb.memory):
            # Holes are already merged on release, so if the free total fits but
            # no single hole does, only compaction can make room.
            free, largest = memory.free_total(), memory.largest_hole()
            moves = memory.compact()
            for move in moves:
                locations[move["process_id"]].append(move["to"])
            compaction = {"kind": "compact", "time": time, "process_id": pcb.process_id,
                          "size": pcb.memory, "free": free, "largest": largest,
                          "moves": moves}
            events.append(compaction)
        block = memory.allocate(pcb.process_id, pcb.memory)
        if block is None:
            return False
        locations[pcb.process_id] = [block["start"]]
        events.append({"kind": "allocate", "time": time, "process_id": pcb.process_id,
                       "start": block["start"], "size": block["size"]})
        if compaction:
            # Report the layout after the waiting process has its new block.
            compaction["layout"] = memory.layout()
        return True

    def admit(include_now=True):
        # Move every process that has arrived to the back of the ready queue.
        # include_now=False stops at arrivals strictly before the current clock.
        while arrivals and (arrivals[0].arrival_time < clock or
                            include_now and arrivals[0].arrival_time == clock):
            arrived = arrivals.popleft()
            ready.append(arrived)
            # It joins the ready queue at once, even without memory; it just
            # cannot be chosen to run until it gets a block (our documented choice).
            if memory and not place(arrived, arrived.arrival_time):
                events.append({"kind": "wait", "time": arrived.arrival_time,
                               "process_id": arrived.process_id, "size": arrived.memory,
                               "free": memory.free_total(),
                               "largest": memory.largest_hole()})

    def has_memory(pcb):
        return memory is None or memory.block_of(pcb.process_id) is not None

    while arrivals or ready:
        admit()
        # Only processes holding memory can run. A waiting one keeps its queue place.
        runnable = [pcb for pcb in ready if has_memory(pcb)]
        if not runnable:
            if not arrivals:
                # Unreachable while every PCB fits in memory on its own, but a
                # clear error is better than looping forever.
                raise RuntimeError("Processes are waiting for memory that can never be freed.")
            # Nobody can run yet. Jump to the next arrival and check again.
            # Even a very long idle gap takes just this one clock update.
            clock = arrivals[0].arrival_time
            continue

        # The next process is chosen BEFORE its penalty is paid. A shorter job
        # that arrives during the penalty waits for the next choice.
        pcb = choose(runnable)
        ready.remove(pcb)

        switch_start = None
        if pcb is not last:
            # Starting or resuming a different process costs the penalty first.
            # The very first start counts too. The same process continuing
            # after its quantum does not pay again.
            switch_start = clock
            clock += penalty
            switches += 1
            # Processes that arrive during the penalty join the queue now.
            admit()

        # shortcut: one loop pass per quantum, so quantum 1 with a CPU of millions is slow; merge uncontended quanta if that ever matters.
        run = pcb.remaining_time if quantum is None else min(quantum, pcb.remaining_time)
        start_time = clock
        clock += run
        pcb.remaining_time -= run
        block = memory.block_of(pcb.process_id) if memory else None
        slices.append({
            "process_id": pcb.process_id,
            "switch_start": switch_start,
            "start_time": start_time,
            "finish_time": clock,
            "remaining": pcb.remaining_time,
            # Where the process sat in memory during this slice (None without memory).
            "memory_start": block["start"] if block else None,
            "memory_size": block["size"] if block else None
        })

        # Arrivals during the run try for memory as it was during the run.
        admit(include_now=False)
        if not pcb.remaining_time:
            completion[pcb.process_id] = clock
            if memory:
                memory.release(pcb.process_id)
                events.append({"kind": "release", "time": clock,
                               "process_id": pcb.process_id, "holes": memory.layout()["holes"]})
                # Waiting processes, in ready-queue order, get the first try at
                # the freed space. Any that fit are placed, even out of order.
                for waiting in ready:
                    if not has_memory(waiting):
                        place(waiting, clock)
        # Arrivals at this same instant enter the queue BEFORE the process
        # whose quantum just expired (our documented choice).
        admit()
        if pcb.remaining_time:
            ready.append(pcb)
        last = pcb

    # One row per process, in the original collection order.
    # Turnaround includes waiting, penalties AND running, so subtract the arrival.
    processes = [{
        "process_id": pcb.process_id,
        "arrival_time": pcb.arrival_time,
        "cpu_required": pcb.cpu_required,
        "completion_time": completion[pcb.process_id],
        "turnaround_time": completion[pcb.process_id] - pcb.arrival_time,
        "memory": pcb.memory,
        # Every start address in order; more than one means compaction moved it.
        "memory_starts": locations.get(pcb.process_id, [])
    } for pcb in pcbs]

    return {
        "slices": slices,
        "processes": processes,
        "context_switches": switches,
        "penalty": penalty,
        "quantum": quantum,
        "fit": fit,
        "memory_size": memory.size if memory else None,
        "events": events,
        "compactions": [event for event in events if event["kind"] == "compact"]
    }


def _front(ready):
    # FCFS and Round-Robin both take whoever has waited longest in the queue.
    return ready[0]


def _shortest(ready):
    # Compare CPU time first, then arrival time. On a complete tie, min keeps
    # the first in queue order, preserving file/addition order.
    # The process ID is a label, not a scheduling priority.
    return min(ready, key=lambda pcb: (pcb.cpu_required, pcb.arrival_time))


def schedule_fcfs(pcbs, fit=None): # First-Come, First-Served
    """Runs processes by arrival time; equal arrivals keep their input order."""
    return _run(pcbs, None, _front, fit)


def schedule_sjf(pcbs, fit=None): # Shortest Job First
    """Runs the shortest ready job each time the CPU becomes free."""
    return _run(pcbs, None, _shortest, fit)


def schedule_rr(pcbs, quantum, fit=None): # Round-Robin
    """Gives each ready process up to `quantum` cycles in turn."""

    # bool is a kind of int in Python, so rule it out explicitly.
    if not isinstance(quantum, int) or isinstance(quantum, bool) or quantum <= 0:
        raise ValueError("Quantum must be a positive whole number of clock cycles.")
    return _run(pcbs, quantum, _front, fit)


def average_turnaround(processes):
    """Returns the mean turnaround, or None when no processes ran."""

    # An empty schedule has no average. Check before dividing by its count.
    if not processes:
        return None

    total = sum(row["turnaround_time"] for row in processes)
    # Regular division keeps fractions. Round only when displaying the answer.
    return total / len(processes)
