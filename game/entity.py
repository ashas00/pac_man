"""Entity: anything that walks through the maze along cell centres"""

import math
from typing import Callable, Optional

from game.geometry import Cell, Direction, Position
from game.maze import Maze


class Entity:
    """Shared movement of Pac-Man and the ghosts

    An entity always walks from one cell centre to the next. It can only turn
    on a centre, but it may reverse at any moment
    """

    def __init__(self, spawn: Cell, speed: float) -> None:
        """Place the entity on ``spawn``, standing still

        Args:
            spawn: Cell where the entity starts and respawns
            speed: Cells per second
        """
        self.spawn = spawn
        self.position = Position.from_cell(spawn)
        self.speed = speed
        self.direction = Direction.NONE
        self.next_direction = Direction.NONE   # wanted turn, taken on the next centre

    @property
    def cell(self) -> Cell:
        """The cell the entity is in"""
        return self.position.cell

    def is_on_cell_centre(self) -> bool:
        """True when standing exactly on a cell centre"""
        x, y = self.cell
        return abs(self.position.x - x) < 1e-6 and abs(self.position.y - y) < 1e-6

    def respawn(self) -> None:
        """Go back to the spawn cell and stop"""
        self.position = Position.from_cell(self.spawn)
        self.direction = Direction.NONE
        self.next_direction = Direction.NONE

    def move(self, maze: Maze, dt: float,
             on_cell_centre: Optional[Callable[[], None]] = None) -> None:
        """Walk ``speed * dt`` cells

        The distance is walked centre by centre, so even a very fast entity
        never skips a centre and never passes through a wall

        Args:
            maze: The board
            dt: Elapsed time in seconds
            on_cell_centre: Called on every centre before turning (ghost AI uses it)
        """
        if self.direction != Direction.NONE and self.next_direction == self.direction.opposite:
            self.direction = self.next_direction           # reversing is always allowed

        distance_left = self.speed * dt
        while distance_left > 1e-9:
            if self.is_on_cell_centre():
                self.position = Position.from_cell(self.cell)
                if on_cell_centre is not None:
                    on_cell_centre()
                if maze.can_move(self.cell, self.next_direction):
                    self.direction = self.next_direction
                if not maze.can_move(self.cell, self.direction):
                    self.direction = Direction.NONE
                    return
                distance_to_centre = 1.0
            else:
                distance_to_centre = self._get_distance_to_next_centre()

            step = min(distance_left, distance_to_centre)
            self.position = self.position.get_shifted(self.direction, step)
            distance_left -= step
            if step == distance_to_centre:
                self.position = Position.from_cell(self.cell)    # land exactly on the centre

    def _get_distance_to_next_centre(self) -> float:
        """How far the next centre is along the current direction"""
        if self.direction.dx != 0:
            coordinate, forward = self.position.x, self.direction.dx > 0
        else:
            coordinate, forward = self.position.y, self.direction.dy > 0
        if forward:
            return math.floor(coordinate) + 1 - coordinate
        return coordinate - (math.ceil(coordinate) - 1)
