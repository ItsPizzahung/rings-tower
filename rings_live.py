#!/usr/bin/env python3
"""Rings Tower solver: fewest-move solution via A* search.

Rules modelled
- N tubes (default 5), each holds up to CAP rings (default 6).
- A move takes the top run of same-coloured adjacent rings from one tube.
- It can land on any other tube that has room (any colour).
  (Use --match-top to require an empty tube or a matching top colour instead.)
- The whole run moves together. If the target lacks room, the target fills to
  CAP and the leftover rings stay behind in the source tube (partial move).
- Solved: every colour sits in exactly one tube, and every tube is one colour.

Colours are entered as numbers: 1=red 2=yellow 3=cyan 4=purple.

Usage
  python rings_tower_solver.py              (asks you for each tube)
  python rings_tower_solver.py 121344 ...   (one string per tube, bottom -> top)
  python rings_tower_solver.py --random [--seed N]
  python rings_tower_solver.py --demo
Use "." for an empty tube, e.g.  python rings_tower_solver.py 121344 ... .

Reading the screen (Arch + Hyprland, iPhone mirrored with UxPlay)
  sudo pacman -S grim slurp python-numpy python-pillow
  python rings_tower_solver.py --live              (finds the UxPlay window)
  python rings_tower_solver.py --live --select     (drag a box round the game)
  python rings_tower_solver.py --live --watch 1    (re-reads by itself)
  python rings_tower_solver.py --image shot.png    (read a saved screenshot)
Add --debug to save rings_debug.png showing what the program saw.
"""

from __future__ import annotations

import argparse
import heapq
import io
import json
import random
import re
import subprocess
import time

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


def report(start: State, cap: int, match: bool = False, brief: bool = False):
    """Solve `start` and print the plan. Returns the move list (or None)."""
    for c in sorted({r for t in start for r in t}):
        n = sum(t.count(c) for t in start)
        if n > cap:
            raise SystemExit(f"{NAMES[c].capitalize()} ({c}) has {n} rings but a tube "
                             f"only holds {cap}.")
    if not brief:
        print("Start (bottom -> top):")
        print("  " + fmt_state(start, cap))
    sol = solve(start, cap, match)
    if sol is None:
        print("\nNo solution.")
        return None
    if not sol:
        print("\nAlready solved!")
        return sol
    print(f"\nFewest moves: {len(sol)}\n")
    cur = start
    for n, (i, j, run) in enumerate(sol, 1):
        colour = cur[i][-1]
        cur = apply(cur, (i, j, run))
        print(f"{n:>2}. tube {i + 1} -> tube {j + 1}   ({run} x {NAMES[colour]})")
        if not brief:
            print("    " + fmt_state(cur, cap))
    return sol


# ---------------------------------------------------------------------------
# Screen reading. Needs numpy + pillow; capture uses grim / slurp / hyprctl.
# Finds the wooden base and poles first, then reads the rings stacked on each pole.
# ---------------------------------------------------------------------------

# Ring colours as hue windows in degrees (0-360) plus a minimum saturation.
# Measured from the real game: red is a pink (~347), cyan ~196, purple ~251 and
# fairly washed out, yellow ~50. The wooden base and poles are ~31-33.
# Edit these if a colour is being misread.
RING_COLOURS = {
    "1": ([(335, 360), (0, 12)], 0.40),  # red / pink
    "2": ([(40, 66)], 0.45),             # yellow
    "3": ([(180, 215)], 0.35),           # cyan
    "4": ([(235, 285)], 0.22),           # purple
}
WOOD = ((24, 38), 0.45, 0.74, 0.60)  # hue range, sat range, min brightness
MIN_VAL = 0.35


