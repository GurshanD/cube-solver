"""The ground truth: a sticker-level cube built from 3D geometry.

Every sticker has a position and an outward normal. A move is a real 90-degree
rotation of the stickers in one layer. Because the moves come from geometry
rather than hand-typed tables, they're correct by construction, and every other
model in this project (cubies, coordinates) is derived from or tested against
this one.

Axes: x points to R, y points to U, z points to F. Positions use doubled
integer coordinates so 2x2 (-1, 1) and 3x3 (-2, 0, 2) both stay integers.
"""

from __future__ import annotations

from functools import cache

FACES = "URFDLB"
NORMALS = {"U": (0, 1, 0), "R": (1, 0, 0), "F": (0, 0, 1), "D": (0, -1, 0), "L": (-1, 0, 0), "B": (0, 0, -1)}
FACE_OF_NORMAL = {v: k for k, v in NORMALS.items()}


# Clockwise quarter turn of each face, seen from outside that face.
def _rot_u(x, y, z): return (-z, y, x)
def _rot_d(x, y, z): return (z, y, -x)
def _rot_r(x, y, z): return (x, z, -y)
def _rot_l(x, y, z): return (x, -z, y)
def _rot_f(x, y, z): return (y, -x, z)
def _rot_b(x, y, z): return (-y, x, z)


ROTATIONS = {"U": _rot_u, "D": _rot_d, "R": _rot_r, "L": _rot_l, "F": _rot_f, "B": _rot_b}
AXIS = {"U": (1, 1), "D": (1, -1), "R": (0, 1), "L": (0, -1), "F": (2, 1), "B": (2, -1)}  # (axis, side)


def _face_cells(n: int, face: str):
    """Sticker cubie-positions of one face in standard reading order
    (U: back row first, F/R/L/B: top row first, D: front row first)."""
    m = n - 1
    r = range(-m, m + 1, 2)
    rev = range(m, -m - 1, -2)
    if face == "U":
        return [(x, m, z) for z in r for x in r]
    if face == "D":
        return [(x, -m, z) for z in rev for x in r]
    if face == "F":
        return [(x, y, m) for y in rev for x in r]
    if face == "B":
        return [(x, y, -m) for y in rev for x in rev]
    if face == "R":
        return [(m, y, z) for y in rev for z in rev]
    if face == "L":
        return [(-m, y, z) for y in rev for z in r]
    raise ValueError(face)


class Geometry:
    """Sticker layout and move permutations for an n x n x n cube."""

    def __init__(self, n: int):
        self.n = n
        self.stickers = [(pos, NORMALS[f]) for f in FACES for pos in _face_cells(n, f)]
        self.index = {s: i for i, s in enumerate(self.stickers)}
        self.solved = tuple(FACES.index(FACE_OF_NORMAL[nrm]) for _, nrm in self.stickers)
        self.moves = {f: self._layer_perm(f) for f in FACES}  # quarter turns
        self.cube_rotations = {"x": self._whole_perm("R"), "y": self._whole_perm("U"), "z": self._whole_perm("F")}

    def _perm(self, rot, selected):
        """Gather-permutation g with new[j] = old[g[j]]."""
        g = list(range(len(self.stickers)))
        for i, (pos, nrm) in enumerate(self.stickers):
            if selected(pos):
                j = self.index[(rot(*pos), rot(*nrm))]
                g[j] = i
        return tuple(g)

    def _layer_perm(self, face):
        axis, side = AXIS[face]
        edge = side * (self.n - 1)
        return self._perm(ROTATIONS[face], lambda p: p[axis] == edge)

    def _whole_perm(self, face):
        return self._perm(ROTATIONS[face], lambda p: True)

    def apply(self, state, face: str, turns: int = 1):
        g = self.moves[face]
        for _ in range(turns % 4):
            state = tuple(state[k] for k in g)
        return state

    def rotate(self, state, axis: str):
        g = self.cube_rotations[axis]
        return tuple(state[k] for k in g)

    def is_solved(self, state) -> bool:
        """Each face shows one colour (orientation of the whole cube doesn't matter)."""
        k = self.n * self.n
        return all(len(set(state[f * k:(f + 1) * k])) == 1 for f in range(6))

    def facelets(self, state) -> str:
        """54-character (or 24 for 2x2) string like 'UUUUUUUUURRR...' in URFDLB face order."""
        return "".join(FACES[c] for c in state)


@cache
def geometry(n: int) -> Geometry:
    if n not in (2, 3):
        raise ValueError("only 2x2 and 3x3 are supported")
    return Geometry(n)
