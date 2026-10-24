# Team Organization

Team: **adudnik** (Anton Dudnik) and **olprymas** (Oleksandr Prymas)

## Who did what

| Area | adudnik | olprymas |
|---|---|---|
| Environment, Makefile, config loader | ✔ | review, Python 3.10 support |
| Data models, movement, wall collisions | ✔ | movement rewrite (no wall skipping) |
| pygame window, sprites, animations | ✔ | MLX-only drawing, cached background |
| A-Maze-ing integration | ✔ | single source of geometry, corners, "42" kept |
| Ghost AI (targets, waves, frightened, eaten) | ✔ | fleeing ghosts, eyes go back to the corner |
| First refactoring proposal | ✔ | |
| Review against the subject | | ✔ |
| Screens, highscores, levels, cheats | | ✔ |
| Packaging (PyInstaller, itch.io) | | ✔ |
| Restructuring into `game/`, naming | | ✔ |
| Function renames, review of the restructuring | ✔ | ✔ |
| README and docs | | ✔ |

## How we worked

- **Phases with a roadmap** (`project_plan.md`). Each phase ended with a
  commit and an update of the roadmap.
- **Git** on the school Vogsphere repository. Each of us commits from their
  own machine; bigger changes are first done on a branch.
- **Definition of done** for a change: `make lint` passes (flake8 and mypy
  with the subject flags) and the game runs through the whole flow (menu →
  play → end screen → menu).
- **AI as a reviewer, not as the author** (see the README): proposals were read,
  discussed and adapted by us before going in.

## How decisions were made

Decisions that change the design were discussed first, then written down in
`design_decisions.md`. Rule: when in doubt, **the subject wins** over the
arcade original. Examples:

| Decision | Why |
|---|---|
| Remove the ghost house; ghosts live in the corners | subject VI.1 and VI.3 |
| Frightened ghosts run away instead of wandering | subject VI.3 |
| Always ask for a name at the end | subject VI.8 |
| One class per module, consistent names | readability for the evaluation and for each other |
| No tests in the repository | not graded; kept outside, `make lint` stays clean |

## Problems and how they were solved

| Problem | Solution |
|---|---|
| `.python-version` pinned 3.12; pyenv on the school machines did not have it, so `uv` would not even start | removed `.python-version`, `requires-python >= 3.10`, uv downloads Python itself |
| The first refactoring stopped half-way; the code and the tests no longer matched | finished it: one geometry source, tests rewritten, lint green |
| The ghost house design did not match the subject | discussed, then replaced by corner spawns |
| Inlining variables during the restructuring broke scoring (an item eaten twice, wrong ghost points) | found by the test script, variables restored; rule: keep a variable when a call changes state or is needed twice |

## Blocking points

- Shared work while one of us was refactoring: the code base was in an
  intermediate state for weeks. We now merge refactorings in small steps.
- Build for itch.io must be made on the target system (PyInstaller cannot
  cross-compile). We build on the school machines.
