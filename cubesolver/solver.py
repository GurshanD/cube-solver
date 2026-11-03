"""One entry point: solve(size, scramble, algorithm) and race(...) for BFS, DFS, IDDFS and A*."""

from __future__ import annotations

import random

from . import notation, pocket
from . import tables as T
from .cubie import SOLVED, CubieCube, all_moves
from .puzzles import CubeProblem, PocketProblem, encode
from .search import ALGORITHMS, Limits

GODS_NUMBER = {2: 11, 3: 20}

INFO = {
    "bfs": {"name": "Breadth-first search", "optimal": True, "memory": "huge",
            "how": "Tries every 1-move position, then every 2-move position, and so on. Guaranteed shortest, "
                   "but it has to remember every position it has seen, so it runs out of memory fast."},
    "dfs": {"name": "Depth-first search", "optimal": False, "memory": "tiny",
            "how": "Follows one sequence of moves as deep as allowed, then backtracks. Needs almost no memory, "
                   "but wanders down hopeless paths and returns whatever solution it trips over first."},
    "iddfs": {"name": "Iterative deepening DFS", "optimal": True, "memory": "tiny",
              "how": "Runs DFS with a depth limit of 1, then 2, then 3... Shortest solution like BFS with the "
                     "memory of DFS. The cost: shallow levels are searched again every round."},
    "astar": {"name": "A*", "optimal": True, "memory": "large",
              "how": "Expands the position with the lowest moves-so-far + estimated-moves-left first. The estimate "
                     "comes from lookup tables and never overshoots, so the answer is still shortest."},
}


def algorithms(size: int) -> list[dict]:
    return [{"id": k, **v} for k, v in INFO.items()]


def cube_from_moves(moves) -> CubieCube:
    c = SOLVED
    mv = all_moves()
    for m in moves:
        c = c * mv[m]
    return c


def verify(size: int, scramble, solution) -> bool:
    c = cube_from_moves(list(scramble) + list(solution))
    return pocket.is_solved(c) if size == 2 else c.is_solved()


def solve(size: int, scramble: str, algorithm: str, seconds: float = 15.0, depth: int | None = None) -> dict:
    if size not in (2, 3):
        raise ValueError("size must be 2 or 3")
    if algorithm not in INFO:
        raise ValueError(f"unknown algorithm '{algorithm}'. Choose from: {', '.join(INFO)}")
    moves = notation.parse(scramble)
    T.load()
    cube = cube_from_moves(moves)
    limits = Limits(seconds=seconds)
    # DFS needs a depth limit. Undoing the scramble is always a solution, so its length is a safe cap.
    limits.depth = depth or (min(len(moves), GODS_NUMBER[size]) if algorithm == "dfs" else GODS_NUMBER[size])

    if size == 2:
        rot, canon = pocket.normalize(cube)
        res = ALGORITHMS[algorithm](PocketProblem(pocket.state_index(canon)), limits)
        res.moves = pocket.translate(res.moves, rot)
    else:
        res = ALGORITHMS[algorithm](CubeProblem(encode(cube)), limits)

    out = res.to_dict()
    out["id"] = algorithm
    out["name"] = INFO[algorithm]["name"]
    out["verified"] = res.status == "solved" and verify(size, moves, res.moves)
    out["moves"] = res.moves
    out["states"] = sticker_states(size, moves, res.moves if res.status == "solved" else [])
    if algorithm == "dfs":
        out["depth_limit"] = limits.depth
    return out


def sticker_states(size: int, scramble_moves, solution_moves) -> list[str]:
    """The cube's stickers after the scramble, then after each solution move.
    The web page just draws these, so it doesn't need to know how moves work."""
    from .geometry import FACES, geometry

    g = geometry(size)
    s = g.solved
    for m in scramble_moves:
        s = g.apply(s, FACES[m // 3], m % 3 + 1)
    states = [g.facelets(s)]
    for m in solution_moves:
        s = g.apply(s, FACES[m // 3], m % 3 + 1)
        states.append(g.facelets(s))
    return states


def race(size: int, scramble: str, which: list[str] | None = None, seconds: float = 8.0) -> list[dict]:
    which = which or [a["id"] for a in algorithms(size)]
    return [solve(size, scramble, a, seconds=seconds) for a in which]


def scramble(size: int, length: int, seed: int | None = None) -> str:
    rng = random.Random(seed)
    # On a 2x2, U/R/F turns alone reach every position; a mix of all faces looks more natural though
    return notation.format(notation.random_scramble(length, rng))


__all__ = ["solve", "race", "scramble", "algorithms", "verify"]
