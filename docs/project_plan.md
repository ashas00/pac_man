# Project Plan

How the work was split, the planned timeline and what really happened.
Dates come from the git history.

## Phases

| # | Phase | Content |
|---|---|---|
| 1 | Setup and core models | uv environment, config with comments (Pydantic), data types, Makefile |
| 2 | Graphics and menus | pygame window, sprites and animations, main menu, pause |
| 3 | Maze | A-Maze-ing integration, wall collisions, pacgums |
| 4 | Ghost AI | targeting of the four ghosts, scatter / chase waves, frightened and eaten |
| 5 | Game flow | game over / victory screens, highscores, levels, cheats |
| 6 | Packaging and defense | itch.io build, README, docs, subject compliance check |

## Timeline: planned versus actual

```
                     Aug 30   Sep 7    Sep 14  ...  Oct 12   Oct 19  Oct 20
Phase 1 setup        ███ done Aug 31
Phase 2 graphics      ██ done Sep 1
Phase 3 maze            ████ done Sep 7
Phase 4 ghost AI            ██ done Sep 8
Refactoring (1st)            ████████████████ in progress, not finished
Review vs subject                                     █
Phase 5 game flow                                     ██
Restructuring                                         ██████
Phase 6 packaging                                      █
README and docs                                               █
```

| Phase | Planned | Actual | Status |
|---|---|---|---|
| 1 Setup and core models | Aug 31 | Aug 31 | done on time |
| 2 Graphics and menus | Sep 1 | Sep 1 | done on time |
| 3 Maze | Sep 7 | Sep 7 | done on time |
| 4 Ghost AI | week 2 | Sep 8 | done |
| 1st refactoring | not planned | Sep 12 – Oct 12 | stopped half-way, tests broken |
| 5 Game flow | week 3 | Oct 19 | done |
| 6 Packaging | week 3 | Oct 19 | build done, itch.io |
| README and docs | week 3 | Oct 20 | done |

## Where we lost time

- **The first refactoring** (September – October) changed the API of the main
  classes but was never finished. On Oct 19 the code ran, but 11 tests failed,
  1 test file did not import, and `make lint` passed only because it did not
  check the whole project.
- **A design that did not match the subject.** The ghosts started in a central
  ghost house (arcade style), but the subject puts them in the four corners and
  Pac-Man in the middle. The house also covered the "42" pattern of the maze.
  It was removed (see `design_decisions.md`).
- **Phase 5 had not started** when the review was done: no game-over screen
  (the game froze), no highscores, a single level, cheats that did nothing.

## Work done on Oct 19–20 (catch-up)

1. Single source of maze geometry, subject spawn points, all tests and lint green
2. Screen flow: menu, highscores, instructions, pause, game over, victory, name entry
3. Persistent highscores
4. 10 levels with time limit, `levels` overrides, cheats
5. Standalone build (PyInstaller) and itch.io manifest
6. Audit against the subject; fixes (fleeing ghosts, name prompt, `pacgum` key, MLX-only drawing)
7. Performance: maze drawn once per level
8. Restructuring into `game/`, one class per module, consistent naming
9. README and documentation

## Remaining

- [ ] Upload the build to itch.io (restricted page) and put the link in the README
- [ ] Prepare the defense: run through `docs/test_plan.md` once more
