# Design Decisions

The analysis behind the project and the choices we made, with the reasons.

## Graphics library: pygame used like MLX

The subject allows any library "similar to MLX": every function used must have
an MLX equivalent. We use pygame, limited to:

| pygame | MLX equivalent |
|---|---|
| `display.set_mode`, `display.flip` | `mlx_new_window`, `mlx_put_image_to_window` |
| `draw.rect`, `draw.line`, `draw.circle` | pixels drawn with `mlx_pixel_put` |
| `Surface`, `get_at`, `set_at`, `blit` | `mlx_new_image`, image buffer (`mlx_get_data_addr`), `mlx_put_image_to_window` |
| `image.load` | `mlx_png_file_to_image` |
| `font.render` | `mlx_string_put` |
| `event.get` | `mlx_hook` (keys, window close) |

`pygame.transform.scale` / `flip` and alpha overlays were removed because MLX
has nothing like them: sprites are scaled and mirrored pixel by pixel, and the
pause box is a solid rectangle.

## Ghost house removed: ghosts live in the corners

The first version had an arcade ghost house in the middle of the maze. We
removed it:

- the subject puts one ghost in each corner and Pac-Man in the middle (VI.1),
  and eaten ghosts respawn in their corner (VI.3);
- the house was carved over the "42" pattern that A-Maze-ing draws in the
  centre;
- the house coordinates were hard-coded for a 19×21 maze, so other sizes put
  ghosts inside walls.

Now `Maze.generate` finds the four corners and the spawn of Pac-Man from the
generated grid, for any size.

## Movement: centre to centre, distance walked step by step

An entity moves along cell centres and may only turn on one. A frame's distance
is walked centre by centre: a fast entity (eaten eyes, speed boost, slow frame)
can no longer jump past a centre and through a wall. The frame time is capped
at 50 ms.

## Ghost AI: arcade targeting, subject behaviour

We kept the arcade targeting of the four ghosts and the scatter / chase waves,
because they make the ghosts feel different from each other. Where the subject
says something else, the subject wins: frightened ghosts run away from Pac-Man
(the arcade ones wander randomly), and eaten ghosts go back to their corner.
Eaten eyes do not use the greedy rule: in a maze with loops it can circle
forever (it happened on seed 42). They follow a real shortest path (BFS
distances to their corner, computed once per level) and may turn back.
Not implemented on purpose: ghost speed changes in tunnels and Blinky's
"Cruise Elroy" mode.

## Rules separated from the screen

`GameSession` holds the rules and never imports pygame; `GameEngine` handles
screens and keys; `Renderer` only draws. The session reports what happened
through an `Event` (life lost, level cleared, game over, victory) and the engine
reacts (resize the window, show "READY!", end screen). This keeps each class
small and makes the rules checkable without a window.

## One package, one class per module, one naming pattern

All code is in `game/`, one main class per file, named after it. Method names
follow `get_` / `set_` / `init_` / `is_` / `handle_*_key` / `draw_*`. Short
helpers used once inside the same class are inlined; variables are kept when a
call changes state or its value is needed twice (this rule came from real bugs,
see `test_plan.md`).

## Configuration: Pydantic v2, validated key by key

Pydantic v2 gives types, ranges and defaults in one declaration. On an invalid
value only that key falls back to its default (with a warning), not the whole
file. Comments are stripped by a small scanner that understands strings, so a
`#` inside a value is kept.

## Highscores: JSON file, atomic save

Simple and readable. Saving writes a temporary file and renames it, so the
table is never half-written. Any read or write problem is reported and the
game goes on.

## Levels

Level 1 uses the configured seed (the subject asks for a fixed first maze);
later levels are random. `levels` can change the size, time and seed of any
level. When the timer runs out, Pac-Man loses a life and the timer restarts
(the subject lets us choose).

## Performance: maze drawn once per level

Redrawing every wall each frame took about 75 % of the frame time and dropped a
100×100 maze to about 23 FPS. The maze is now drawn once into a background
image; only eaten pacgums are erased from it. A frame takes about 0.5 ms on any
size.

## Packaging: PyInstaller and an itch.io manifest

One executable that contains Python and the libraries, with `config.json`,
`assets/` and `PLAYING.txt` next to it so players can edit them. `.itch.toml`
makes the itch.io app pass `config.json`, so the program still takes exactly one
argument.
