import pytest
from fastapi.testclient import TestClient

from cubesolver import notation as N
from cubesolver import pocket, solver
from cubesolver.api import create_app
from cubesolver.cubie import SOLVED, all_moves

OPTIMAL = ["bfs", "iddfs", "astar"]


def test_only_the_four_algorithms_are_offered():
    assert [a["id"] for a in solver.algorithms(2)] == ["bfs", "dfs", "iddfs", "astar"]
    assert [a["id"] for a in solver.algorithms(3)] == ["bfs", "dfs", "iddfs", "astar"]


@pytest.mark.parametrize("scramble", ["R", "R U", "R U F'", "R U2 F' L", "D R2 F L B'"])
def test_3x3_optimal_algorithms_agree_and_verify(scramble):
    results = solver.race(3, scramble, OPTIMAL + ["dfs"], seconds=20)
    for r in results:
        assert r["status"] == "solved" and r["verified"], r
    assert len({r["length"] for r in results if r["id"] in OPTIMAL}) == 1


def test_dfs_is_capped_by_scramble_length_and_verifies():
    r = solver.solve(3, "R U", "dfs")
    assert r["status"] == "solved" and r["verified"] and r["depth_limit"] == 2


@pytest.mark.parametrize("seed", range(5))
def test_2x2_random_scrambles_astar_and_iddfs_agree(seed):
    scr = solver.scramble(2, 25, seed=seed)
    a = solver.solve(2, scr, "astar")
    i = solver.solve(2, scr, "iddfs", seconds=30)
    assert a["verified"] and i["verified"]
    assert a["length"] == i["length"] <= 11


def test_3x3_astar_handles_9_moves():
    r = solver.solve(3, solver.scramble(3, 9, seed=1009), "astar")
    assert r["verified"] and r["length"] <= 9 and r["optimal"]


def test_2x2_solution_uses_your_orientation():
    """Scrambles using D/L/B are solved in the frame you hold the cube in."""
    scr = "D L' B2 D' L"
    r = solver.solve(2, scr, "astar")
    c = SOLVED
    for m in N.parse(scr) + r["moves"]:
        c = c * all_moves()[m]
    assert pocket.is_solved(c)


def test_limits_make_bfs_give_up_on_a_long_3x3_scramble():
    r = solver.solve(3, solver.scramble(3, 12, seed=1), "bfs", seconds=3)
    assert r["status"] == "limit" and r["length"] is None and not r["verified"]


def test_already_solved():
    for size in (2, 3):
        for algo in ("bfs", "dfs", "iddfs", "astar"):
            r = solver.solve(size, "", algo)
            assert r["status"] == "solved" and r["length"] == 0


def test_bad_input():
    with pytest.raises(ValueError):
        solver.solve(3, "R Q", "bfs")
    with pytest.raises(ValueError):
        solver.solve(3, "R", "kociemba")


def test_api():
    c = TestClient(create_app())
    assert c.get("/").status_code == 200
    assert c.get("/static/script.js").status_code == 200
    assert c.get("/api/preview?size=3&scramble=R").json()["state"][:9] == "UUFUUFUUF"
    assert [a["id"] for a in c.get("/api/algorithms?size=2").json()] == ["bfs", "dfs", "iddfs", "astar"]
    scr = c.get("/api/scramble?size=3&length=5").json()["scramble"]
    assert len(scr.split()) == 5
    r = c.post("/api/solve", json={"size": 3, "scramble": "R U R'", "algorithm": "astar"}).json()
    assert r["length"] == 3 and r["verified"] and r["optimal"]
    assert c.post("/api/solve", json={"size": 3, "scramble": "R Z", "algorithm": "bfs"}).status_code == 422


def test_random_scramble_seeded():
    assert solver.scramble(3, 10, seed=42) == solver.scramble(3, 10, seed=42)
