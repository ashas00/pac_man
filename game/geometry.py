"""Basic geometry types used everywhere: Direction, Position and Cell"""

import math
from dataclasses import dataclass
from enum import Enum

# A board cell as (column, row)
Cell = tuple[int, int]


class Direction(Enum):
    """One of the four moves (or no move). The value is the (dx, dy) step"""

    UP = (0, -1)
    DOWN = (0, 1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)
    NONE = (0, 0)

    @property
    def dx(self) -> int:
        """Horizontal step: -1, 0 or 1"""
        return self.value[0]

    @property
    def dy(self) -> int:
        """Vertical step: -1, 0 or 1"""
        return self.value[1]

    @property
    def opposite(self) -> "Direction":
        """The direction pointing the other way"""
        return Direction((-self.dx, -self.dy))


# The four real moves, in the arcade tie-break order used by the ghosts
MOVES: tuple[Direction, ...] = (Direction.UP, Direction.LEFT, Direction.DOWN, Direction.RIGHT)


@dataclass
class Position:
    """A point on the board in cell units (x = column, y = row)"""

    x: float = 0.0
    y: float = 0.0

    @property
    def cell(self) -> Cell:
        """The cell whose centre is nearest (halves round up, the same in every direction)"""
        return math.floor(self.x + 0.5), math.floor(self.y + 0.5)

    def get_shifted(self, direction: Direction, distance: float = 1.0) -> "Position":
        """A new position ``distance`` cells away in ``direction``"""
        return Position(self.x + direction.dx * distance, self.y + direction.dy * distance)

    def get_distance_squared(self, other: "Position") -> float:
        """Squared distance to ``other`` (cheaper than the real distance)"""
        return (self.x - other.x) ** 2 + (self.y - other.y) ** 2

    @staticmethod
    def from_cell(cell: Cell) -> "Position":
        """The centre of ``cell``"""
        return Position(float(cell[0]), float(cell[1]))