def classify(rgb):
    """HxWx3 uint8 image -> (labels, wood). labels: 0 = not a ring, 1..4 colour."""
    import numpy as np
    x = rgb.astype(np.float32) / 255.0
    r, g, b = x[..., 0], x[..., 1], x[..., 2]
    mx, mn = x.max(axis=2), x.min(axis=2)
    d = mx - mn
    nz = d > 1e-6
    h = np.zeros_like(mx)
    rm = nz & (mx == r)
    gm = nz & (mx == g) & ~rm
    bm = nz & ~rm & ~gm
    h[rm] = ((g - b)[rm] / d[rm]) % 6
    h[gm] = (b - r)[gm] / d[gm] + 2
    h[bm] = (r - g)[bm] / d[bm] + 4
    h *= 60.0
    sat = np.where(mx > 0, d / np.maximum(mx, 1e-6), 0.0)
    lab = np.zeros(mx.shape, np.int8)
    bright = mx >= MIN_VAL
    for k, (spans, min_sat) in RING_COLOURS.items():
        ok = bright & (sat >= min_sat)
        for lo, hi in spans:
            lab[ok & (h >= lo) & (h <= hi)] = int(k)
    (wlo, whi), wsat0, wsat1, wval = WOOD
    wood = (h >= wlo) & (h <= whi) & (sat >= wsat0) & (sat <= wsat1) & (mx >= wval)
    return lab, wood


def find_board(wood, n_tubes, warns):
    """Locate the wooden base and the poles.

    Returns (poles, spacing, pole_top_y, base_bottom_y); poles = x centre of every
    tube (empty ones included), left to right. Rings can only be between the two.
    """
    import numpy as np
    H, W = wood.shape
    rows = wood.sum(axis=1)
    if rows.max() < max(60, 0.05 * W):
        warns.append("Can't see the wooden base - is the whole game in the capture?")
        return None
    peak = int(rows.argmax())
    good = rows >= 0.5 * rows[peak]
    y0 = y1 = peak
    while y0 > 0 and good[y0 - 1]:
        y0 -= 1
    while y1 < H - 1 and good[y1 + 1]:
        y1 += 1
    xs = np.flatnonzero(wood[peak])
    bx0, bx1 = int(xs.min()), int(xs.max())
    # poles: narrow wooden strips standing above the base's top face
    top = int(np.argmax(rows >= 0.2 * rows[peak]))
    cw = wood[:top, bx0:bx1 + 1].sum(axis=0)
    on = cw >= 0.04 * (bx1 - bx0)
    spans, x = [], 0
    while x < len(on):
        if on[x]:
            s0 = x
            while x < len(on) and on[x]:
                x += 1
            if 2 <= x - s0 <= 0.12 * (bx1 - bx0):
                spans.append((bx0 + (s0 + x - 1) / 2, float(cw[s0:x].sum())))
        else:
            x += 1
    spans = sorted(sorted(spans, key=lambda p: -p[1])[:n_tubes])
    poles = [p[0] for p in spans]
    if len(poles) == n_tubes:
        spacing = float(np.median(np.diff(poles)))
        return poles, spacing, _pole_top(wood, poles, top), y1
    if len(poles) < 2:
        warns.append("Couldn't find the poles.")
        return None
    spacing = float(min(np.diff(poles)))  # neighbouring poles are closest
    cx = (bx0 + bx1) / 2  # the board is symmetric about its middle
    poles = [cx + (j - (n_tubes - 1) / 2) * spacing for j in range(n_tubes)]
    warns.append(f"Only {len(spans)} poles found; positions worked out from the base.")
    return poles, spacing, _pole_top(wood, poles, top), y1


def _pole_top(wood, poles, base_top):
    """Row where the poles start (they all stand the same height)."""
    import numpy as np
    firsts = []
    for cx in poles:
        band = wood[:base_top, max(0, int(cx) - 2):int(cx) + 3].any(axis=1)
        if band.any():
            firsts.append(int(band.argmax()))
    return int(np.median(firsts)) if firsts else 0


def read_column(lab, cx, half, min_len):
    """Runs of one colour down a tube: [(label, y0, y1)], top to bottom."""
    import numpy as np
    H, W = lab.shape
    x0, x1 = max(0, int(cx - half)), min(W, int(cx + half) + 1)
    sub = lab[:, x0:x1]
    cnt = np.stack([(sub == k).sum(axis=1) for k in range(1, 5)])  # 4 x H
    best = cnt.argmax(axis=0) + 1
    row = np.where(cnt.max(axis=0) >= 0.5 * (x1 - x0), best, 0)
    runs_, y = [], 0
    while y < H:
        if row[y]:
            y0, v = y, row[y]
            while y < H and row[y] == v:
                y += 1
            if y - y0 >= min_len:
                runs_.append((int(v), y0, y))
        else:
            y += 1
    return runs_


