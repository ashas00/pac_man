"""Entry point: ``python3 pac-man.py <config.json>``."""

import os
import sys

from game.maze import MazeError
from game.config import load_config


def main() -> int:
    """Load the configuration and run the game.

    Returns:
        Process exit code (0 on success).
    """
    if len(sys.argv) != 2:
        program = sys.argv[0] if getattr(sys, "frozen", False) else "python3 pac-man.py"
        print(f"Usage: {program} <config.json>", file=sys.stderr)
        return 1

    config_path = os.path.abspath(sys.argv[1])
    if getattr(sys, "frozen", False):
        # Packaged build: assets and highscores live next to the executable.
        os.chdir(os.path.dirname(sys.executable))
    try:
        config = load_config(config_path)
        # Imported here so that a broken graphics setup is reported cleanly.
        from game.engine import GameEngine
        GameEngine(config).run()
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return 130
    except MazeError as e:
        print(f"Error: could not build the maze: {e}", file=sys.stderr)
        return 1
    except Exception as e:  # last safety net: never show a traceback
        print(f"Error: {type(e).__name__}: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
