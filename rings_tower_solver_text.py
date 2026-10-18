#!/usr/bin/env python3
"""Rings Tower solver: fewest-move solution via A* search.

Colours are entered as numbers: 1=red 2=yellow 3=cyan 4=purple.

Usage
  python rings_tower_solver.py              (asks you for each tube)
  python rings_tower_solver.py 121344 ...   (one string per tube, bottom -> top)
  python rings_tower_solver.py --random [--seed N]
  python rings_tower_solver.py --demo
Use "." for an empty tube, e.g.  python rings_tower_solver.py 121344 ... .
"""

from __future__ import annotations

import argparse
import heapq
import random

NAMES = {"1": "red", "2": "yellow", "3": "cyan", "4": "purple"}

Tube = tuple[str, ...]
State = tuple[Tube, ...]
Move = tuple[int, int, int]  # (from_tube, to_tube, rings_moved), 0-indexed tubes


def top_run(tube: Tube) -> int:
    """Number of same-coloured rings stacked together at the top."""
    if not tube:
        return 0
    n = 1
    while n < len(tube) and tube[-1 - n] == tube[-1]:
        n += 1
    return n


def is_solved(state: State) -> bool:
    seen: set[str] = set()
    for tube in state:
        if not tube:
            continue
        if len(set(tube)) != 1:
            return False
        if tube[0] in seen:  # same colour split across two tubes
            return False
        seen.add(tube[0])
    return True


def moves(state: State, cap: int, match: bool = False) -> list[Move]:
    out: list[Move] = []
    for i, src in enumerate(state):
        run = top_run(src)
        if run == 0:
            continue
        colour = src[-1]
        for j, dst in enumerate(state):
            if i == j or len(dst) >= cap:
                continue
            if match and dst and dst[-1] != colour:
                continue
            # Moving a whole tube onto an empty tube just swaps tubes: useless.
            if not dst and run == len(src):
                continue
            out.append((i, j, min(run, cap - len(dst))))  # overflow splits
    return out


def apply(state: State, move: Move) -> State:
    i, j, run = move
    t = list(state)
    t[j] = t[j] + t[i][-run:]
    t[i] = t[i][:-run]
    return tuple(t)


def runs(state: State) -> int:
    """Total number of maximal same-colour runs across all tubes."""
    total = 0
    for t in state:
        for k, ring in enumerate(t):
            if k == 0 or t[k - 1] != ring:
                total += 1
    return total


def heuristic(state: State, n_colours: int) -> int:
    """Lower bound on moves left.

    A move lifts a run (or part of it) off a tube and drops it on another.
    Fully lifting a run is -1 run; landing on an empty tube is +1, on a
    matching top is 0; a partial lift removes nothing. Net is never below -1. So one move removes at most one run, and the goal has exactly one
    run per colour. This never overestimates, so A* stays optimal.
    """
    return runs(state) - n_colours


def solve(start: State, cap: int = 6, match: bool = False) -> list[Move] | None:
    """Return a shortest list of moves, or None if unsolvable (A*)."""
    if is_solved(start):
        return []
    n_col = len({r for t in start for r in t})
    # Tubes are interchangeable, so sort them to build the visited key.
    key = lambda s: tuple(sorted(s))  # noqa: E731
    k0 = key(start)
    parent: dict[State, tuple[State, Move] | None] = {k0: None}
    best_g: dict[State, int] = {k0: 0}
    tick = 0
    heap = [(heuristic(start, n_col), heuristic(start, n_col), tick, 0, start)]
    while heap:
        _, _, _, g, cur = heapq.heappop(heap)
        kc = key(cur)
        if g > best_g[kc]:
            continue
        if is_solved(cur):
            return _path(parent, kc)
        for mv in moves(cur, cap, match):
            nxt = apply(cur, mv)
            kn = key(nxt)
            ng = g + 1
            if kn in best_g and best_g[kn] <= ng:
                continue
            best_g[kn] = ng
            parent[kn] = (kc, mv)
            tick += 1
            h = heuristic(nxt, n_col)
            # On equal f, prefer smaller h (closer to the goal).
            heapq.heappush(heap, (ng + h, h, tick, ng, nxt))
    return None


def _path(parent, end_key) -> list[Move]:
    chain: list[Move] = []
    k = end_key
    while parent[k] is not None:
        k, mv = parent[k]
        chain.append(mv)
    return chain[::-1]


def fmt_state(state: State, cap: int) -> str:
    return "  ".join(f"{''.join(t):<{cap}}" for t in state)


def parse(tubes: list[str]) -> State:
    out = []
    for t in tubes:
        t = t.replace(" ", "").replace(",", "")
        if t in {".", "-"}:
            t = ""
        bad = [c for c in t if c not in NAMES]
        if bad:
            raise SystemExit(f"Bad colour {bad[0]!r} in tube {t!r}: use 1-4 "
                             "(1=red 2=yellow 3=cyan 4=purple).")
        out.append(tuple(t))
    return tuple(out)


def ask_tubes(n_tubes: int = 5, cap: int = 6) -> State:
    print("1=red  2=yellow  3=cyan  4=purple")
    print(f"Type each tube bottom -> top (up to {cap} digits), e.g. 121344."
          " Press Enter for an empty tube.\n")
    tubes = []
    for k in range(1, n_tubes + 1):
        while True:
            t = input(f"Tube {k}: ").strip() or "."
            if len(t.replace(" ", "").replace(",", "").replace(".", "")) > cap:
                print(f"  A tube holds at most {cap} rings, try again.")
                continue
            tubes.append(t)
            break
    return parse(tubes)


def random_puzzle(n_tubes: int = 5, colours: str = "1234", cap: int = 6,
                  seed: int | None = None) -> State:
    rng = random.Random(seed)
    rings = [c for c in colours for _ in range(cap)]
    rng.shuffle(rings)
    tubes = [tuple(rings[i * cap:(i + 1) * cap]) for i in range(len(colours))]
    tubes += [()] * (n_tubes - len(colours))
    return tuple(tubes)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tubes", nargs="*", help="one string of digits 1-4 per tube, bottom to top")
    ap.add_argument("--cap", type=int, default=6, help="tube capacity (default 6)")
    ap.add_argument("--match-top", action="store_true",
                    help="only land on an empty tube or a matching top colour")
    ap.add_argument("--random", action="store_true", help="solve a random puzzle")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--demo", action="store_true", help="solve a sample puzzle")
    a = ap.parse_args()

    if a.random:
        start = random_puzzle(cap=a.cap, seed=a.seed)
    elif a.demo:
        start = random_puzzle(cap=a.cap, seed=8)
    elif not a.tubes:
        start = ask_tubes(cap=a.cap)
    else:
        start = parse(a.tubes)

    for c in sorted({r for t in start for r in t}):
        n = sum(t.count(c) for t in start)
        if n > a.cap:
            raise SystemExit(f"{NAMES[c].capitalize()} ({c}) has {n} rings but a tube "
                             f"only holds {a.cap}.")
    print("Start (bottom -> top):")
    print("  " + fmt_state(start, a.cap))
    sol = solve(start, a.cap, a.match_top)
    if sol is None:
        print("\nNo solution.")
        return
    print(f"\nFewest moves: {len(sol)}\n")
    cur = start
    for n, (i, j, run) in enumerate(sol, 1):
        colour = cur[i][-1]
        cur = apply(cur, (i, j, run))
        print(f"{n:>2}. tube {i + 1} -> tube {j + 1}   ({run} x {NAMES[colour]})")
        print("    " + fmt_state(cur, a.cap))


if __name__ == "__main__":
    main()
