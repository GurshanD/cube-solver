"""Generic search algorithms, written once and run on any puzzle.

A puzzle ("problem") provides:
    start                  the scrambled state
    goal                   the solved state
    successors(s, last)    [(move, next_state), ...], skipping redundant moves after `last`
    h(s)                   admissible estimate of moves left (never overestimates)

Every algorithm counts what it does, so they can be compared fairly:
    expanded  states whose successors were generated
    stored    the most states held in memory at once (BFS's weakness)
and stops cleanly when it hits a time, node, memory or depth limit.
"""

from __future__ import annotations

import heapq
import time
from collections import deque
from dataclasses import dataclass, field

from . import notation


@dataclass
class Limits:
    seconds: float = 15.0
    expanded: int = 3_000_000
    stored: int = 1_500_000  # roughly 300 MB of Python objects for 3x3 states
    depth: int = 20


@dataclass
class Result:
    algorithm: str
    status: str  # "solved" | "limit" | "not_found"
    moves: list[int] = field(default_factory=list)
    expanded: int = 0
    generated: int = 0
    stored: int = 0
    seconds: float = 0.0
    optimal: bool = False  # True when the algorithm guarantees the shortest solution and finished
    note: str = ""

    def to_dict(self) -> dict:
        return {
            "algorithm": self.algorithm,
            "status": self.status,
            "solution": notation.format(self.moves),
            "length": len(self.moves) if self.status == "solved" else None,
            "expanded": self.expanded,
            "generated": self.generated,
            "stored": self.stored,
            "seconds": round(self.seconds, 4),
            "optimal": self.optimal and self.status == "solved",
            "note": self.note,
        }


class LimitReached(Exception):
    pass


class Counter:
    """Shared bookkeeping + limit checks (time is checked every 2048 nodes; it's slow to read)."""

    def __init__(self, limits: Limits):
        self.limits = limits
        self.start = time.perf_counter()
        self.deadline = self.start + limits.seconds
        self.expanded = 0
        self.generated = 0
        self.stored = 0
        self.why = ""

    def expand(self, stored_now: int = 0):
        self.expanded += 1
        if stored_now > self.stored:
            self.stored = stored_now
            if stored_now > self.limits.stored:
                self.why = f"memory limit: {self.limits.stored:,} states stored"
                raise LimitReached
        if self.expanded > self.limits.expanded:
            self.why = f"node limit: {self.limits.expanded:,} states expanded"
            raise LimitReached
        if self.expanded & 2047 == 0 and time.perf_counter() > self.deadline:
            self.why = f"time limit: {self.limits.seconds:g}s"
            raise LimitReached

    def result(self, name, status, moves=(), optimal=False, note="") -> Result:
        return Result(name, status, list(moves), self.expanded, self.generated, self.stored,
                      time.perf_counter() - self.start, optimal, note or self.why)


def _path(parent, s):
    moves = []
    while parent[s] is not None:
        s, m = parent[s]
        moves.append(m)
    return moves[::-1]


# ---------------------------------------------------------------- uninformed
def bfs(p, limits: Limits) -> Result:
    """Breadth-first: explores every state 1 move away, then 2, ... Always finds the
    shortest solution, but must remember every state it has seen."""
    c = Counter(limits)
    if p.start == p.goal:
        return c.result("bfs", "solved", [], True)
    parent = {p.start: None}
    last = {p.start: None}
    queue = deque([p.start])
    try:
        while queue:
            s = queue.popleft()
            c.expand(len(parent))
            for m, t in p.successors(s, last[s]):
                c.generated += 1
                if t in parent:
                    continue
                parent[t] = (s, m)
                last[t] = m
                if t == p.goal:
                    return c.result("bfs", "solved", _path(parent, t), True)
                queue.append(t)
    except LimitReached:
        return c.result("bfs", "limit")
    return c.result("bfs", "not_found")


def dfs(p, limits: Limits) -> Result:
    """Depth-first: follows one line of moves as deep as allowed before backtracking.
    Tiny memory, but the first solution it stumbles on is usually long."""
    c = Counter(limits)
    path: list[int] = []

    def go(s, depth_left, last):
        if s == p.goal:
            return True
        if depth_left == 0:
            return False
        c.expand(len(path))
        for m, t in p.successors(s, last):
            c.generated += 1
            path.append(m)
            if go(t, depth_left - 1, m):
                return True
            path.pop()
        return False

    try:
        found = go(p.start, limits.depth, None)
    except LimitReached:
        return c.result("dfs", "limit")
    if found:
        return c.result("dfs", "solved", notation.simplify(path))
    return c.result("dfs", "not_found", note=f"no solution within {limits.depth} moves")


def iddfs(p, limits: Limits) -> Result:
    """Iterative deepening: DFS with depth limit 0, 1, 2, ... Shortest solution like
    BFS, tiny memory like DFS; the price is re-exploring shallow levels each round."""
    c = Counter(limits)
    path: list[int] = []

    def go(s, depth_left, last):
        if depth_left == 0:
            return s == p.goal
        c.expand(len(path))
        for m, t in p.successors(s, last):
            c.generated += 1
            path.append(m)
            if go(t, depth_left - 1, m):
                return True
            path.pop()
        return False

    try:
        for limit in range(limits.depth + 1):
            if go(p.start, limit, None):
                return c.result("iddfs", "solved", path, True)
    except LimitReached:
        return c.result("iddfs", "limit")
    return c.result("iddfs", "not_found", note=f"no solution within {limits.depth} moves")


# ---------------------------------------------------------------- informed (heuristic)
def astar(p, limits: Limits) -> Result:
    """A*: always expands the state with the lowest (moves so far + estimated moves left).
    With an estimate that never overshoots, the first solution found is the shortest."""
    c = Counter(limits)
    g = {p.start: 0}
    parent = {p.start: None}
    last = {p.start: None}
    tie = 0
    heap = [(p.h(p.start), 0, tie, p.start)]
    try:
        while heap:
            f, gs, _, s = heapq.heappop(heap)
            if gs > g[s]:
                continue  # stale entry
            if s == p.goal:
                return c.result("astar", "solved", _path(parent, s), True)
            c.expand(len(g))
            for m, t in p.successors(s, last[s]):
                c.generated += 1
                gt = gs + 1
                if gt < g.get(t, 1 << 30):
                    g[t] = gt
                    parent[t] = (s, m)
                    last[t] = m
                    tie += 1
                    heapq.heappush(heap, (gt + p.h(t), gt, tie, t))
    except LimitReached:
        return c.result("astar", "limit")
    return c.result("astar", "not_found")


ALGORITHMS = {
    "bfs": bfs,
    "dfs": dfs,
    "iddfs": iddfs,
    "astar": astar,
}
