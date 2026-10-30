"""Calculates Phase 2 CPU schedules without changing the process definitions."""


# The pcb manager supplies validated PCB objects. These functions only read them;
# they do not ask for input, print tables, or save files. This lets the menu
# and the tests use the same calculations.
# Both algorithms are non-preemptive: once a process starts, it finishes
# before another gets the CPU. Quantum and switch penalties are unused here.


def schedule_fcfs(pcbs): # First-Come, First-Served
    """Runs processes by arrival time; equal arrivals keep their input order."""

    # sorted makes a new list, leaving View and Save in their original order.
    # The lambda tells Python which field to sort by. Python's sort is stable:
    # records with the same arrival stay in their existing file/addition order.
    waiting = sorted(pcbs, key=lambda pcb: pcb.arrival_time)
    clock = 0
    results = []

    for pcb in waiting:
        # If the next process has not arrived, the CPU waits until it does.
        # max picks the later time without stepping through each idle cycle.
        start_time = max(clock, pcb.arrival_time)
        finish_time = start_time + pcb.cpu_required

        # Each dictionary holds the values for one completed process.
        # Turnaround includes waiting AND running, so subtract the arrival,
        # not the start. The list order is the order in which processes run.
        results.append({
            "process_id": pcb.process_id,
            "arrival_time": pcb.arrival_time,
            "cpu_required": pcb.cpu_required,
            "start_time": start_time,
            "finish_time": finish_time,
            "turnaround_time": finish_time - pcb.arrival_time
        })
        clock = finish_time

    # An empty input naturally produces an empty schedule.
    return results


def schedule_sjf(pcbs): # Shortest Job First
    """Runs the shortest available job each time the CPU becomes free."""

    # This copy holds references to the same PCBs, but has its own list order.
    # Removing a finished job from remaining does not remove it from the
    # manager. The PCB objects themselves are never changed during a run.
    remaining = list(pcbs)
    clock = 0
    results = []

    while remaining:
        # Ready means the process has arrived and is waiting for the CPU.
        # Rebuild this list after every completion because more jobs may
        # have arrived while the last one was running.
        ready_processes = [pcb for pcb in remaining if pcb.arrival_time <= clock]

        if not ready_processes:
            # Nobody can run yet. Jump to the next arrival and check again.
            # Even a very long idle gap takes just this one clock update.
            clock = min(pcb.arrival_time for pcb in remaining)
            continue

        # Compare CPU time first, then arrival time. On a complete tie, min
        # takes the first item in ready_processes, preserving file/addition
        # order. The process ID is a label, not a scheduling priority.
        pcb = min(ready_processes,
                  key=lambda pcb: (pcb.cpu_required, pcb.arrival_time))

        # Run the whole job. A shorter job arriving during this interval
        # waits until the next choice; it does not interrupt this process.
        start_time = clock
        finish_time = start_time + pcb.cpu_required
        results.append({
            "process_id": pcb.process_id,
            "arrival_time": pcb.arrival_time,
            "cpu_required": pcb.cpu_required,
            "start_time": start_time,
            "finish_time": finish_time,
            "turnaround_time": finish_time - pcb.arrival_time
        })
        clock = finish_time
        remaining.remove(pcb)

    return results


def average_turnaround(results):
    """Returns the mean turnaround, or None when no processes ran."""

    # An empty schedule has no average. Check before dividing by its count.
    if not results:
        return None

    total = sum(row["turnaround_time"] for row in results)
    # Regular division keeps fractions. Round only when displaying the answer.
    return total / len(results)
