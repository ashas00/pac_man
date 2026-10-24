# Acceptance Test Plan

How we check the game before the defense, and the bugs this found.

## Automatic checks

- `make lint`: flake8 and mypy with the subject flags (also `make lint-strict`).
- A test script kept **outside** the repository (tests are not graded) with
  52 checks: configuration, maze generation (5×5 to 100×100), movement,
  ghost AI, scoring, levels, cheats, highscores, every screen, drawing. One check
  plays 30 s of random moves and verifies, on the raw wall bits, that nobody
  ever walks through a wall.
- A stress run: 20,000 frames of random key presses on all screens, no crash.

## Manual acceptance tests

| # | Feature | How to test | Expected | Result |
|---|---|---|---|---|
| 1 | Start | `python3 pac-man.py config.json` | main menu | ✔ |
| 2 | Wrong arguments | no argument / two arguments | usage message, exit code 1 | ✔ |
| 3 | Broken config | missing file, invalid JSON, `"lives": -5`, `"seed": "x"`, unknown key | warning, game runs with defaults for those keys only | ✔ |
| 4 | Comments in config | `#`, `//`, `/* */`, and `#` inside a string | comments ignored, strings kept | ✔ |
| 5 | Maze | start a level | maze from A-Maze-ing, "42" visible, super-pacgums in the corners | ✔ |
| 6 | Spawns | start a level | Pac-Man in the middle, one ghost in each corner | ✔ |
| 7 | Movement | arrows and WASD | moves in corridors only, turns at corners | ✔ |
| 8 | Ghost touch | let a ghost catch Pac-Man | one life less, everybody back home, "READY!" | ✔ |
| 9 | Super-pacgum | eat one (or press F) | ghosts blue and running away, flashing at the end | ✔ |
| 10 | Eat ghosts | eat 4 ghosts in a row | +200, +400, +800, +1600; eyes go to their corner and revive after the delay | ✔ |
| 11 | Clear a level | eat everything (or press L) | next level, score and lives kept, new maze | ✔ |
| 12 | Timer | let the time run out | one life less, timer restarts | ✔ |
| 13 | Game over | lose the last life | final score, name prompt | ✔ |
| 14 | Victory | clear the last level (L repeatedly) | congratulations, final score, name prompt | ✔ |
| 15 | Name entry | type `" Bob!!_42 is too long"` | only letters, digits, spaces; max 10; no leading space | ✔ |
| 16 | Highscores | save a score, restart the game | score in the top 10 and in the main menu | ✔ |
| 17 | Broken highscore file | corrupt `highscores.json` | warning, empty table, no crash | ✔ |
| 18 | Pause | P or Esc during play | pause menu, timer stopped; Resume / Main menu work | ✔ |
| 19 | Cheats | I, Z, B, L, K, F | each works and is shown in the HUD | ✔ |
| 20 | Big maze | `width` and `height` 100 | fits on screen, smooth | ✔ |
| 21 | Missing sprites | wrong `spritesheet_path` | warning, game drawn with shapes | ✔ |
| 22 | Packaged game | `make package`, unzip, run from another folder | starts without Python, uses its own config | ✔ |

## Bugs found and fixed

| # | Bug | Found by | Fix |
|---|---|---|---|
| B1 | Ghost house coordinates hard-coded for 19×21: other sizes put ghosts in walls | review | geometry taken from the generated maze; later the house was removed |
| B2 | Fast entities (eaten eyes) skipped a cell centre and went through walls | regression check | movement walked centre by centre |
| B3 | Game over froze the game: no screen, no way back | review | end screens with name entry, back to the menu |
| B4 | Level timer ran in the menu and during pause | review | timer runs only while playing |
| B5 | Cheat keys toggled flags nobody read | review | cheats applied in the session |
| B6 | One invalid config value reset the whole config; `#` in a string broke parsing | review | key-by-key validation; string-aware comment stripping |
| B7 | 11 tests failing and 1 not importing after the first refactoring | test run | refactoring finished, tests rewritten |
| B8 | Frightened ghosts wandered randomly (subject: run away) | subject audit | ghosts pick the direction farthest from Pac-Man |
| B9 | Name prompt only shown for a top-10 score | subject audit | always shown |
| B10 | `pacgum` key ignored | subject audit | number of pacgums per level |
| B11 | 100×100 maze ran at about 23 FPS | measurement | maze drawn once per level (0.5 ms per frame) |
| B12 | Level 1 maze generated twice at start | code review | built once in `start_level` |
| B13 | During the restructuring: `eat_item` returned the item after deleting it, an item was eaten twice per frame, ghost points shifted to 400/800/1600/1600 | test script | temporary variables restored, order of updates fixed |
| B14 | `make lint` red after the restructuring (E402, mypy `str | None`) | `make lint` | pygame import order fixed, value stored before use |
| B15 | Eaten eyes sometimes circled a loop forever instead of going home (about 22 % of start positions on seed 42) | playing | shortest path (BFS) home |
