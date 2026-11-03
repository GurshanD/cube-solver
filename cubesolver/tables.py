"""Coordinates, move tables and distance (pruning) tables.

A *coordinate* squeezes one aspect of the cube into a single integer, e.g.
"twist" = the orientation of all corners = a number from 0 to 2186. Instead of
turning a whole cube to see what a move does to its twist, we look it up:
twist_move[twist][move]. Distance tables store, for every coordinate value,
the fewest moves needed to solve that aspect; they're filled by breadth-first
search outward from the solved state, done in bulk with numpy.

Everything is built once (about 15 seconds) and cached on disk.
"""

from __future__ import annotations

import itertools
import logging
import os
import threading
import time
from pathlib import Path

import numpy as np

from .cubie import all_moves

log = logging.getLogger("cubesolver.tables")

VERSION = 2
N_TWIST, N_FLIP, N_SLICE, N_PERM8, N_SP = 2187, 2048, 495, 40320, 24
N_CP7, N_CO6 = 5040, 729
POCKET_MOVES = list(range(9))  # U, R, F families: they never move the DBL corner

_COMBOS = list(itertools.combinations(range(12), 4))
_COMBO_INDEX = np.full(4096, -1, dtype=np.int32)
for _i, _c in enumerate(_COMBOS):
    _COMBO_INDEX[sum(1 << p for p in _c)] = _i
SLICE_SOLVED = _COMBOS.index((8, 9, 10, 11))


def rank_perms(a: np.ndarray) -> np.ndarray:
    """Lexicographic rank of each row (a permutation of 0..k-1), vectorised."""
    k = a.shape[1]
    r = np.zeros(a.shape[0], dtype=np.int64)
    for i in range(k):
        r = r * (k - i) + (a[:, i + 1:] < a[:, i:i + 1]).sum(axis=1)
    return r


def all_perms(k: int) -> np.ndarray:
    return np.array(list(itertools.permutations(range(k))), dtype=np.int8)


def _orientations(n_free: int, total: int, base: int) -> np.ndarray:
    """All orientation vectors: n_free digits, the last piece fixed by the sum rule."""
    digits = np.array(list(itertools.product(range(base), repeat=n_free)), dtype=np.int8)
    last = (-digits.sum(axis=1)) % base
    out = np.zeros((len(digits), total), dtype=np.int8)
    out[:, :n_free] = digits
    out[:, total - 1] = last
    return out


def _digits_to_int(a: np.ndarray, base: int) -> np.ndarray:
    r = np.zeros(a.shape[0], dtype=np.int64)
    for i in range(a.shape[1]):
        r = r * base + a[:, i]
    return r


# ---------------------------------------------------------------- coordinates of a CubieCube
def twist(c) -> int:
    r = 0
    for i in range(7):
        r = r * 3 + c.co[i]
    return r


def flip(c) -> int:
    r = 0
    for i in range(11):
        r = r * 2 + c.eo[i]
    return r


def slice_coord(c) -> int:
    return int(_COMBO_INDEX[sum(1 << i for i in range(12) if c.ep[i] >= 8)])


def perm_rank(p) -> int:
    k = len(p)
    r = 0
    for i in range(k):
        r = r * (k - i) + sum(1 for j in range(i + 1, k) if p[j] < p[i])
    return r


def cp_coord(c) -> int:
    return perm_rank(c.cp)


# 2x2: slot 6 (DBL) is held fixed, the other 7 slots/pieces are relabelled 0..6
POCKET_SLOTS = [0, 1, 2, 3, 4, 5, 7]
_PIECE7 = {p: i for i, p in enumerate(POCKET_SLOTS)}


def cp7_coord(c) -> int:
    return perm_rank([_PIECE7[c.cp[s]] for s in POCKET_SLOTS])


def co6_coord(c) -> int:
    r = 0
    for i in range(6):
        r = r * 3 + c.co[i]
    return r


