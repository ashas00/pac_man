"""GhostManager: moves the four ghosts and decides where each one goes

On every cell centre a ghost picks the open direction that brings it closest
to its target (never turning back unless it is a dead end):

    CHASE       target = its personality's chase cell
    SCATTER     target = its home corner          (global waves, arcade timing)
    FRIGHTENED  runs AWAY from Pac-Man
    EATEN       shortest path home (may turn back), then waits there before reviving
"""

from game.geometry import Cell, Direction, Position
from game.ghost import Ghost, GhostMode, GhostType
from game.maze import Maze

# Arcade level-1 waves as (mode, seconds); the last one lasts forever
WAVES: tuple[tuple[GhostMode, float], ...] = (
    (GhostMode.SCATTER, 7), (GhostMode.CHASE, 20),
    (GhostMode.SCATTER, 7), (GhostMode.CHASE, 20),
    (GhostMode.SCATTER, 5), (GhostMode.CHASE, 20),
    (GhostMode.SCATTER, 5), (GhostMode.CHASE, float("inf")),
)
MAX_EAT_STREAK = 3     # 4th ghost in a row is worth 8x the base points


class WaveTimer:
    """Walks through the scatter / chase schedule"""

    def __init__(self, waves: tuple[tuple[GhostMode, float], ...] = WAVES) -> None:
        """Start with the first wave"""
        self.waves = waves
        self.index = 0
        self.time_in_wave = 0.0

    @property
    def mode(self) -> GhostMode:
        """SCATTER or CHASE"""
        return self.waves[self.index][0]

    def update(self, dt: float) -> bool:
        """Advance the clock. Return True when a new wave starts"""
        self.time_in_wave += dt
        if (self.index == len(self.waves) - 1) or self.time_in_wave < self.waves[self.index][1]:
            return False
        self.index += 1
        self.time_in_wave = 0.0
        return True


class GhostManager:
    """All four ghosts together: timers, waves, steering and scoring"""

    def __init__(self, ghosts: list[Ghost], respawn_delay: float) -> None:
        """Manage ``ghosts``; eaten eyes wait ``respawn_delay`` seconds at home"""
        self.ghosts = ghosts
        self.respawn_delay = respawn_delay
        self.waves = WaveTimer()
        self.eat_streak = 0

    @property
    def blinky(self) -> Ghost:
        """Blinky (Inky needs his position)"""
        return next(ghost for ghost in self.ghosts if ghost.TYPE == GhostType.BLINKY)

    def update(self, maze: Maze, dt: float, pacman_position: Position,
               pacman_direction: Direction) -> None:
        """Advance the waves and the timers, then move every ghost"""
        if self.waves.update(dt):
            self.reverse_all(maze)
        blinky_position = self.blinky.position
        for ghost in self.ghosts:
            ghost.update_timers(dt)
            if ghost.is_waiting_at_home:
                continue

            def choose_direction(ghost: Ghost = ghost) -> None:
                """Called by the ghost on every cell centre it reaches"""
                self.choose_direction(ghost, maze, pacman_position, pacman_direction,
                                      blinky_position)

            ghost.move(maze, dt, on_cell_centre=choose_direction)

    def choose_direction(self, ghost: Ghost, maze: Maze, pacman_position: Position,
                         pacman_direction: Direction, blinky_position: Position) -> None:
        """Set the direction of ``ghost``, which stands on a cell centre"""
        if ghost.mode == GhostMode.EATEN and ghost.is_at_home:
            ghost.set_waiting_at_home(self.respawn_delay)
            return
        if ghost.mode == GhostMode.FRIGHTENED:
            direction = get_best_direction(maze, ghost, pacman_position.cell, run_away=True)
        elif ghost.mode == GhostMode.EATEN:
            direction = maze.get_shortest_step(ghost.cell, ghost.spawn)
        elif self.waves.mode == GhostMode.SCATTER:
            direction = get_best_direction(maze, ghost, ghost.spawn)
        else:
            target = ghost.get_chase_target(pacman_position, pacman_direction, blinky_position)
            direction = get_best_direction(maze, ghost, target)
        ghost.direction = direction
        ghost.next_direction = direction

    def frighten_all(self, duration: float, maze: Maze) -> None:
        """Super-pacgum eaten: every ghost becomes edible and turns around"""
        self.eat_streak = 0
        for ghost in self.ghosts:
            ghost.set_frightened(duration)
        self.reverse_all(maze)

    def eat(self, ghost: Ghost, base_points: int) -> int:
        """Pac-Man eats ``ghost``. Return its points: 1x, 2x, 4x, 8x in a row"""
        ghost.set_eaten()
        points = base_points * 2 ** self.eat_streak
        self.eat_streak = min(self.eat_streak + 1, MAX_EAT_STREAK)
        return int(points)

    def reset_all(self) -> None:
        """Every ghost back to its corner (Pac-Man lost a life)"""
        for ghost in self.ghosts:
            ghost.reset()

    def reverse_all(self, maze: Maze) -> None:
        """Turn moving ghosts around (wave change or super-pacgum), like the arcade"""
        for ghost in self.ghosts:
            back = ghost.direction.opposite
            if ghost.mode == GhostMode.EATEN or back == Direction.NONE:
                continue
            if not ghost.is_on_cell_centre() or maze.can_move(ghost.cell, back):
                ghost.direction = back
                ghost.next_direction = back


def get_best_direction(maze: Maze, ghost: Ghost, target: Cell, run_away: bool = False) -> Direction:
    """The open direction whose next cell is closest to ``target`` (farthest if ``run_away``)

    A ghost never turns back unless it is in a dead end. Ties keep the arcade
    order UP, LEFT, DOWN, RIGHT
    """
    options = maze.get_open_directions(ghost.cell)
    forward = [direction for direction in options if direction != ghost.direction.opposite]
    options = forward or options
    if not options:
        return Direction.NONE

    def get_distance_after_step(direction: Direction) -> float:
        """Squared distance from the next cell in ``direction`` to the target."""
        x, y = ghost.cell
        return Position(x + direction.dx, y + direction.dy).get_distance_squared(
            Position.from_cell(target))

    if run_away:
        return max(options, key=get_distance_after_step)
    return min(options, key=get_distance_after_step)
