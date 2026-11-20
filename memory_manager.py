"""Tracks one contiguous memory as allocated blocks and free holes (Phase 4)."""

# The assignment gives every run 15,000 locations, numbered 0 to 14999.
# The whole memory starts as one hole of 15,000.
MEMORY_SIZE = 15000
FIRST_FIT = "First-Fit"
WORST_FIT = "Worst-Fit"


class MemoryManager:
    """Variable partitions: each process gets one block of exactly its size."""

    # Two lists describe memory, both kept in address order:
    #   blocks: {"process_id", "start", "size"} for every process holding memory
    #   holes:  {"start", "size"} for every free range
    # Together they cover every location exactly once. Holes are never left
    # side by side: release() merges neighbours straight away.

    def __init__(self, fit, size=MEMORY_SIZE):
        if fit not in (FIRST_FIT, WORST_FIT):
            raise ValueError(f"Memory allocation must be {FIRST_FIT} or {WORST_FIT}.")
        self.fit = fit
        self.size = size
        self.blocks = []
        self.holes = [{"start": 0, "size": size}]

    def free_total(self):
        """All free locations added together, even if they are split up."""
        return sum(hole["size"] for hole in self.holes)

    def largest_hole(self):
        return max((hole["size"] for hole in self.holes), default=0)

    def find_hole(self, size):
        """Picks a hole by the chosen rule, or None if no single hole is big enough."""
        fitting = [hole for hole in self.holes if hole["size"] >= size]
        if not fitting:
            return None
        if self.fit == FIRST_FIT:
            # Holes are in address order, so the first match is the lowest one.
            return fitting[0]
        # Worst-Fit: the largest hole. On a tie, max keeps the first one it
        # saw, which is the lowest address.
        return max(fitting, key=lambda hole: hole["size"])

    def needs_compaction(self, size):
        """Compaction helps only when no hole fits but the free total would."""
        return self.find_hole(size) is None and self.free_total() >= size

    def allocate(self, process_id, size):
        """Places a block at the start of the chosen hole; None if nothing fits."""
        hole = self.find_hole(size)
        if hole is None:
            return None
        block = {"process_id": process_id, "start": hole["start"], "size": size}
        # The block takes the front of the hole; whatever is left stays a hole.
        hole["start"] += size
        hole["size"] -= size
        if hole["size"] == 0:
            self.holes.remove(hole)
        self.blocks.append(block)
        self.blocks.sort(key=lambda b: b["start"])
        return block

    def release(self, process_id):
        """Frees a finished process's block and merges it with neighbouring holes."""
        block = self.block_of(process_id)
        if block is None:
            raise ValueError(f"Process {process_id} does not hold any memory.")
        self.blocks.remove(block)
        self.holes.append({"start": block["start"], "size": block["size"]})
        self.holes.sort(key=lambda hole: hole["start"])

        # Consolidate adjacent holes: a hole that begins exactly where the
        # previous one ends becomes part of it. This happens on every release,
        # so holes are always merged before any compaction is considered.
        merged = []
        for hole in self.holes:
            if merged and merged[-1]["start"] + merged[-1]["size"] == hole["start"]:
                merged[-1]["size"] += hole["size"]
            else:
                merged.append(hole)
        self.holes = merged

    def compact(self):
        """Slides every block down to address 0, leaving one hole at the top."""
        moves = []
        next_start = 0
        # Blocks are in address order, so each one moves down (or stays put)
        # and the order of processes in memory is kept.
        for block in self.blocks:
            if block["start"] != next_start:
                moves.append({"process_id": block["process_id"],
                              "from": block["start"], "to": next_start})
                block["start"] = next_start
            next_start += block["size"]
        self.holes = ([{"start": next_start, "size": self.size - next_start}]
                      if next_start < self.size else [])
        return moves

    def block_of(self, process_id):
        return next((b for b in self.blocks if b["process_id"] == process_id), None)

    def layout(self):
        """A snapshot of blocks and holes for reports; later changes do not alter it."""
        return {"blocks": [dict(b) for b in self.blocks],
                "holes": [dict(h) for h in self.holes]}
