"""Pacman: the player-controlled entity"""

from game.entity import Entity
from game.geometry import Cell, Direction
from game.maze import Maze

UNPLACED = (0, 0)     # until init_pacman_position() puts Pac-Man in a maze

SPEED_BOOST_FACTOR = 1.6


class Pacman(Entity):
    """Pac-Man: steered by the keyboard, owns the lives"""

    def __init__(self, speed: float, lives: int) -> None:
        """Create Pac-Man; ``init_pacman_position`` places him in a maze

        Args:
            speed: Normal speed in cells per second
            lives: Starting number of lives
        """
        super().__init__(UNPLACED, speed)
        self.normal_speed = speed
        self.lives = lives

    def set_direction(self, direction: Direction) -> None:
        """Remember the wanted direction; it is taken as soon as the way is free"""
        self.next_direction = direction

    def set_speed_boost(self, enabled: bool) -> None:
        """Turn the speed-boost cheat on or off"""
        self.speed = self.normal_speed * (SPEED_BOOST_FACTOR if enabled else 1.0)

    def update(self, maze: Maze, dt: float) -> None:
        """Move for one frame"""
        self.move(maze, dt)

    def init_pacman_position(self, spawn: Cell) -> None:
        """Put Pac-Man on ``spawn`` of a new maze (lives are kept)"""
        self.spawn = spawn
        self.respawn()
