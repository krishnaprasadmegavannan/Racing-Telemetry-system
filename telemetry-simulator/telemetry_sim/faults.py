"""Network-fault injection: lose, duplicate and reorder packets after they are generated.

Faults are applied to the already-serialised line, so a duplicate is byte-identical to the
original (same sequence_number, same timestamp), exactly as a retransmission would be.
A separate RNG is used so turning faults on does not change the sensor values themselves.
"""
from __future__ import annotations

import random


def parse_seq_list(text: str | None) -> set[int]:
    """'15,16,40-45' -> {15, 16, 40, 41, 42, 43, 44, 45}"""
    out: set[int] = set()
    if not text:
        return out
    for part in text.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            out.update(range(int(a), int(b) + 1))
        elif part:
            out.add(int(part))
    return out


class FaultInjector:
    def __init__(self, rng: random.Random, drop_rate: float = 0.0, dup_rate: float = 0.0,
                 reorder_rate: float = 0.0, reorder_depth: int = 3,
                 drop_seqs: set[int] | None = None, dup_seqs: set[int] | None = None,
                 reorder_seqs: set[int] | None = None):
        self.rng = rng
        self.drop_rate, self.dup_rate, self.reorder_rate = drop_rate, dup_rate, reorder_rate
        self.reorder_depth = max(1, reorder_depth)
        self.drop_seqs = drop_seqs or set()
        self.dup_seqs = dup_seqs or set()
        self.reorder_seqs = reorder_seqs or set()
        self.held: list[list] = []      # [packets_remaining_before_release, line]

    def process(self, seq: int, line: str, apply_explicit: bool = True) -> tuple[list[str], list[str]]:
        """Returns (lines to transmit now, fault tags describing what happened to this packet).

        apply_explicit=False skips the --drop-seq/--dup-seq/--reorder-seq lists (used after a
        reboot, when sequence numbers restart and would otherwise be hit twice).
        """
        for h in self.held:
            h[0] -= 1
        released = [h[1] for h in self.held if h[0] <= 0]
        self.held = [h for h in self.held if h[0] > 0]

        explicit = apply_explicit
        rnd = self.rng.random
        tags: list[str] = []
        now: list[str] = []
        if (explicit and seq in self.drop_seqs) or rnd() < self.drop_rate:
            tags.append("dropped")
            return released, tags

        copies = 1
        if (explicit and seq in self.dup_seqs) or rnd() < self.dup_rate:
            copies = 2
            tags.append("duplicated")

        if (explicit and seq in self.reorder_seqs) or rnd() < self.reorder_rate:
            depth = self.reorder_depth if (explicit and seq in self.reorder_seqs) \
                else self.rng.randint(1, self.reorder_depth)
            for _ in range(copies):
                self.held.append([depth, line])
            tags.append(f"delayed_by_{depth}")
        else:
            now.extend([line] * copies)
        return now + released, tags

    def flush(self) -> list[str]:
        out = [h[1] for h in sorted(self.held, key=lambda h: h[0])]
        self.held = []
        return out
