"""Calculates Phase 3 CPU schedules without changing the process definitions."""

from collections import deque
import copy


# The pcb manager supplies validated PCB objects. These functions only read them;
# they do not ask for input, print tables, or save files. This lets the menu
# and the tests use the same calculations.
# FCFS, SJF and Round-Robin share one CPU loop built around a ready queue.
# They differ in only two ways: which ready process is picked next, and
# whether a quantum cuts a run short. Every algorithm pays the context-switch
# penalty before a process starts or resumes.


def _run(pcbs, quantum, choose):
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

    def admit():
        # Move every process that has arrived by now to the back of the ready queue.
        while arrivals and arrivals[0].arrival_time <= clock:
            ready.append(arrivals.popleft())

    while arrivals or ready:
        admit()
        if not ready:
            # Nobody can run yet. Jump to the next arrival and check again.
            # Even a very long idle gap takes just this one clock update.
            clock = arrivals[0].arrival_time
            continue

        # The next process is chosen BEFORE its penalty is paid. A shorter job
        # that arrives during the penalty waits for the next choice.
        pcb = choose(ready)
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
        slices.append({
            "process_id": pcb.process_id,
            "switch_start": switch_start,
            "start_time": start_time,
            "finish_time": clock,
            "remaining": pcb.remaining_time
        })

        # Arrivals at this same instant enter the queue BEFORE the process
        # whose quantum just expired (our documented choice).
        admit()
        if pcb.remaining_time:
            ready.append(pcb)
        else:
            completion[pcb.process_id] = clock
        last = pcb

    # One row per process, in the original collection order.
    # Turnaround includes waiting, penalties AND running, so subtract the arrival.
    processes = [{
        "process_id": pcb.process_id,
        "arrival_time": pcb.arrival_time,
        "cpu_required": pcb.cpu_required,
        "completion_time": completion[pcb.process_id],
        "turnaround_time": completion[pcb.process_id] - pcb.arrival_time
    } for pcb in pcbs]

    return {
        "slices": slices,
        "processes": processes,
        "context_switches": switches,
        "penalty": penalty,
        "quantum": quantum
    }


def _front(ready):
    # FCFS and Round-Robin both take whoever has waited longest in the queue.
    return ready[0]


def _shortest(ready):
    # Compare CPU time first, then arrival time. On a complete tie, min keeps
    # the first in queue order, preserving file/addition order.
    # The process ID is a label, not a scheduling priority.
    return min(ready, key=lambda pcb: (pcb.cpu_required, pcb.arrival_time))


def schedule_fcfs(pcbs): # First-Come, First-Served
    """Runs processes by arrival time; equal arrivals keep their input order."""
    return _run(pcbs, None, _front)


def schedule_sjf(pcbs): # Shortest Job First
    """Runs the shortest ready job each time the CPU becomes free."""
    return _run(pcbs, None, _shortest)


def schedule_rr(pcbs, quantum): # Round-Robin
    """Gives each ready process up to `quantum` cycles in turn."""

    # bool is a kind of int in Python, so rule it out explicitly.
    if not isinstance(quantum, int) or isinstance(quantum, bool) or quantum <= 0:
        raise ValueError("Quantum must be a positive whole number of clock cycles.")
    return _run(pcbs, quantum, _front)


def average_turnaround(processes):
    """Returns the mean turnaround, or None when no processes ran."""

    # An empty schedule has no average. Check before dividing by its count.
    if not processes:
        return None

    total = sum(row["turnaround_time"] for row in processes)
    # Regular division keeps fractions. Round only when displaying the answer.
    return total / len(processes)
