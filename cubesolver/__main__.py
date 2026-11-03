"""Command line.

    python -m cubesolver                       # web app on http://localhost:8001
    python -m cubesolver solve "R U R' U'"     # solve from the terminal
    python -m cubesolver solve "R U F" --size 2 --algo bfs
    python -m cubesolver solve random --size 2      # a fully random 2x2
    python -m cubesolver race "R U R' F2 D"    # every algorithm on one scramble
"""

from __future__ import annotations

import argparse
import logging


def _print_result(r: dict):
    if r["status"] == "solved":
        tag = "optimal" if r["optimal"] else "not guaranteed shortest"
        print(f"{r['name']:<26} {r['length']:>3} moves ({tag})  {r['solution']}")
    else:
        print(f"{r['name']:<26} gave up: {r['note']}")
    print(f"{'':<26} {r['expanded']:,} states expanded, {r['stored']:,} stored at peak, {r['seconds']:.3f}s")


def main(argv=None):
    p = argparse.ArgumentParser(prog="cubesolver")
    sub = p.add_subparsers(dest="cmd")
    s = sub.add_parser("serve", help="run the web app (default)")
    s.add_argument("--port", type=int, default=8001)
    s.add_argument("--host", default="127.0.0.1")
    for name in ("solve", "race"):
        q = sub.add_parser(name)
        q.add_argument("scramble", help="e.g. \"R U R' U'\" or 'random'")
        q.add_argument("--size", type=int, choices=[2, 3], default=3)
        q.add_argument("--seconds", type=float, default=10)
        if name == "solve":
            q.add_argument("--algo", default=None,
                           help="bfs, dfs, iddfs or astar (default astar)")
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if args.cmd in (None, "serve"):
        import uvicorn

        from .api import create_app

        port = getattr(args, "port", 8001)
        host = getattr(args, "host", "127.0.0.1")
        print(f"Cube solver running at http://localhost:{port}")
        uvicorn.run(create_app(), host=host, port=port, log_level="warning")
        return

    from . import solver

    scramble = args.scramble
    if scramble == "random":
        scramble = solver.scramble(args.size, 25)
    print(f"Scramble ({args.size}x{args.size}): {scramble}\n")
    if args.cmd == "solve":
        algo = args.algo or "astar"
        _print_result(solver.solve(args.size, scramble, algo, seconds=args.seconds))
    else:
        for r in solver.race(args.size, scramble, seconds=args.seconds):
            _print_result(r)
            print()


if __name__ == "__main__":
    main()
