"""GameSession: the rules of one game, from level 1 to victory or game over

It owns the maze, Pac-Man, the ghosts, the score, the level timer and the
cheats. It knows nothing about the window or the keyboard
"""

from enum import Enum, auto

from game.config import GameConfig
from game.ghost import create_ghosts
from game.ghost_manager import GhostManager
from game.maze import Item, Maze
from game.pacman import Pacman

TOUCH_DISTANCE = 0.6     # Pac-Man and a ghost touch when closer than this (in cells)


class Cheat(Enum):
    """Toggle cheats for the evaluation"""

    INVINCIBLE = auto()
    FREEZE = auto()
    BOOST = auto()


class Event(Enum):
    """What happened during one ``GameSession.update``"""

    NOTHING = auto()
    LIFE_LOST = auto()
    LEVEL_CLEARED = auto()
    GAME_OVER = auto()
    VICTORY = auto()


class GameSession:
    """Score, lives, level progression and collisions of one game"""

    def __init__(self, config: GameConfig) -> None:
        """Start a new game on level 1

        Raises:
            MazeError: If the maze generator fails
        """
        self.config = config
        self.score = 0
        self.cheats: set[Cheat] = set()
        self.level = 1
        self.pacman = Pacman(config.player_speed, config.lives)
        self.start_level(self.level)

    def start_level(self, number: int) -> None:
        """Build level ``number``. Score and lives are kept"""
        settings = self.config.get_level_settings(number)
        self.level = number
        self.maze = Maze.generate(settings.width, settings.height, settings.seed,
                                  self.config.pacgum, self.config.pacgum_percent)
        self.pacman.init_pacman_position(self.maze.pacman_spawn)
        self.ghost_manager = GhostManager(create_ghosts(self.maze, self.config.ghost_speed),
                                          self.config.ghost_respawn_delay)
        self.time_limit = settings.max_time
        self.time_left = self.time_limit

    def go_to_next_level(self) -> Event:
        """Next level, or victory after the last one"""
        if self.level >= self.config.total_levels:
            return Event.VICTORY
        self.start_level(self.level + 1)
        return Event.LEVEL_CLEARED

    def update(self, dt: float) -> Event:
        """Play ``dt`` seconds and report what happened"""
        self.time_left -= dt
        if self.time_left <= 0:
            self.time_left = self.time_limit
            return self.lose_life()

        self.pacman.set_speed_boost(Cheat.BOOST in self.cheats)
        self.pacman.update(self.maze, dt)
        self.eat_item_under_pacman()
        if self.maze.items_left == 0:
            return self.go_to_next_level()

        if Cheat.FREEZE not in self.cheats:
            self.ghost_manager.update(self.maze, dt, self.pacman.position,
                                      self.pacman.direction)
        return self.check_ghost_collisions()

    def eat_item_under_pacman(self) -> None:
        """Score the pacgum under Pac-Man; a super-pacgum frightens the ghosts"""
        item = self.maze.eat_item(self.pacman.cell)
        if item == Item.DOT:
            self.score += self.config.points_per_pacgum
        elif item == Item.SUPER_DOT:
            self.score += self.config.points_per_super_pacgum
            self.ghost_manager.frighten_all(self.config.frightened_duration, self.maze)

    def check_ghost_collisions(self) -> Event:
        """Eat touched edible ghosts; touching a dangerous one costs a life"""
        for ghost in self.ghost_manager.ghosts:
            if ghost.position.get_distance_squared(self.pacman.position) > TOUCH_DISTANCE ** 2:
                continue
            if ghost.is_edible:
                self.score += self.ghost_manager.eat(ghost, self.config.points_per_ghost)
            elif ghost.is_dangerous and Cheat.INVINCIBLE not in self.cheats:
                return self.lose_life()
        return Event.NOTHING

    def lose_life(self) -> Event:
        """One life less; everybody goes back home (game over at zero)"""
        self.pacman.lives -= 1
        if self.pacman.lives <= 0:
            return Event.GAME_OVER
        self.pacman.respawn()
        self.ghost_manager.reset_all()
        return Event.LIFE_LOST

    def toggle_cheat(self, cheat: Cheat) -> None:
        """Switch ``cheat`` on or off"""
        self.cheats ^= {cheat}

    def add_life(self) -> None:
        """Cheat: one more life"""
        self.pacman.lives += 1

    def frighten_ghosts(self) -> None:
        """Cheat: make every ghost edible right now"""
        self.ghost_manager.frighten_all(self.config.frightened_duration, self.maze)