def _tubes_from_runs(per_tube):
    """Turn colour runs into ring lists. Each run is normally one ring (there is a
    little gap between rings); a longer run is several touching same-colour rings."""
    import numpy as np
    lens = [y1 - y0 for rs in per_tube for _, y0, y1 in rs]
    if not lens:
        return tuple(() for _ in per_tube)
    h = float(np.median(lens))  # one ring's visible height
    steps = [b[1] - a[1] for rs in per_tube for a, b in zip(rs, rs[1:])]
    pitch = max(float(np.median(steps)) if steps else h / 0.77, h)
    tubes = []
    for rs in per_tube:
        t: list[str] = []
        for v, y0, y1 in reversed(rs):  # bottom first
            t += [str(v)] * max(1, int(round((y1 - y0 + pitch - h) / pitch)))
        tubes.append(tuple(t))
    return tuple(tubes)


def problems(state, cap):
    """Reasons a read state can't be a real board (empty list = looks fine)."""
    out = []
    for c, name in NAMES.items():
        n = sum(t.count(c) for t in state)
        if n != cap:
            out.append(f"counted {n} {name} rings, expected {cap}")
    for i, t in enumerate(state, 1):
        if len(t) > cap:
            out.append(f"tube {i} has {len(t)} rings, max is {cap}")
    return out


def read_state(img, cap=6, n_tubes=5, debug_path=None):
    """Read a screenshot of the game. Returns (state or None, warnings)."""
    import numpy as np
    rgb = np.asarray(img.convert("RGB"))
    lab, wood = classify(rgb)
    warns: list[str] = []
    found = find_board(wood, n_tubes, warns)
    if found is None:
        return None, warns
    poles, spacing, ceil, floor = found
    half = max(3.0, 0.22 * spacing)  # stay on the ring face, away from the edges
    lab = lab.copy()
    lab[:max(0, ceil - 4)] = 0  # ignore the phone's buttons, clock, etc.
    lab[floor + 1:] = 0
    per_tube = [read_column(lab, cx, half, 0.25 * spacing) for cx in poles]
    state = _tubes_from_runs(per_tube)
    bad = problems(state, cap)
    if bad:
        warns.append("Reading looks wrong: " + "; ".join(bad) + ".")
    if debug_path:
        _save_debug(img, poles, half, per_tube, state, debug_path)
    return state, warns