# ---------------------------------------------------------------- building
def _build_move_tables() -> dict[str, np.ndarray]:
    moves = all_moves()
    t = {}

    co = _orientations(7, 8, 3)  # row index == twist coordinate
    t["twist"] = np.stack([_digits_to_int(((co[:, m.cp] + np.array(m.co)) % 3)[:, :7], 3) for m in moves], 1)

    eo = _orientations(11, 12, 2)
    t["flip"] = np.stack([_digits_to_int(((eo[:, m.ep] + np.array(m.eo)) % 2)[:, :11], 2) for m in moves], 1)

    occ = np.zeros((N_SLICE, 12), dtype=np.int64)
    for i, c in enumerate(_COMBOS):
        occ[i, list(c)] = 1
    weights = 1 << np.arange(12)
    t["slice"] = np.stack([_COMBO_INDEX[(occ[:, m.ep] * weights).sum(1)] for m in moves], 1)

    p8 = all_perms(8)
    t["cp"] = np.stack([rank_perms(p8[:, m.cp]) for m in moves], 1)

    # 2x2 coordinates under U/R/F moves
    p7 = all_perms(7)
    t["cp7"] = np.stack([rank_perms(p7[:, [_PIECE7[moves[i].cp[s]] for s in POCKET_SLOTS]]) for i in POCKET_MOVES], 1)
    co8 = np.zeros((N_CO6, 8), dtype=np.int8)
    co8[:, :6] = np.array(list(itertools.product(range(3), repeat=6)))
    co8[:, 7] = (-co8[:, :6].sum(1)) % 3
    t["co6"] = np.stack([_digits_to_int(((co8[:, moves[i].cp] + np.array(moves[i].co)) % 3)[:, :6], 3)
                         for i in POCKET_MOVES], 1)
    return {k: v.astype(np.int32) for k, v in t.items()}


def bfs_distances(mt_a: np.ndarray, mt_b: np.ndarray | None, start: int) -> np.ndarray:
    """Distance from `start` for every value of the combined coordinate a * nb + b,
    expanding one whole BFS layer at a time with numpy."""
    na = mt_a.shape[0]
    nb = 1 if mt_b is None else mt_b.shape[0]
    dist = np.full(na * nb, -1, dtype=np.int8)
    dist[start] = 0
    frontier = np.array([start], dtype=np.int64)
    depth = 0
    while frontier.size:
        a, b = np.divmod(frontier, nb)
        nxt = mt_a[a].astype(np.int64) * nb
        if mt_b is not None:
            nxt += mt_b[b]
        nxt = np.unique(nxt.ravel())
        nxt = nxt[dist[nxt] < 0]
        depth += 1
        dist[nxt] = depth
        frontier = nxt
    return dist


def _build() -> dict[str, np.ndarray]:
    t0 = time.time()
    mt = _build_move_tables()
    log.info("move tables built in %.1fs", time.time() - t0)
    t = dict(mt)
    t["p1_twist_slice"] = bfs_distances(mt["twist"], mt["slice"], 0 * N_SLICE + SLICE_SOLVED)
    t["p1_flip_slice"] = bfs_distances(mt["flip"], mt["slice"], 0 * N_SLICE + SLICE_SOLVED)
    t["d_cp"] = bfs_distances(mt["cp"], None, 0)
    t["d_cp7"] = bfs_distances(mt["cp7"], None, 0)
    t["d_co6"] = bfs_distances(mt["co6"], None, 0)
    log.info("all tables built in %.1fs", time.time() - t0)
    return t


def cache_path() -> Path:
    base = Path(os.getenv("CUBESOLVER_CACHE", Path.home() / ".cache" / "cubesolver"))
    return base / f"tables-v{VERSION}.npz"


_tables: dict[str, np.ndarray] | None = None
_lock = threading.Lock()


def load() -> dict[str, np.ndarray]:
    """Load tables from the disk cache, building them on first use."""
    global _tables
    with _lock:
        if _tables is None:
            path = cache_path()
            if path.exists():
                with np.load(path) as z:
                    _tables = {k: z[k] for k in z.files}
            else:
                log.info("building lookup tables (first run only, ~15s)...")
                _tables = _build()
                path.parent.mkdir(parents=True, exist_ok=True)
                tmp = path.with_suffix(".tmp.npz")
                np.savez_compressed(tmp, **_tables)
                tmp.replace(path)
        return _tables


def ready() -> bool:
    return _tables is not None
