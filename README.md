# Rings Tower Solver

A solver for the **Rings Tower Lens by Anubhav Bharti** Snapchat filter via A* search.



It is in 2 python files: 
- For text-based only `rings_tower_solver_text.py`.
- For both grim capture and text-based `rings_live.py`.

Second file can read the board from IOS devices with [UxPlay](https://github.com/FDH2/UxPlay).

---

## Game rules

- 5 tubes (poles), each holds up to **6** rings. 4 colours, 6 rings of each.
- A move takes the **top group** of same-coloured rings on a tube. All adjacent rings of that colour move together, never just one of them.
- The group can land on **any other tube that has room**, whatever colour is on top there.
- If the destination doesn't have enough room, it **fills to 6** and the leftover rings stay behind on the original tube (the group splits).
- **Solved** = every colour sits on exactly one tube, so you end with 4 full single-colour tubes and 1 empty tube.

If your version of the game only lets you stack on an empty tube or a matching colour, run with `--match-top`.

## Colour numbers

Tubes are numbered **1 to 5 from left to right** as you see them on screen. Boards are written **bottom to top**, so `224311` means yellow, yellow, purple, cyan, red, red from the bottom up.

---
## Limitations
- **Live capture is Hyprland only** (`hyprctl` + `grim`). May work for other distros but I have not tested.
- `--select` also works on other wlroots compositors such as Sway. On other desktops, take a screenshot yourself and use `--image`, or type the board in.
- **The window must be visible**, fully on screen, on the active workspace. A window inside a Hyprland tab group that isn't the active tab may be reported as hidden and won't be found. The program does not check which workspace the window is on.
- **Tuned to one game.** The colours and the base-and-poles layout come from real screenshots of the Paper Rings filter. A different skin, a game update, or different video settings could change them.
- **Fixed layout.** It assumes 5 tubes and 4 colours. `--cap` changes the tube capacity, but the tube and colour counts are fixed.
- **Colour tinting.** `hyprsunset`/night light does not affect the capture. Anything that tints the captured picture itself may: in simulation, a warm tint of about 5000K was fine, but around 4000K and warmer the colours were misread.
- **Rules come from the game as described.** If your filter behaves differently, use `--match-top` or open an issue.


## Install

### For text-based only

Download the `rings_tower_solver_text.py`
Usage
  python rings_tower_solver.py              (asks you for each tube, enter for blank tubes)
  python rings_tower_solver.py 121344 ...   (one string per tube, bottom -> top)
  python rings_tower_solver.py --random [--seed N]
  python rings_tower_solver.py --demo
Use "." for an empty tube, e.g.  python rings_tower_solver.py 121344 ... .


### For UxPlay version


You need **Python 3.9 or newer**.

Autoread is only coded for Hyprland, may work for other distros but I have not tested.

**Reading the screen (Arch Linux + Hyprland):**

```bash
sudo pacman -S grim slurp python-numpy python-pillow
```

and install UxPlay from your package source (e.g. the AUR) so you can mirror your iPhone.

`slurp` is only needed for `--select`.

---

## Quick start

### 1. Type the board in

```bash
python rings_tower_solver_text.py
```
or
```bash
python rings_live.py
```

It asks for each tube, bottom to top, using the colour numbers. Press Enter for an empty tube.

Or give it all five tubes at once, with `.` for an empty tube:

```bash
python rings_tower_solver.py 224311 443433 . 312243 221114
```

### 2. Read it off the screen

Mirror your iPhone with UxPlay, open the filter, and keep the UxPlay window **fully visible** (not covered by another window, on the workspace you're looking at). Put your terminal next to it.

```bash
python rings_live.py --live
```

It finds the UxPlay window, reads the board, and prints the plan. After you make a move in the game, press **Enter** to re-read and get the next best move. Other keys at the prompt: `t` to type the board by hand, `q` to quit.

For hands-free mode that re-reads by itself:

```bash
python rings_live.py --live --watch 1
```

---

## Example

```
$ python rings_live.py 224311 443433 . 312243 221114
Start (bottom -> top):
  224311  443433          312243  221114

Fewest moves: 15

 1. tube 4 -> tube 3   (1 x cyan)
    224311  443433  3       31224   221114
 2. tube 1 -> tube 3   (2 x red)
    2243    443433  311     31224   221114
 3. tube 2 -> tube 1   (2 x cyan)
    224333  4434    311     31224   221114
 ...
```

Each line says which tube to take from, which tube to drop on, and how many rings of which colour. In live mode only the move list is printed, without the board after each step.

---

## All options

| Option | What it does |
| ------ | ------------ |
| *(none)* | Asks you to type the board, tube by tube |
| `TUBE TUBE ...` | Solve this board, one string of digits per tube, `.` = empty |
| `--live` | Read the board from the UxPlay window on screen |
| `--select` | With `--live`: drag a box over the game once instead of auto-finding the window |
| `--watch SEC` | With `--live`: re-read every `SEC` seconds and print a new plan whenever the board changes |
| `--window REGEX` | Window class or title to look for (default `uxplay`) |
| `--image FILE` | Read the board from a screenshot file instead of the screen |
| `--debug` | Save `rings_debug.png` showing what the program detected |
| `--match-top` | Only allow landing on an empty tube or a matching top colour |
| `--cap N` | Tube capacity (default 6) |
| `--random`, `--seed N` | Solve a random board |
| `--demo` | Solve a built-in sample board |

---

## How it works

### 1. Capturing the screen

- `--live` asks Hyprland for its window list (`hyprctl clients -j`) and picks the first visible window whose class or title matches `uxplay`.
- It takes that window's position and size and captures **only that rectangle** of the screen with `grim`.
- This happens again on every refresh, so it doesn't matter whether UxPlay is on the left or right, or whether you move it between reads.
- The capture is of what is actually on screen, so anything covering the window (a floating window, a notification) ends up in the picture.
- With `--select`, you drag a box once with `slurp` and that same box is used every time; it won't follow the window if you move it.
- It does not look at tabs or at other windows. It only sees pixels.

### 2. Reading the board from the picture

1. **Colour each pixel.** Each pixel is classed as red, yellow, cyan, purple, wood, or none, using hue and saturation ranges measured from the real game (set in `RING_COLOURS` and `WOOD` near the top of the file).
2. **Find the wooden base.** The widest row of wood-coloured pixels is the base.
3. **Find the poles.** Poles are the narrow wooden strips standing above the base. This also locates an empty tube, which has no rings but still has a pole.
4. **Ignore everything else.** Only a narrow band around each pole, between the tops of the poles and the bottom of the base, is looked at. Snapchat's buttons, the clock and the filter carousel all fall outside it.
5. **Read each pole top to bottom.** A run of one colour is a ring. A taller run is several touching rings of the same colour.
6. **Sanity check.** It must count exactly 6 rings of each colour and no tube over capacity. If not, it says what looked wrong, saves `rings_debug.png`, and refuses to guess.

### 3. Solving

- The search is **A\*** over every reachable board, so the first solution it finds is a shortest one.
- Its distance estimate is the number of colour blocks on the board minus the number of colours. One move can remove at most one block, and a solved board has exactly one block per colour, so the estimate never overshoots and the answer stays optimal.
- Boards that differ only by the order of the tubes are treated as the same board.


- The solver's answers were compared against a plain exhaustive search (no shortcuts) on 80 small puzzles, and every one matched.
- Every solution was replayed move by move against the rules and ended in a solved board.
- The screen reader was checked on real screenshots from the game, and on 150 more boards built from those screenshots' real ring images, including resized and compressed versions.
---

## Troubleshooting

| Problem | Try this |
| ------- | -------- |
| `No window matching 'uxplay'` | It prints the windows it can see. Re-run with `--window <part of the class or title>`, or use `--live --select`. |
| `grim isn't installed` | `sudo pacman -S grim slurp` |
| `Couldn't read a valid board` | Open `rings_debug.png`. It shows the detected poles, rings and digits. Make sure the whole game is in view and nothing covers it. |
| Wrong colours | Adjust the hue ranges in `RING_COLOURS`, or share a screenshot of the game so they can be tuned. |
| `No solution` | The board as read can't be solved under the rules above. Double-check the numbers, and check whether your game really needs `--match-top` (or really doesn't). |

---


