"""Pac-Man game package.

Modules, from the bottom up:
    geometry       Direction, Position, Cell
    config         GameConfig (JSON file with comments)
    maze           Maze (built with the A-Maze-ing package)
    entity         Entity (movement shared by Pac-Man and the ghosts)
    pacman         Pacman
    ghost          Ghost and the four personalities
    ghost_manager  GhostManager (ghost AI)
    session        GameSession (rules of one game)
    highscores     Highscores
    sprites        Sprites
    renderer       Renderer (window and drawing)
    engine         GameEngine (screens, keys, main loop)
"""

import os


os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
