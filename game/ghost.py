"""Ghost: shared ghost state plus the four personalities (Blinky, Pinky, Inky, Clyde)

A ghost lives in one maze corner. Its life cycle:

    CHASE / SCATTER --super-pacgum--> FRIGHTENED --eaten--> EATEN (eyes go home,
    wait there) --> CHASE again

Where to go is decided by ``GhostManager``; each personality only says which
cell it aims at while chasing
"""

from abc import ABC, abstractmethod
from enum import Enum, auto

from game.entity import Entity
from game.geometry import Cell, Direction, Position
from game.maze import Maze

EATEN_SPEED_FACTOR = 2.0     # eyes go home faster
CLYDE_SHY_DISTANCE = 8       # Clyde flees to his corner when closer than this


class GhostType(Enum):
    """The four personalities; the order matches the sprite sheet colours"""

    BLINKY = auto()
    PINKY = auto()
    INKY = auto()
    CLYDE = auto()


class GhostMode(Enum):
    """What a ghost is doing (CHASE and SCATTER are also the global waves)"""

    CHASE = auto()
    SCATTER = auto()
    FRIGHTENED = auto()
    EATEN = auto()


class Ghost(Entity, ABC):
    """Common state and life cycle of every ghost"""

    TYPE = GhostType.BLINKY

    def __init__(self, home: Cell, speed: float) -> None:
        """Create the ghost on its ``home`` corner (also its scatter target)

        Args:
            home: Corner cell where the ghost starts, scatters to and revives
            speed: Normal speed in cells per second
        """
        super().__init__(home, speed)
        self.normal_speed = speed
        self.number = list(GhostType).index(self.TYPE)    # 0..3, picks the colour
        self.mode = GhostMode.CHASE
        self.frightened_time_left = 0.0
        self.wait_time_left = 0.0

    @property
    def is_dangerous(self) -> bool:
        """True if touching it costs Pac-Man a life"""
        return self.mode in (GhostMode.CHASE, GhostMode.SCATTER)

    @property
    def is_edible(self) -> bool:
        """True if Pac-Man can eat it"""
        return self.mode == GhostMode.FRIGHTENED

    @property
    def is_waiting_at_home(self) -> bool:
        """True while eaten eyes wait in the corner before reviving"""
        return self.mode == GhostMode.EATEN and self.wait_time_left > 0

    @property
    def is_at_home(self) -> bool:
        """True when standing on its home corner"""
        return self.cell == self.spawn

    def set_frightened(self, duration: float) -> None:
        """Become edible for ``duration`` seconds (eaten eyes are not affected)"""
        if self.mode != GhostMode.EATEN:
            self.mode = GhostMode.FRIGHTENED
            self.frightened_time_left = duration

    def set_eaten(self) -> None:
        """Turn into eyes that hurry back home"""
        self.mode = GhostMode.EATEN
        self.frightened_time_left = 0.0
        self.speed = self.normal_speed * EATEN_SPEED_FACTOR

    def set_waiting_at_home(self, delay: float) -> None:
        """Eyes reached home: stay there ``delay`` seconds before reviving"""
        self.wait_time_left = max(delay, 1e-3)
        self.direction = Direction.NONE
        self.next_direction = Direction.NONE

    def reset(self) -> None:
        """Back home in normal mode (after reviving, or when Pac-Man loses a life)"""
        self.respawn()
        self.mode = GhostMode.CHASE
        self.speed = self.normal_speed
        self.frightened_time_left = 0.0
        self.wait_time_left = 0.0

    def update_timers(self, dt: float) -> None:
        """Count down the frightened time and the waiting time"""
        if self.mode == GhostMode.FRIGHTENED:
            self.frightened_time_left -= dt
            if self.frightened_time_left <= 0:
                self.mode = GhostMode.CHASE
                self.frightened_time_left = 0.0
        if self.is_waiting_at_home:
            self.wait_time_left -= dt
            if self.wait_time_left <= 0:
                self.reset()

    @abstractmethod
    def get_chase_target(self, pacman_position: Position, pacman_direction: Direction,
                         blinky_position: Position) -> Cell:
        """The cell this ghost aims at while chasing"""


class Blinky(Ghost):
    """Red: aims straight at Pac-Man"""

    TYPE = GhostType.BLINKY

    def get_chase_target(self, pacman_position: Position, pacman_direction: Direction,
                         blinky_position: Position) -> Cell:
        """Pac-Man's cell"""
        return pacman_position.cell


class Pinky(Ghost):
    """Pink: ambushes 4 cells ahead of Pac-Man"""

    TYPE = GhostType.PINKY

    def get_chase_target(self, pacman_position: Position, pacman_direction: Direction,
                         blinky_position: Position) -> Cell:
        """4 cells ahead of Pac-Man"""
        return get_cell_ahead_of_pacman(pacman_position, pacman_direction, 4)


class Inky(Ghost):
    """Cyan: uses Blinky's position, so he attacks from the other side"""

    TYPE = GhostType.INKY

    def get_chase_target(self, pacman_position: Position, pacman_direction: Direction,
                         blinky_position: Position) -> Cell:
        """Blinky's cell mirrored through the cell 2 ahead of Pac-Man"""
        pivot_x, pivot_y = get_cell_ahead_of_pacman(pacman_position, pacman_direction, 2)
        blinky_x, blinky_y = blinky_position.cell
        return 2 * pivot_x - blinky_x, 2 * pivot_y - blinky_y


class Clyde(Ghost):
    """Orange: chases when far away, runs to his corner when close"""

    TYPE = GhostType.CLYDE

    def get_chase_target(self, pacman_position: Position, pacman_direction: Direction,
                         blinky_position: Position) -> Cell:
        """Pac-Man's cell when 8+ cells away, otherwise the home corner"""
        distance_squared = Position.from_cell(self.cell).get_distance_squared(pacman_position)
        if distance_squared >= CLYDE_SHY_DISTANCE ** 2:
            return pacman_position.cell
        return self.spawn


def get_cell_ahead_of_pacman(pacman_position: Position, pacman_direction: Direction,
                             steps: int) -> Cell:
    """The cell ``steps`` ahead of Pac-Man

    Like the arcade original, facing up also shifts the target ``steps`` to the left
    """
    x, y = pacman_position.cell
    x, y = x + pacman_direction.dx * steps, y + pacman_direction.dy * steps
    if pacman_direction == Direction.UP:
        x -= steps
    return x, y


def create_ghosts(maze: Maze, speed: float) -> list[Ghost]:
    """One ghost of each personality, each in its own corner of ``maze``"""
    top_left, top_right, bottom_left, bottom_right = maze.corners
    return [Blinky(top_right, speed), Pinky(top_left, speed),
            Inky(bottom_right, speed), Clyde(bottom_left, speed)]
