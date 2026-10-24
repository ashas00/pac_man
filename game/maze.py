"""Maze: the board of one level, built from the external A-Maze-ing package

The package is used as-is. Only its ``maze`` property is read: a grid of 4-bit
wall codes (1 = north, 2 = east, 4 = south, 8 = west). Cells with all four
walls are the closed blocks that draw the "42" pattern. Everything else
(spawn points, pacgums) is decided here
"""

import random
from collections import deque
from enum import Enum

from mazegenerator import MazeGenerator

from game.geometry import MOVES, Cell, Direction

NORTH, EAST, SOUTH, WEST = 1, 2, 4, 8
ALL_WALLS = NORTH | EAST | SOUTH | WEST
WALL_BIT: dict[Direction, int] = {
    Direction.UP: NORTH, Direction.RIGHT: EAST, Direction.DOWN: SOUTH, Direction.LEFT: WEST,
}


class Item(Enum):
    """What lies on a cell"""

    NONE = 0
    DOT = 1          # pacgum
    SUPER_DOT = 2    # super-pacgum


class MazeError(Exception):
    """The generator failed or returned something unusable"""


class Maze:
    """Walls, items and spawn points of one level"""

    def __init__(self, walls: list[list[int]], pacman_spawn: Cell,
                 corners: tuple[Cell, Cell, Cell, Cell]) -> None:
        """Create a maze from a wall grid; items are placed by ``generate``.

        Args:
            walls: ``walls[y][x]`` = 4-bit wall code of each cell
            pacman_spawn: Cell where Pac-Man starts (closest to the centre)
            corners: Top-left, top-right, bottom-left and bottom-right home cells
        """
        self.walls = walls
        self.items = [[Item.NONE] * len(row) for row in walls]
        self.pacman_spawn = pacman_spawn
        self.corners = corners
        self.items_left = 0
        self.eaten_cells: list[Cell] = []     # read by the renderer to erase pacgums
        self.path_cache: dict[Cell, dict[Cell, int]] = {}   # cache of get_path_to

    @classmethod
    def generate(cls, width: int, height: int, seed: int, pacgum_limit: int = 0,
                 pacgum_percent: float = 100) -> "Maze":
        """Generate a maze and fill it with pacgums

        Args:
            width: Columns
            height: Rows
            seed: Generator seed; 0 or less gives a random maze
            pacgum_limit: Number of pacgums; 0 = use ``pacgum_percent``
            pacgum_percent: Share of the free cells that get a pacgum
                The four super-pacgums in the corners are always placed

        Raises:
            MazeError: If the generator crashes or returns a grid of the wrong shape
        """
        try:
            raw = MazeGenerator(size=(width, height), perfect=False, seed=seed).maze
            walls = [[int(code) & ALL_WALLS for code in row] for row in raw]
        except Exception as error:
            raise MazeError(f"maze generator failed ({type(error).__name__}: {error})")
        if len(walls) != height or any(len(row) != width for row in walls):
            raise MazeError(f"generator returned a maze of the wrong size, wanted {width}x{height}")

        open_cells = {(x, y) for y in range(height) for x in range(width)
                      if walls[y][x] != ALL_WALLS}
        if not open_cells:
            raise MazeError("generated maze has no free cell")
        spawn = _get_nearest_cell(open_cells, (width - 1) / 2, (height - 1) / 2)

        maze = cls(walls, spawn, (spawn, spawn, spawn, spawn))   # real corners below
        reachable = set(maze.get_path_to(spawn))
        maze.corners = (
            _get_nearest_cell(reachable, 0, 0),
            _get_nearest_cell(reachable, width - 1, 0),
            _get_nearest_cell(reachable, 0, height - 1),
            _get_nearest_cell(reachable, width - 1, height - 1),
        )
        maze.init_items(reachable, pacgum_limit, pacgum_percent, seed)
        return maze

    def init_items(self, cells: set[Cell], pacgum_limit: int, pacgum_percent: float,
                   seed: int) -> None:
        """Super-pacgums on the corners, pacgums on the other ``cells`` (except the spawn)"""
        dot_cells = sorted(cells - set(self.corners) - {self.pacman_spawn})
        count = pacgum_limit or round(len(dot_cells) * pacgum_percent / 100)
        if count < len(dot_cells):
            dot_cells = random.Random(seed if seed > 0 else None).sample(dot_cells, count)
        for x, y in dot_cells:
            self.items[y][x] = Item.DOT
        for x, y in set(self.corners) - {self.pacman_spawn}:
            self.items[y][x] = Item.SUPER_DOT
        self.items_left = sum(item != Item.NONE for row in self.items for item in row)

    def get_path_to(self, target: Cell) -> dict[Cell, int]:
        """Steps from every reachable cell to ``target`` (cached, eaten eyes ask often)"""
        if target not in self.path_cache:
            distances, queue = {target: 0}, deque([target])
            while queue:
                cell = queue.popleft()
                for direction in self.get_open_directions(cell):
                    neighbour = (cell[0] + direction.dx, cell[1] + direction.dy)
                    if neighbour not in distances:
                        distances[neighbour] = distances[cell] + 1
                        queue.append(neighbour)
            self.path_cache[target] = distances
        return self.path_cache[target]

    def get_shortest_step(self, cell: Cell, target: Cell) -> Direction:
        """First step of a shortest path from ``cell`` to ``target``"""
        distances = self.get_path_to(target)
        return min(self.get_open_directions(cell), default=Direction.NONE,
                   key=lambda direction: distances.get(
                       (cell[0] + direction.dx, cell[1] + direction.dy), len(distances)))

    @property
    def width(self) -> int:
        """Number of columns"""
        return len(self.walls[0])

    @property
    def height(self) -> int:
        """Number of rows"""
        return len(self.walls)

    def is_inside(self, cell: Cell) -> bool:
        """True if ``cell`` is on the board"""
        return 0 <= cell[0] < self.width and 0 <= cell[1] < self.height

    def is_block(self, cell: Cell) -> bool:
        """True for a closed cell (walls on all four sides, part of the "42")"""
        return self.walls[cell[1]][cell[0]] == ALL_WALLS

    def has_wall(self, cell: Cell, direction: Direction) -> bool:
        """True if ``cell`` has a wall on the ``direction`` side"""
        return bool(self.walls[cell[1]][cell[0]] & WALL_BIT[direction])

    def can_move(self, cell: Cell, direction: Direction) -> bool:
        """True if one step from ``cell`` in ``direction`` is allowed"""
        if direction == Direction.NONE or not self.is_inside(cell):
            return False
        target = (cell[0] + direction.dx, cell[1] + direction.dy)
        return (self.is_inside(target) and not self.has_wall(cell, direction)
                and not self.is_block(target))

    def get_open_directions(self, cell: Cell) -> list[Direction]:
        """Every direction one can step to from ``cell`` (in arcade priority order)"""
        return [direction for direction in MOVES if self.can_move(cell, direction)]

    def get_item(self, cell: Cell) -> Item:
        """The item lying on ``cell``"""
        return self.items[cell[1]][cell[0]]

    def eat_item(self, cell: Cell) -> Item:
        """Remove and return the item on ``cell`` (``Item.NONE`` if there was nothing)"""
        item = self.get_item(cell)
        if item != Item.NONE:
            self.items[cell[1]][cell[0]] = Item.NONE
            self.items_left -= 1
            self.eaten_cells.append(cell)
        return item


def _get_nearest_cell(cells: set[Cell], x: float, y: float) -> Cell:
    """The cell of ``cells`` closest to (x, y); ties go to the top-left one"""
    return min(cells, key=lambda cell: ((cell[0] - x) ** 2 + (cell[1] - y) ** 2,
                                        cell[1], cell[0]))
