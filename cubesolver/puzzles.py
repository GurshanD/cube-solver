"""The two puzzles, packaged as search problems (start, goal, successors, h).

2x2 ("pocket cube"): state = one integer, corner permutation * 729 + corner twist,
with the DBL corner held still (see pocket.py for why that loses nothing).

3x3: state = 20 bytes, one per piece slot (8 corners then 12 edges); each byte
encodes which piece is there and how it's twisted/flipped.
"""

from __future__ import annotations

from . import notation
from . import tables as T
from .cubie import CubieCube, all_moves


class PocketProblem:
    name = "2x2"
    goal = 0

    def __init__(self, start: int):
        t = T.load()
        self.start = start
        self.cp_mt = t["cp7"].tolist()
        self.co_mt = t["co6"].tolist()
        self.d_cp = t["d_cp7"].tobytes()
        self.d_co = t["d_co6"].tobytes()
        self.moves = T.POCKET_MOVES

    def successors(self, s, last):
        cp, co = divmod(s, T.N_CO6)
        cpr, cor = self.cp_mt[cp], self.co_mt[co]
        return [(m, cpr[m] * T.N_CO6 + cor[m]) for m in self.moves if notation.allowed_after(last, m)]

    def h(self, s):
        """Moves needed to fix corner positions alone, or twists alone; the larger
        is still never more than the real answer."""
        cp, co = divmod(s, T.N_CO6)
        return max(self.d_cp[cp], self.d_co[co])


def encode(c: CubieCube) -> bytes:
    return bytes([c.cp[i] * 3 + c.co[i] for i in range(8)] + [c.ep[i] * 2 + c.eo[i] for i in range(12)])


def decode(b: bytes) -> CubieCube:
    return CubieCube(tuple(v // 3 for v in b[:8]), tuple(v % 3 for v in b[:8]),
                     tuple(v // 2 for v in b[8:]), tuple(v % 2 for v in b[8:]))


SOLVED_BYTES = encode(CubieCube())


def _move_specs():
    """For each move: per slot, (source slot, lookup table that adds the twist/flip)."""
    corner_add = [[(v // 3) * 3 + (v % 3 + t) % 3 for v in range(24)] for t in range(3)]
    edge_add = [[(v // 2) * 2 + (v % 2 + t) % 2 for v in range(24)] for t in range(2)]
    specs = []
    for mv in all_moves():
        spec = [(mv.cp[i], corner_add[mv.co[i]]) for i in range(8)]
        spec += [(8 + mv.ep[i], edge_add[mv.eo[i]]) for i in range(12)]
        specs.append(spec)
    return specs


_SPECS = _move_specs()


def apply_move(s: bytes, m: int) -> bytes:
    return bytes([tab[s[src]] for src, tab in _SPECS[m]])


class CubeProblem:
    name = "3x3"
    goal = SOLVED_BYTES

    def __init__(self, start: bytes):
        t = T.load()
        self.start = start
        self.p1a = t["p1_twist_slice"].tobytes()
        self.p1b = t["p1_flip_slice"].tobytes()
        self.d_cp = t["d_cp"].tobytes()
        self.combo = T._COMBO_INDEX.tolist()
        self.tw_w = [[(v % 3) * 3 ** (6 - i) for v in range(24)] for i in range(7)]
        self.fl_w = [[(v % 2) * 2 ** (10 - i) for v in range(24)] for i in range(11)]
        self.sl_w = [[(1 << i) if v // 2 >= 8 else 0 for v in range(24)] for i in range(12)]

    def successors(self, s, last):
        return [(m, bytes([tab[s[src]] for src, tab in _SPECS[m]]))
                for m in range(18) if notation.allowed_after(last, m)]

    def h(self, s):
        """Max of three 'relaxed' distances (each ignores part of the cube, so each
        is a lower bound): corner twist + slice edges, edge flip + slice edges,
        corner positions."""
        tw = sum(self.tw_w[i][s[i]] for i in range(7))
        fl = sum(self.fl_w[i][s[8 + i]] for i in range(11))
        sl = self.combo[sum(self.sl_w[i][s[8 + i]] for i in range(12))]
        cp = T.perm_rank([v // 3 for v in s[:8]])
        return max(self.p1a[tw * T.N_SLICE + sl], self.p1b[fl * T.N_SLICE + sl], self.d_cp[cp])
