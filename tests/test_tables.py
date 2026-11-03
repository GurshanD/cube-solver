import random

import numpy as np

from cubesolver import notation as N
from cubesolver import tables as T
from cubesolver.cubie import SOLVED, all_moves


def random_cube(rng, length=30):
    c = SOLVED
    for m in N.random_scramble(length, rng):
        c = c * all_moves()[m]
    return c


def test_full_2x2_bfs_matches_published_distribution():
    """BFS over every 2x2 position. The count at each distance must match the published
    numbers exactly, which only happens if the move model is right."""
    t = T.load()
    known = [1, 9, 54, 321, 1847, 9992, 50136, 227536, 870072, 1887748, 623800, 2644]
    assert np.bincount(T.bfs_distances(t["cp7"], t["co6"], 0)).tolist() == known


def test_solved_coordinates():
    assert (T.twist(SOLVED), T.flip(SOLVED), T.slice_coord(SOLVED)) == (0, 0, T.SLICE_SOLVED)
    assert T.cp_coord(SOLVED) == 0


def test_move_tables_agree_with_turning_real_cubes():
    t = T.load()
    rng = random.Random(2)
    for _ in range(100):
        c = random_cube(rng)
        m = rng.randrange(18)
        d = c * all_moves()[m]
        assert t["twist"][T.twist(c), m] == T.twist(d)
        assert t["flip"][T.flip(c), m] == T.flip(d)
        assert t["slice"][T.slice_coord(c), m] == T.slice_coord(d)
        assert t["cp"][T.cp_coord(c), m] == T.cp_coord(d)


def test_heuristic_tables_never_overestimate_on_short_scrambles():
    t = T.load()
    rng = random.Random(4)
    for length in range(1, 8):
        for _ in range(20):
            c = random_cube(rng, length)
            h = max(t["p1_twist_slice"][T.twist(c) * T.N_SLICE + T.slice_coord(c)],
                    t["p1_flip_slice"][T.flip(c) * T.N_SLICE + T.slice_coord(c)],
                    t["d_cp"][T.cp_coord(c)])
            assert h <= length
