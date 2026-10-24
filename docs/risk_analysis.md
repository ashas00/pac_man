# Risk Analysis

| # | Risk | Impact | Likelihood | Mitigation | Status |
|---|---|---|---|---|---|
| R1 | The A-Maze-ing package fails or returns an unexpected grid (it is re-installed during the review) | high | medium | only `maze.py` uses it; output shape checked; any error becomes `MazeError` with a clear message | mitigated |
| R2 | Invalid configuration during the defense ("the configuration will be updated") | high | high | key-by-key validation with ranges; invalid key → default + warning; unknown keys ignored; comments stripped safely | mitigated |
| R3 | A Python traceback during the evaluation | critical | medium | entry point catches every exception and prints one line; config, highscores and sprites never stop the game | mitigated |
| R4 | pygame function without an MLX equivalent | high | low | only basic primitives used; scaling, mirroring and overlays done by hand (`design_decisions.md`) | mitigated |
| R5 | `make lint` fails on the evaluator's machine | high | medium | lint run after every change; tests kept out of the repository | mitigated |
| R6 | Wrong Python version or missing tools on the school machines | medium | high (it happened) | `requires-python >= 3.10`, no `.python-version`, `uv` installs Python | mitigated |
| R7 | Game too slow on big mazes | medium | medium (23 FPS on 100×100) | maze drawn once per level | mitigated |
| R8 | Fast entities passing through walls | high | medium (it happened) | movement walked centre by centre | mitigated |
| R9 | Packaged game does not start on the evaluation machine | high | medium | build on the target system; paths relative to the executable; tested from a clean folder | mitigated |
| R10 | Highscore file missing, broken or not writable | medium | medium | empty table on missing file, invalid entries skipped, atomic save, failure only reported | mitigated |
| R11 | Unfinished refactoring blocks the team | high | it happened | refactor in small steps; lint and the full game flow must pass before a merge | mitigated |
| R12 | itch.io upload not done before the defense | high | low | build ready; upload is the last open task in `project_plan.md` | open |
