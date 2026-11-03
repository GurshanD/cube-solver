import random

import pytest

from cubesolver import notation as N
from cubesolver.cubie import SOLVED, all_moves, basic_moves, from_stickers, to_stickers
from cubesolver.geometry import FACES, geometry


@pytest.mark.parametrize("n", [2, 3])
def test_every_face_turn_has_order_four(n):
    g = geometry(n)
    for f in FACES:
        s = g.solved
        for k in range(1, 5):
            s = g.apply(s, f)
            assert (s == g.solved) == (k == 4)


def test_moves_derived_from_geometry_match_kociembas_published_tables():
    m = basic_moves()
    assert m["U"].cp == (3, 0, 1, 2, 4, 5, 6, 7)
    assert m["R"].cp == (4, 1, 2, 0, 7, 5, 6, 3) and m["R"].co == (2, 0, 0, 1, 1, 0, 0, 2)
    assert m["F"].eo == (0, 1, 0, 0, 0, 1, 0, 0, 1, 1, 0, 0)
    assert m["B"].ep == (0, 1, 2, 11, 4, 5, 6, 10, 8, 9, 3, 7)


def test_sticker_and_cubie_models_agree_on_random_sequences():
    g = geometry(3)
    rng = random.Random(0)
    for _ in range(150):
        s, c = g.solved, SOLVED
        for m in N.random_scramble(30, rng):
            s = g.apply(s, FACES[m // 3], m % 3 + 1)
            c = c * all_moves()[m]
        assert from_stickers(s) == c
        assert to_stickers(c) == s
        assert c.is_valid()


def test_inverse_undoes_a_cube():
    c = SOLVED
    for m in N.parse("R U2 F' L D B2"):
        c = c * all_moves()[m]
    assert (c * c.inverse()).is_solved()


def test_sexy_move_has_order_six():
    seq = N.parse("R U R' U'")
    c = SOLVED
    for k in range(1, 7):
        for m in seq:
            c = c * all_moves()[m]
        assert c.is_solved() == (k == 6)


def test_parse_and_format():
    assert N.format(N.parse("r u' F2 B’ D3")) == "R U' F2 B' D'"
    assert N.parse("RUR'U'") == N.parse("R U R' U'")
    with pytest.raises(ValueError):
        N.parse("R X")


def test_simplify_and_invert():
    assert N.format(N.simplify(N.parse("R R U U' F2 F2 L"))) == "R2 L"
    assert N.format(N.invert(N.parse("R U F2"))) == "F2 U' R'"


def test_canonical_move_order_rules():
    assert not N.allowed_after(N.parse("R")[0], N.parse("R'")[0])  # same face
    assert N.allowed_after(N.parse("U")[0], N.parse("D")[0])  # U then D is fine...
    assert not N.allowed_after(N.parse("D")[0], N.parse("U")[0])  # ...D then U is the same thing


def test_random_scramble_has_no_redundant_pairs():
    seq = N.random_scramble(200, random.Random(1))
    assert all(N.allowed_after(a, b) for a, b in zip(seq, seq[1:]))
