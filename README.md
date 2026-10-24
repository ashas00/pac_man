*This project has been created as part of the 42 curriculum by adudnik, olprymas.*

# Pac-Man

## Description

A remake of the 1980 arcade game **Pac-Man** in Python. Pac-Man runs through a
maze, eats every pacgum to clear the level and avoids four ghosts. Each ghost
has its own way of hunting him. A super-pacgum turns the ghosts blue for a few
seconds, and then Pac-Man can eat them.

The mazes are not hand-made. They come from an external **A-Maze-ing** package, so every level is different. The first level always
uses the seed from the configuration, and the following levels are random.

Features:

- 10 levels (configurable) with a time limit; score and lives carry over
- 4 ghosts with the arcade personalities (Blinky, Pinky, Inky, Clyde) and the
  arcade scatter / chase waves
- main menu, highscores page, instructions page, pause menu, game-over and
  victory screens
- persistent top-10 highscores with name entry
- JSON configuration with comments; invalid values never crash the game
- cheat keys for the evaluation
- standalone build for itch.io (no Python needed to play)

## Instructions

Requirements: Python 3.10 or newer and [uv](https://docs.astral.sh/uv/).
`uv` downloads a suitable Python by itself when the system one is too old.

```bash
make install        # create .venv and install dependencies
make run            # play with config.json
```

Without `make`:

```bash
uv sync
uv run python pac-man.py config.json
```

The program takes exactly one argument, the configuration file. Any problem
(missing file, invalid JSON, invalid value) is reported as a warning, and the
game continues with safe defaults. No traceback is ever shown.

Other Makefile rules:

| Rule | What it does |
|---|---|
| `make debug` | run the game under `pdb` |
| `make lint` | `flake8 .` and `mypy .` with the flags required by the subject |
| `make lint-strict` | `flake8 .` and `mypy . --strict` |
| `make package` | build the standalone game into `dist/pac-man/` and `dist/pac-man-linux.zip` |
| `make clean` | remove caches and build outputs |

Controls:

| Key | Action |
|---|---|
| Arrows / WASD | move |
| P / Esc | pause menu |
| Up / Down + Enter | navigate the menus |

Cheats (for the evaluation, work during play, active ones are shown in red in the HUD):

| Key | Cheat |
|---|---|
| I | invincible (ghosts cannot take a life) |
| Z | freeze the ghosts |
| B | speed boost |
| L | skip the level (victory after the last one) |
| K | one extra life |
| F | make every ghost edible now |

Packaged game: `make package` builds one executable with PyInstaller
(`pac-man.spec`). Next to it the build puts `config.json`, `assets/`,
`PLAYING.txt` (in-package instructions) and `.itch.toml`, which tells the itch.io
app to start the game with `config.json` as its argument. Build on the machine
you will play on: PyInstaller only builds for the system it runs on.


## Configuration

`config.json` is JSON with comments: lines or line ends starting with `#` or
`//`, and `/* ... */` blocks, are ignored (but not inside strings).

Every key is optional. A missing key uses its default. An invalid value prints a
warning and only that key falls back to its default; the rest of the file is
still used. Unknown keys are ignored.

| Key | Default | Allowed | Meaning |
|---|---|---|---|
| `lives` | 3 | 1–99 | starting lives |
| `points_per_pacgum` | 10 | ≥ 0 | points for a pacgum |
| `points_per_super_pacgum` | 50 | ≥ 0 | points for a super-pacgum |
| `points_per_ghost` | 200 | ≥ 0 | first ghost; next ones in a row are worth 2x, 4x, 8x |
| `player_speed` | 5.0 | 0–20 | Pac-Man speed, cells per second |
| `ghost_speed` | 4.5 | 0–20 | ghost speed, cells per second |
| `frightened_duration` | 7.0 | 0–60 | seconds the ghosts stay edible |
| `ghost_respawn_delay` | 5.0 | 0–60 | seconds an eaten ghost waits in its corner |
| `level_count` | 10 | 1–100 | number of levels (more if `levels` lists more) |
| `level_max_time` | 90 | 0–3600 | seconds per level |
| `seed` | 42 | any int | maze seed of level 1 (0 or less = random) |
| `width`, `height` | 19, 21 | 5–100 | maze size in cells |
| `pacgum` | 0 | ≥ 0 | pacgums per level; 0 = use `pacgum_percent` |
| `pacgum_percent` | 100 | 1–100 | share of the free cells that get a pacgum (same feel on every maze size) |
| `cell_size` | 32 | 8–120 | cell size in pixels (shrinks to fit the screen) |
| `highscore_filename` | `highscores.json` | path | where the highscores are saved |
| `spritesheet_path` | `assets/spritesheet.png` | path | sprites; plain shapes are drawn if it is missing |
| `levels` | `[]` | list | per-level overrides, see below |

`levels` is a list; entry *n* changes level *n+1*. Each entry may set `width`,
`height`, `level_max_time` and `seed`. Anything not set comes from the main
keys. Without an explicit `seed`, levels 2 and later are random.

```json
"levels": [
  {},
  { "width": 16, "height": 10 },
  { "width": 20, "height": 14, "level_max_time": 120 }
]
```

## Highscore

The ten best scores are stored in a small JSON file (`highscore_filename`):

```json
{"highscores": [{"name": "Bob", "score": 1200}, {"name": "Ann", "score": 950}]}
```

- loaded when the game starts, shown in the main menu (top 5) and on the
  Highscores page (top 10)
- at the end of every game (won or lost) the player types a name: 1–10
  characters, letters, digits and spaces only; Enter saves, Esc skips
- only the top 10 are kept; equal scores keep their order of arrival

Why JSON in a file: it is simple, human-readable and needs no extra library.
The file is written to a temporary file first and then renamed, so a crash
while saving can never leave a half-written table. A missing file means "no
scores yet". A broken file, or an entry with an invalid name or score, is
reported and skipped. If saving fails (read-only folder), the game shows a
warning and keeps the scores in memory.

## Maze Generation

Mazes come from the assigned **A-Maze-ing** package
(`assets/mazegenerator-2.1.0-py3-none-any.whl`), used as-is without
modification. `game/maze.py` is the only place that talks to it:

```python
MazeGenerator(size=(width, height), perfect=False, seed=seed).maze
```

- `perfect=False` gives loops, as Pac-Man needs (a perfect maze has dead ends only).
- `.maze` is a grid of 4-bit wall codes: 1 = north, 2 = east, 4 = south, 8 = west.
- Cells with all four walls are the closed blocks that draw the "42" pattern.
  They are drawn filled and nobody can enter them.

From that grid `Maze.generate` derives everything else:

1. Pac-Man's spawn: the free cell closest to the centre of the maze.
2. Every cell reachable from the spawn (flood fill), so no pacgum is unreachable.
3. The four corners: the reachable cells closest to the real corners. The
   ghosts live there, and the super-pacgums lie there.
4. Pacgums on the other reachable cells: `pacgum` of them, or `pacgum_percent`
   percent of them when `pacgum` is 0, chosen with the seed.

If the package raises an error or returns a grid of the wrong shape,
`MazeError` is raised and the program stops with a clear message.

## Implementation

**Movement.** Pac-Man and the ghosts walk from cell centre to cell centre
(`Entity.move`). They turn only on a centre; reversing is allowed at any time.
The distance of a frame is walked centre by centre, so even a very fast entity
never skips a centre and never passes through a wall. A wanted direction is
remembered, so the player can press a key before reaching the corner.

**Ghost AI** (`GhostManager`). On every cell centre a ghost looks at the open
directions (never the way back unless it is in a dead end) and takes the one
whose next cell is closest to its target. Ties follow the arcade order up,
left, down, right.

| Mode | Target |
|---|---|
| Chase | depends on the ghost (below) |
| Scatter | its home corner |
| Eaten | shortest path (BFS) to its home corner, may turn back; then waits `ghost_respawn_delay` and revives |
| Eaten | its home corner, then waits `ghost_respawn_delay` and revives |

- Blinky (red) aims at Pac-Man's cell.
- Pinky (pink) aims 4 cells ahead of Pac-Man (facing up also shifts 4 to the
  left, like the arcade bug).
- Inky (cyan) mirrors Blinky's position through the cell 2 ahead of Pac-Man.
- Clyde (orange) chases when 8 or more cells away, otherwise goes to his corner.

Global waves (arcade level 1): scatter 7 s, chase 20 s, scatter 7 s, chase 20 s,
scatter 5 s, chase 20 s, scatter 5 s, then chase forever. A wave change and a
super-pacgum make the ghosts turn around.

**Rules** (`GameSession`). Each frame the level timer runs, Pac-Man moves and
eats what lies on his cell, then the ghosts move and collisions are checked
(touching = centres closer than 0.6 cell). A dangerous ghost or the end of the
timer costs a life (and restarts the timer); eating every item clears the
level. Ghosts eaten in a row during one frightened period are worth 1x, 2x, 4x,
8x `points_per_ghost`. The session never touches the window; it reports what
happened with an `Event` (life lost, level cleared, game over, victory).

**Screens** (`GameEngine`). A small state machine:

```
MAIN_MENU -> PLAYING <-> PAUSED
             PLAYING -> GAME_OVER / VICTORY -> (enter name) -> MAIN_MENU
MAIN_MENU <-> HIGHSCORES, INSTRUCTIONS
```

Before each level and after a lost life the game freezes 1.5 s on "LEVEL n /
READY!". The frame time is measured and capped at 50 ms, so a stalled window
does not make everything jump.

**Drawing** (`Renderer`). The maze never changes during a level, so it is drawn
once into a background image. Every frame copies that image, erases the
pacgums eaten since the last frame and draws the moving parts and the HUD
(0.5 ms per frame even on a 100×100 maze). Only primitives with an MLX
equivalent are used: filled rectangles, lines, circles, text and image copies.
Sprites are cut from the sprite sheet and scaled pixel by pixel, like writing
into an MLX image buffer. The window has a minimum size so menus always fit,
and cells shrink so a big maze still fits on the screen.

**Errors.** `pac-man.py` catches every exception and prints one clear line
instead of a traceback. The configuration and the highscores never stop the
game, and a missing sprite sheet only switches to plain shapes.

## General Software Architecture

One package, `game/`, with one main class per module. The file name is the
class name:

| Module | Main class | Role |
|---|---|---|
| `geometry.py` | `Direction`, `Position` | basic types (`Cell` = (column, row)) |
| `config.py` | `GameConfig` | loads and validates `config.json` (Pydantic v2) |
| `maze.py` | `Maze` | adapter for A-Maze-ing: walls, items, spawn points |
| `entity.py` | `Entity` | movement shared by Pac-Man and the ghosts |
| `pacman.py` | `Pacman` | the player: direction, lives, speed boost |
| `ghost.py` | `Ghost`, `Blinky`, `Pinky`, `Inky`, `Clyde` | ghost state and the four chase targets |
| `ghost_manager.py` | `GhostManager`, `WaveTimer` | ghost AI: waves, steering, eating |
| `session.py` | `GameSession` | rules of one game: levels, score, lives, timer, cheats |
| `highscores.py` | `Highscores` | top-10 table in JSON |
| `sprites.py` | `Sprites` | animation frames from the sprite sheet |
| `renderer.py` | `Renderer` | window, game view and every screen |
| `engine.py` | `GameEngine` | screens, keyboard, main loop |

`pac-man.py` (the entry point) reads the argument, loads the configuration and
runs `GameEngine`.

```
pac-man.py
   └─ GameEngine ──────────────┬─ Renderer ── Sprites
        │  uses                └─ Highscores
        ▼
   GameSession ── GameConfig
        ├─ Maze  (A-Maze-ing)
        ├─ Pacman ─┐
        └─ GhostManager ── Ghost ×4 (Blinky, Pinky, Inky, Clyde)
                   └─ both inherit Entity (movement)
```

Rules of the layering:

- `GameSession` and everything below it never import pygame. The rules can be
  run and checked without a window.
- The `Renderer` only reads the game state; it never changes it.
- `Maze` hides the wall bit flags. Other classes ask it questions
  (`can_move`, `is_block`, `get_item`, `eat_item`).
- Method names follow one pattern: `get_` returns a value, `set_` / `init_`
  change state, `is_` / `has_` / `can_` answer yes or no, `handle_*_key` reacts
  to keys, `draw_*` draws.

## Project Management

We split the work into phases, tracked progress against the plan, analysed the
risks and kept an acceptance test plan. Everything is in [`docs/`](docs/):

- [`docs/project_plan.md`](docs/project_plan.md): timeline, planned versus actual progress
- [`docs/team_organization.md`](docs/team_organization.md): who did what, how decisions were made, blocking points
- [`docs/design_decisions.md`](docs/design_decisions.md): project analysis and the choices we made
- [`docs/risk_analysis.md`](docs/risk_analysis.md): risks and mitigation
- [`docs/test_plan.md`](docs/test_plan.md): acceptance tests, bugs found and fixed

## Resources

- [The Pac-Man Dossier](https://pacman.holenet.info/), Jamey Pittman: the
  reference for the original ghost behaviour and timings
- [Understanding Pac-Man Ghost Behavior](https://gameinternals.com/understanding-pac-man-ghost-behavior),
  Chad Birch: ghost targeting explained with diagrams
- [pygame documentation](https://www.pygame.org/docs/)
- [Pydantic v2 documentation](https://docs.pydantic.dev/latest/)
- [PyInstaller manual](https://pyinstaller.org/en/stable/)
- [itch.io app manifest](https://itch.io/docs/itch/integrating/manifest.html)
- [uv documentation](https://docs.astral.sh/uv/)
- [flake8](https://flake8.pycqa.org/) and [mypy](https://mypy.readthedocs.io/)

### How AI was used

We used AI as an assistant:

- **Checks:** writing throw-away test scripts (not part of the submission) and
  measuring the frame time.
- **Documentation:** first drafts of this README and of `docs/`.

Every change was read, discussed in the team, and reworked or renamed by us
where needed; we can explain each part of the code.