def _save_debug(img, poles, half, per_tube, state, path):
    from PIL import ImageDraw
    im = img.convert("RGB")
    d = ImageDraw.Draw(im)
    for n, (cx, runs_, t) in enumerate(zip(poles, per_tube, state), 1):
        d.rectangle([cx - half, 0, cx + half, im.height - 1], outline=(255, 255, 255))
        d.text((cx - 6, 4), f"T{n}", fill=(255, 255, 255))
        for v, y0, y1 in runs_:
            d.rectangle([cx - half, y0, cx + half, y1], outline=(0, 0, 0), width=2)
            d.text((cx + half + 4, (y0 + y1) // 2 - 5), str(v), fill=(255, 255, 255))
        d.text((cx - half, 22), "".join(t) or ".", fill=(255, 255, 255))
    im.save(path)


# --- getting the picture ----------------------------------------------------
def _find_window(pattern: str) -> str:
    """Geometry 'x,y wxh' of the first visible window matching `pattern`."""
    try:
        out = subprocess.run(["hyprctl", "clients", "-j"], capture_output=True,
                             text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError) as e:
        raise SystemExit(f"Couldn't run hyprctl ({e}). Use --select instead.")
    clients = [c for c in json.loads(out)
               if c.get("mapped", True) and not c.get("hidden")]
    rx = re.compile(pattern, re.I)
    hits = [c for c in clients
            if rx.search(f"{c.get('class', '')} {c.get('initialClass', '')} "
                         f"{c.get('title', '')}")]
    if not hits:
        names = "\n".join(f"  class={c.get('class')!r} title={c.get('title')!r}"
                          for c in clients)
        raise SystemExit(f"No window matching {pattern!r}. Open windows:\n{names}\n"
                         "Re-run with --window <part of class or title>, or --select.")
    x, y = hits[0]["at"]
    w, h = hits[0]["size"]
    return f"{x},{y} {w}x{h}"


def _grab(region: str | None):
    from PIL import Image
    cmd = ["grim"] + (["-g", region] if region else []) + ["-"]
    try:
        png = subprocess.run(cmd, capture_output=True, check=True).stdout
    except OSError:
        raise SystemExit("grim isn't installed: sudo pacman -S grim slurp")
    except subprocess.CalledProcessError as e:
        raise SystemExit(f"grim failed: {e.stderr.decode(errors='replace')}")
    return Image.open(io.BytesIO(png))


def live(a) -> None:
    from PIL import Image
    region = None
    if a.image:
        get = lambda: Image.open(a.image)  # noqa: E731
    elif a.select:
        try:
            region = subprocess.run(["slurp"], capture_output=True, text=True,
                                    check=True).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            raise SystemExit("slurp failed or isn't installed: sudo pacman -S slurp")
        get = lambda: _grab(region)  # noqa: E731
    else:
        get = lambda: _grab(_find_window(a.window))  # noqa: E731

    watching = bool(a.watch) and not a.image
    # Always save the debug picture when asked, or when reading by hand.
    dbg = "rings_debug.png" if (a.debug or not watching) else None
    prev = shown = None
    while True:
        state, warns = read_state(get(), a.cap, debug_path=dbg)
        bad = state is None or bool(problems(state, a.cap))
        if watching:
            # Only act on a valid board that has stopped moving and changed.
            steady = (not bad) and state == prev
            prev = None if bad else state
            if bad:
                print("waiting for a readable board (use --debug to see why)...",
                      end="\r")
            if not steady or state == shown:
                time.sleep(a.watch)
                continue
            shown = state
            print("\033[2J\033[H", end="")  # clear the terminal
        if state is not None:
            print("Read from screen (bottom -> top, tube 1 = leftmost):")
            print("  " + fmt_state(state, a.cap))
        for w in warns:
            print("  !", w)
        if bad:
            print("  Couldn't read a valid board. Saved rings_debug.png to show "
                  "what was seen." if dbg else "  Couldn't read a valid board.")
        else:
            print()
            report(state, a.cap, a.match_top, brief=True)
        if a.image:
            return
        if watching:
            time.sleep(a.watch)
            continue
        ans = input("\n[Enter] re-read after your move   [t] type the board   "
                    "[q] quit: ").strip().lower()
        if ans == "q":
            return
        if ans == "t":
            report(ask_tubes(cap=a.cap), a.cap, a.match_top)
            input("\n[Enter] to go back to reading the screen ")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tubes", nargs="*", help="one string of digits 1-4 per tube, bottom to top")
    ap.add_argument("--cap", type=int, default=6, help="tube capacity (default 6)")
    ap.add_argument("--match-top", action="store_true",
                    help="only land on an empty tube or a matching top colour")
    ap.add_argument("--live", action="store_true",
                    help="read the board from the UxPlay window on screen")
    ap.add_argument("--image", metavar="FILE", help="read the board from a screenshot")
    ap.add_argument("--window", default="uxplay", metavar="REGEX",
                    help="window class/title to capture (default: uxplay)")
    ap.add_argument("--select", action="store_true",
                    help="with --live: drag a box over the game instead of "
                         "auto-finding the window")
    ap.add_argument("--watch", type=float, metavar="SEC",
                    help="with --live: re-read every SEC seconds, no key presses")
    ap.add_argument("--debug", action="store_true",
                    help="save rings_debug.png showing what was detected")
    ap.add_argument("--random", action="store_true", help="solve a random puzzle")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--demo", action="store_true", help="solve a sample puzzle")
    a = ap.parse_args()

    if a.live or a.image:
        live(a)
        return
    if a.random:
        start = random_puzzle(cap=a.cap, seed=a.seed)
    elif a.demo:
        start = random_puzzle(cap=a.cap, seed=8)
    elif not a.tubes:
        start = ask_tubes(cap=a.cap)
    else:
        start = parse(a.tubes)
    report(start, a.cap, a.match_top)


if __name__ == "__main__":
    main()
