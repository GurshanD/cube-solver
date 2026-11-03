"""How far can each algorithm go? Runs every algorithm on random 3x3 scrambles of
increasing length and on random 2x2 scrambles, and prints Markdown tables.

    python -m bench.benchmark                 # ~10 minutes
    python -m bench.benchmark --trials 5 --seconds 15

Once an algorithm fails every trial at some depth, deeper levels are skipped
(it will only get worse).
"""

from __future__ import annotations

import argparse
import statistics

from cubesolver import solver

ALGOS3 = ["bfs", "dfs", "iddfs", "astar"]
ALGOS2 = ["bfs", "dfs", "iddfs", "astar"]


def fmt_n(x):
    if x >= 1e6:
        return f"{x / 1e6:.1f}M"
    if x >= 1e3:
        return f"{x / 1e3:.1f}k"
    return str(int(x))


def cell(rs, trials):
    ok = [r for r in rs if r["status"] == "solved"]
    if not ok:
        return "✗"
    t = statistics.median(r["seconds"] for r in ok)
    n = statistics.median(r["expanded"] for r in ok)
    s = f"{fmt_n(n)} nodes, {t:.2f}s" if t >= 0.01 else f"{fmt_n(n)} nodes, <0.01s"
    return s if len(ok) == trials else f"{s} ({len(ok)}/{trials})"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--trials", type=int, default=3)
    p.add_argument("--seconds", type=float, default=10)
    p.add_argument("--max-depth", type=int, default=9)
    args = p.parse_args()

    depths = list(range(3, args.max_depth + 1))
    print(f"## 3x3: median positions examined and time ({args.trials} random scrambles per cell, "
          f"{args.seconds:g}s limit, ✗ = never solved)\n")
    print("| Algorithm | " + " | ".join(f"{d} moves" for d in depths) + " |")
    print("|---|" + "---|" * len(depths))
    for algo in ALGOS3:
        row = []
        dead = False
        for d in depths:
            if dead:
                row.append("✗")
                continue
            rs = [solver.solve(3, solver.scramble(3, d, seed=1000 * d + i), algo, seconds=args.seconds)
                  for i in range(args.trials)]
            c = cell(rs, args.trials)
            dead = c == "✗"
            row.append(c)
        print(f"| {solver.INFO[algo]['name']} | " + " | ".join(row) + " |", flush=True)

    print(f"\n## 2x2: fully random scrambles ({args.trials * 3} per algorithm)\n")
    print("| Algorithm | Solved | Median moves | Median positions | Median time | Peak memory (states) |")
    print("|---|---|---|---|---|---|")
    for algo in ALGOS2:
        rs = [solver.solve(2, solver.scramble(2, 25, seed=i), algo, seconds=args.seconds)
              for i in range(args.trials * 3)]
        ok = [r for r in rs if r["status"] == "solved"]
        if ok:
            def med(k, ok=ok):
                return statistics.median(r[k] for r in ok)

            print(f"| {solver.INFO[algo]['name']} | {len(ok)}/{len(rs)} | {med('length'):g} | {fmt_n(med('expanded'))} "
                  f"| {med('seconds'):.2f}s | {fmt_n(max(r['stored'] for r in rs))} |", flush=True)
        else:
            print(f"| {solver.INFO[algo]['name']} | 0/{len(rs)} | – | – | – | {fmt_n(max(r['stored'] for r in rs))} |",
                  flush=True)


if __name__ == "__main__":
    main()
