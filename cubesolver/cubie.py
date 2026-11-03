"""Cubie-level model: where each corner/edge piece is and how it's twisted.

Corners (slot order): URF UFL ULB UBR DFR DLF DBL DRB
Edges   (slot order): UR UF UL UB DR DF DL DB FR FL BL BR

A cube is (cp, co, ep, eo): cp[i] = which corner piece sits in slot i,
co[i] = its twist (0, 1, 2); same for edges with flip (0, 1).

The 6 basic face turns are *not* typed in by hand: they're computed by turning
the geometric sticker cube and reading the pieces back off it.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache

from .geometry import FACES, NORMALS, geometry

CORNERS = ["URF", "UFL", "ULB", "UBR", "DFR", "DLF", "DBL", "DRB"]
EDGES = ["UR", "UF", "UL", "UB", "DR", "DF", "DL", "DB", "FR", "FL", "BL", "BR"]

# Each slot's stickers, listed U/D sticker first, then clockwise around the piece.
CORNER_FACES = ["URF", "UFL", "ULB", "UBR", "DFR", "DLF", "DBL", "DRB"]
EDGE_FACES = ["UR", "UF", "UL", "UB", "DR", "DF", "DL", "DB", "FR", "FL", "BL", "BR"]


def _slot_stickers(n: int, faces: str):
    """Sticker indices of the piece touching exactly these faces, in this order."""
    g = geometry(n)
    m = n - 1
    pos = [0, 0, 0]
    for f in faces:
        axis = [i for i, v in enumerate(NORMALS[f]) if v][0]
        pos[axis] = NORMALS[f][axis] * m
    return [g.index[(tuple(pos), NORMALS[f])] for f in faces]


@dataclass(frozen=True)
class CubieCube:
    cp: tuple = tuple(range(8))
    co: tuple = (0,) * 8
    ep: tuple = tuple(range(12))
    eo: tuple = (0,) * 12

    def __mul__(self, b: CubieCube) -> CubieCube:
        """self * b = do self, then b (b given in 'replaced-by' form)."""
        a = self
        return CubieCube(
            tuple(a.cp[b.cp[i]] for i in range(8)),
            tuple((a.co[b.cp[i]] + b.co[i]) % 3 for i in range(8)),
            tuple(a.ep[b.ep[i]] for i in range(12)),
            tuple((a.eo[b.ep[i]] + b.eo[i]) % 2 for i in range(12)),
        )

    def inverse(self) -> CubieCube:
        cp = [0] * 8
        co = [0] * 8
        ep = [0] * 12
        eo = [0] * 12
        for i in range(8):
            cp[self.cp[i]] = i
        for i in range(8):
            co[i] = (-self.co[cp[i]]) % 3
        for i in range(12):
            ep[self.ep[i]] = i
        for i in range(12):
            eo[i] = self.eo[ep[i]]
        return CubieCube(tuple(cp), tuple(co), tuple(ep), tuple(eo))

    def is_solved(self) -> bool:
        return self == SOLVED

    def corner_parity(self) -> int:
        return _parity(self.cp)

    def edge_parity(self) -> int:
        return _parity(self.ep)

    def is_valid(self) -> bool:
        return (sorted(self.cp) == list(range(8)) and sorted(self.ep) == list(range(12))
                and sum(self.co) % 3 == 0 and sum(self.eo) % 2 == 0
                and self.corner_parity() == self.edge_parity())


def _parity(p) -> int:
    s = 0
    for i in range(len(p)):
        for j in range(i + 1, len(p)):
            if p[i] > p[j]:
                s ^= 1
    return s


SOLVED = CubieCube()


def from_stickers(state, n: int = 3) -> CubieCube:
    """Read pieces off a sticker state (Kociemba's facelet -> cubie method)."""
    corner_slots = [_slot_stickers(n, f) for f in CORNER_FACES]
    ud = (FACES.index("U"), FACES.index("D"))
    corner_colors = [tuple(FACES.index(c) for c in f) for f in CORNER_FACES]
    cp, co = [0] * 8, [0] * 8
    for i, slot in enumerate(corner_slots):
        cols = [state[k] for k in slot]
        ori = next(o for o in range(3) if cols[o] in ud)
        c1, c2 = cols[(ori + 1) % 3], cols[(ori + 2) % 3]
        j = next(j for j, cc in enumerate(corner_colors) if cc[1] == c1 and cc[2] == c2)
        cp[i], co[i] = j, ori
    if n == 2:
        return CubieCube(tuple(cp), tuple(co))

    edge_slots = [_slot_stickers(n, f) for f in EDGE_FACES]
    edge_colors = [tuple(FACES.index(c) for c in f) for f in EDGE_FACES]
    ep, eo = [0] * 12, [0] * 12
    for i, slot in enumerate(edge_slots):
        a, b = state[slot[0]], state[slot[1]]
        for j, (x, y) in enumerate(edge_colors):
            if (a, b) == (x, y):
                ep[i], eo[i] = j, 0
                break
            if (a, b) == (y, x):
                ep[i], eo[i] = j, 1
                break
    return CubieCube(tuple(cp), tuple(co), tuple(ep), tuple(eo))


def to_stickers(c: CubieCube, n: int = 3):
    """Paint stickers from a cubie cube (inverse of from_stickers)."""
    g = geometry(n)
    state = list(g.solved)  # centres stay put
    for i, slot in enumerate(_slot_stickers(n, f) for f in CORNER_FACES):
        piece = [FACES.index(ch) for ch in CORNER_FACES[c.cp[i]]]
        for k in range(3):
            state[slot[(k + c.co[i]) % 3]] = piece[k]
    if n == 3:
        for i, slot in enumerate(_slot_stickers(n, f) for f in EDGE_FACES):
            piece = [FACES.index(ch) for ch in EDGE_FACES[c.ep[i]]]
            for k in range(2):
                state[slot[(k + c.eo[i]) % 2]] = piece[k]
    return tuple(state)


@cache
def basic_moves() -> dict[str, CubieCube]:
    """U R F D L B quarter turns as cubie cubes, derived from the geometry."""
    g = geometry(3)
    return {f: from_stickers(g.apply(g.solved, f), 3) for f in FACES}


@cache
def all_moves() -> list[CubieCube]:
    """18 moves indexed face*3 + k: k=0 clockwise, 1 half turn, 2 counter-clockwise."""
    out = []
    for f in FACES:
        q = basic_moves()[f]
        out += [q, q * q, q * q * q]
    return out
