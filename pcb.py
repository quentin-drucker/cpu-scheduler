"""Defines the six values stored for one process and their individual checks."""


class PCB:
    """Keeps one process record together in a single object."""

    # I use a class to group the six related integers into one record.
    # PCB is the definition; each PCB(...) creates a separate process object.
    # Named attributes like pcb.memory make the fields easier to identify than
    # numbered positions in a six-item list. This object does not run a process.

    def __init__(
        self,
        process_id,
        memory,
        arrival_time,
        cpu_required,
        quantum,
        context_switch_penalty
    ):
        """Stores the supplied values and checks them as soon as the PCB is created."""

        # self refers to this particular PCB. Each object has its own six values.
        self.process_id = process_id
        self.memory = memory
        self.arrival_time = arrival_time
        self.cpu_required = cpu_required
        self.quantum = quantum
        self.context_switch_penalty = context_switch_penalty

        # An invalid record should be rejected at creation, not stored for later.
        self.validate()

    def validate(self):
        """Checks this PCB; rules involving other PCBs belong to PCBManager."""

        # isinstance checks the Python value type. File and menu input also pass
        # through int() before reaching this point.
        if not isinstance(self.process_id, int):
            raise ValueError("Process ID must be an integer.")

        if not isinstance(self.memory, int):
            raise ValueError("Memory must be an integer.")

        if not isinstance(self.arrival_time, int):
            raise ValueError("Arrival time must be an integer.")

        if not isinstance(self.cpu_required, int):
            raise ValueError("CPU required must be an integer.")

        if not isinstance(self.quantum, int):
            raise ValueError("Quantum must be an integer.")

        if not isinstance(self.context_switch_penalty, int):
            raise ValueError("Context-switch penalty must be an integer.")

        # Memory must be positive. Phases 1 and 2 do not enforce a total limit.
        # The assignment also does not require a positive process ID.
        if self.memory <= 0:
            raise ValueError("Memory must be greater than 0.")

        # Arrival at time zero is allowed, but a negative arrival is not.
        if self.arrival_time < 0:
            raise ValueError("Arrival time must be 0 or greater.")

        # A process must require at least some CPU time.
        if self.cpu_required <= 0:
            raise ValueError("CPU required must be greater than 0.")

        # Quantum and penalty must be positive here. The manager checks that
        # they match the other processes in the set.
        if self.quantum <= 0:
            raise ValueError("Quantum must be greater than 0.")

        if self.context_switch_penalty <= 0:
            raise ValueError("Context-switch penalty must be greater than 0.")

    def __str__(self):
        """Builds a readable description, also used by the removal confirmation."""

        # Adjacent strings inside these parentheses form one description.
        # The table and saved-file format are handled elsewhere.
        return (
            f"PCB(process_id={self.process_id}, "
            f"memory={self.memory}, "
            f"arrival_time={self.arrival_time}, "
            f"cpu_required={self.cpu_required}, "
            f"quantum={self.quantum}, "
            f"context_switch_penalty={self.context_switch_penalty})"
        )
