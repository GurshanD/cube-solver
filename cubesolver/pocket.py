"""2x2 specifics.

A 2x2 has no centres, so turning D is the same as turning U and then rotating
the whole cube. That means we can rotate any scrambled 2x2 so the DBL corner is
already in place, then solve using only U, R and F turns. That shrinks the
puzzle from 88 million positions to 3,674,160 and the branching factor from 18
moves to 9, which is what lets plain BFS solve a random 2x2.

The solution found in the rotated frame is translated back to the cube as you
hold it, so the moves shown match the scramble you typed.
"""

from __future__ import annotations

from functools import cache

from . import tables as T
from .cubie import SOLVED, CubieCube, all_moves


def corners_only(c: CubieCube) -> CubieCube:
    return CubieCube(c.cp, c.co)


@cache
def rotations() -> list[CubieCube]:
    """The 24 whole-cube rotations, as corner permutations. On a 2x2,
    rotating the whole cube = turning two opposite layers: y = U D', x = R L', z = F B'."""
    mv = all_moves()
    gens = [corners_only(mv[0] * mv[11]), corners_only(mv[3] * mv[14]), corners_only(mv[6] * mv[17])]
    seen = [corners_only(SOLVED)]
    frontier = list(seen)
    while frontier:
        new = []
        for r in frontier:
            for g in gens:
                x = r * g
                if x not in seen:
                    seen.append(x)
                    new.append(x)
        frontier = new
    assert len(seen) == 24
    return seen


@cache
def _move_lookup():
    return {corners_only(m): i for i, m in enumerate(all_moves())}


def normalize(c: CubieCube) -> tuple[int, CubieCube]:
    """Find the rotation that puts the DBL corner home, untwisted."""
    c = corners_only(c)
    for i, r in enumerate(rotations()):
        x = c * r
        if x.cp[6] == 6 and x.co[6] == 0:
            return i, x
    raise AssertionError("unreachable: some rotation always fixes DBL")


def translate(moves, rot_index: int) -> list[int]:
    """Moves found in the rotated frame -> the same physical turns in your frame.
    If X*r*M is solved then X*M'*r is too, where M' = r*M*r^-1."""
    r = rotations()[rot_index]
    rinv = r.inverse()
    lookup = _move_lookup()
    mv = all_moves()
    return [lookup[r * corners_only(mv[m]) * rinv] for m in moves]


def state_index(c: CubieCube) -> int:
    return T.cp7_coord(c) * T.N_CO6 + T.co6_coord(c)


def is_solved(c: CubieCube) -> bool:
    """A 2x2 is solved when it equals some whole-cube rotation of the solved cube."""
    return corners_only(c) in rotations()
