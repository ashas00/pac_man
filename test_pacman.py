"""Checks for the Pac-Man project (not part of the submission).

Run from the project root:
    uv run --with pytest pytest -q test_pacman.py
"""

import json
import os
import random
from pathlib import Path
from typing import Any, Iterator

import pygame
import pytest

import game.maze as maze_module
from game.config import GameConfig, LevelConfig, LevelSettings, load_config, strip_json_comments
from game.engine import MAIN_MENU_OPTIONS, GameEngine, Screen
from game.entity import Entity
from game.geometry import MOVES, Direction, Position
from game.ghost import Blinky, Clyde, Ghost, GhostMode, Inky, Pinky, create_ghosts
from game.ghost_manager import GhostManager, WaveTimer, get_best_direction
from game.highscores import MAX_ENTRIES, Highscores, clean_name, is_valid_name_char
from game.maze import EAST, NORTH, SOUTH, WALL_BIT, WEST, Item, Maze, MazeError
from game.pacman import Pacman
from game.renderer import Renderer
from game.session import Cheat, Event, GameSession
from game.sprites import Sprites


@pytest.fixture(scope="session", autouse=True)
def headless_pygame() -> Iterator[None]:
    """Run pygame without a real window or sound card."""
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    pygame.init()
    pygame.display.set_mode((1, 1))
    yield
    pygame.quit()


def make_open_maze(width: int = 10, height: int = 10) -> Maze:
    """A maze with only the outer walls."""
    walls = [[0] * width for _ in range(height)]
    for x in range(width):
        walls[0][x] |= NORTH
        walls[-1][x] |= SOUTH
    for row in walls:
        row[0] |= WEST
        row[-1] |= EAST
    corners = ((0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1))
    return Maze(walls, (width // 2, height // 2), corners)


def write_file(folder: Path, name: str, text: str) -> str:
    """Write ``text`` to ``folder/name`` and return the path."""
    path = folder / name
    path.write_text(text)
    return str(path)


def test_comments_are_removed_but_not_inside_strings() -> None:
    text = '{ # c\n "lives": 5, // c\n /* b */ "name": "a#b//c /* d */" }'
    assert json.loads(strip_json_comments(text)) == {"lives": 5, "name": "a#b//c /* d */"}


def test_bad_value_only_resets_that_key(tmp_path: Path,
                                        capsys: pytest.CaptureFixture[str]) -> None:
    path = write_file(tmp_path, "c.json", '{"lives": -5, "seed": "x", "width": 30, "foo": 1}')
    config = load_config(path)
    assert (config.lives, config.seed, config.width) == (3, 42, 30)
    assert "'lives'" in capsys.readouterr().err


@pytest.mark.parametrize("text", ["{ x", "[1]", ""])
def test_broken_config_gives_defaults(tmp_path: Path, text: str) -> None:
    assert load_config(write_file(tmp_path, "c.json", text)) == GameConfig()


def test_level_settings() -> None:
    levels = [LevelConfig(height=9), LevelConfig(seed=3, width=12)]
    config = GameConfig(seed=7, width=20, levels=levels)
    assert config.get_level_settings(1) == LevelSettings(20, 9, 90.0, 7)
    assert config.get_level_settings(2) == LevelSettings(12, 21, 90.0, 3)
    assert config.get_level_settings(3) == LevelSettings(20, 21, 90.0, 0)


def test_project_config_loads() -> None:
    assert load_config("config.json").total_levels >= 10


def test_geometry() -> None:
    assert Direction.LEFT.opposite == Direction.RIGHT
    assert Direction.NONE.opposite == Direction.NONE
    assert Position(1.5, 2.5).cell == (2, 3)
    assert Position(2.5, 3.5).cell == (3, 4)


@pytest.mark.parametrize("width,height", [(19, 21), (22, 19), (15, 10), (41, 31), (5, 5),
                                          (100, 100)])
def test_generated_maze(width: int, height: int) -> None:
    maze = Maze.generate(width, height, 42)
    assert (maze.width, maze.height) == (width, height)
    assert not maze.is_block(maze.pacman_spawn)
    assert maze.get_item(maze.pacman_spawn) == Item.NONE
    for corner in maze.corners:
        assert maze.get_item(corner) == Item.SUPER_DOT or corner == maze.pacman_spawn
    items_on_board = sum(item != Item.NONE for row in maze.items for item in row)
    assert maze.items_left == items_on_board


def test_real_corners_and_42_pattern() -> None:
    maze = Maze.generate(22, 19, 42)
    assert set(maze.corners) == {(0, 0), (21, 0), (0, 18), (21, 18)}
    blocks = sum(maze.is_block((x, y)) for y in range(19) for x in range(22))
    assert blocks >= 10


def test_pacgum_limit() -> None:
    maze = Maze.generate(22, 19, 42, 42)
    assert sum(item == Item.DOT for row in maze.items for item in row) == 42
    assert sum(item == Item.SUPER_DOT for row in maze.items for item in row) == 4


def test_pacgum_percent() -> None:
    full = Maze.generate(22, 19, 42)
    half = Maze.generate(22, 19, 42, pacgum_percent=50)
    full_dots = sum(item == Item.DOT for row in full.items for item in row)
    half_dots = sum(item == Item.DOT for row in half.items for item in row)
    assert half_dots == round(full_dots / 2)


def test_eaten_eyes_always_reach_home() -> None:
    maze = Maze.generate(19, 21, 42)
    for cell in maze.get_path_to(maze.pacman_spawn):
        ghost = create_ghosts(maze, 4.5)[0]
        manager = GhostManager([ghost], 5)
        ghost.position = Position.from_cell(cell)
        ghost.set_eaten()
        for _ in range(60 * 20):
            manager.update(maze, 1 / 60, Position.from_cell(maze.pacman_spawn), Direction.NONE)
            if ghost.is_waiting_at_home:
                break
        assert ghost.is_waiting_at_home, cell


def test_eat_item() -> None:
    maze = Maze.generate(19, 21, 42)
    corner = maze.corners[0]
    items_before = maze.items_left
    assert maze.eat_item(corner) == Item.SUPER_DOT
    assert maze.eat_item(corner) == Item.NONE
    assert maze.items_left == items_before - 1
    assert maze.eaten_cells == [corner]


class CrashingGenerator:
    """Stands in for MazeGenerator and fails."""

    def __init__(self, **_: Any) -> None:
        raise ValueError("boom")


class WrongSizeGenerator:
    """Stands in for MazeGenerator and returns a 1x1 maze."""

    maze: Any = [[0]]

    def __init__(self, **_: Any) -> None:
        pass


class NoGridGenerator(WrongSizeGenerator):
    """Stands in for MazeGenerator and returns no grid at all."""

    maze = None


@pytest.mark.parametrize("generator", [CrashingGenerator, WrongSizeGenerator, NoGridGenerator])
def test_generator_problems_raise_maze_error(monkeypatch: pytest.MonkeyPatch,
                                             generator: type) -> None:
    monkeypatch.setattr(maze_module, "MazeGenerator", generator)
    with pytest.raises(MazeError):
        Maze.generate(19, 21, 42)


def test_turns_on_next_centre() -> None:
    entity = Entity((5, 5), 5.0)
    maze = make_open_maze()
    entity.next_direction = Direction.RIGHT
    entity.move(maze, 0.1)
    assert entity.position == Position(5.5, 5)
    entity.next_direction = Direction.DOWN
    entity.move(maze, 0.2)
    assert entity.position == Position(6, 5.5)
    assert entity.direction == Direction.DOWN


def test_u_turn_is_immediate() -> None:
    entity = Entity((5, 5), 5.0)
    maze = make_open_maze()
    entity.next_direction = Direction.RIGHT
    entity.move(maze, 0.05)
    entity.next_direction = Direction.LEFT
    entity.move(maze, 0.02)
    assert entity.direction == Direction.LEFT
    assert entity.position.x == pytest.approx(5.15)


def test_fast_entity_never_crosses_a_wall() -> None:
    walls = [[0, 0, 0, EAST, WEST, 0]]
    maze = Maze(walls, (0, 0), ((0, 0), (0, 0), (0, 0), (0, 0)))
    entity = Entity((0, 0), 100.0)
    entity.next_direction = Direction.RIGHT
    entity.move(maze, 0.05)
    assert entity.position == Position(3, 0)


def test_pacman_speed_boost() -> None:
    pacman = Pacman(5.0, 3)
    pacman.set_speed_boost(True)
    assert pacman.speed > 5.0
    pacman.set_speed_boost(False)
    assert pacman.speed == 5.0


def test_chase_targets() -> None:
    pacman_position = Position(10, 10)
    corner = (0, 19)
    blinky = Blinky(corner, 4)
    assert blinky.get_chase_target(pacman_position, Direction.RIGHT, Position()) == (10, 10)
    pinky = Pinky(corner, 4)
    assert pinky.get_chase_target(pacman_position, Direction.UP, Position()) == (6, 6)
    inky = Inky(corner, 4)
    assert inky.get_chase_target(pacman_position, Direction.RIGHT, Position(8, 10)) == (16, 10)
    clyde = Clyde(corner, 4)
    clyde.position = Position(10, 2)
    assert clyde.get_chase_target(pacman_position, Direction.RIGHT, Position()) == (10, 10)
    clyde.position = Position(10, 5)
    assert clyde.get_chase_target(pacman_position, Direction.RIGHT, Position()) == corner


def test_best_direction() -> None:
    maze = make_open_maze(5, 5)
    ghost = Blinky((2, 2), 4)
    ghost.direction = Direction.RIGHT
    assert get_best_direction(maze, ghost, (1, 1)) == Direction.UP
    assert get_best_direction(maze, ghost, (0, 2)) != Direction.LEFT


def test_wave_timer() -> None:
    timer = WaveTimer(((GhostMode.SCATTER, 2), (GhostMode.CHASE, float("inf"))))
    assert not timer.update(1)
    assert timer.update(1.1)
    assert timer.mode == GhostMode.CHASE
    assert not timer.update(1e9)


def test_frightened_ghost_runs_away() -> None:
    ghost = Blinky((5, 5), 4.0)
    manager = GhostManager([ghost], 5.0)
    maze = make_open_maze()
    manager.frighten_all(5, maze)
    for _ in range(30):
        manager.update(maze, 1 / 60, Position(2, 5), Direction.NONE)
    assert ghost.position.get_distance_squared(Position(2, 5)) > 9


def test_eating_ghosts_doubles_points() -> None:
    ghosts: list[Ghost] = [Blinky((0, 0), 4), Pinky((0, 0), 4), Inky((0, 0), 4),
                           Clyde((0, 0), 4)]
    manager = GhostManager(ghosts, 5)
    manager.frighten_all(7, make_open_maze())
    assert [manager.eat(ghost, 200) for ghost in ghosts] == [200, 400, 800, 1600]


def test_eaten_eyes_go_home_and_revive() -> None:
    ghost = Blinky((0, 0), 4.0)
    ghost.position = Position(6, 6)
    manager = GhostManager([ghost], 2.0)
    maze = make_open_maze()
    manager.eat(ghost, 200)
    for _ in range(300):
        manager.update(maze, 1 / 60, Position(9, 9), Direction.NONE)
        if ghost.is_waiting_at_home:
            break
    assert ghost.position == Position(0, 0)
    assert not ghost.is_dangerous
    manager.update(maze, 2.5, Position(9, 9), Direction.NONE)
    assert ghost.is_dangerous
    assert ghost.speed == 4.0


@pytest.mark.parametrize("width,height", [(19, 21), (41, 31)])
def test_nobody_walks_through_walls(width: int, height: int) -> None:
    """30 seconds of random play; every step is checked against the raw wall bits."""
    maze = Maze.generate(width, height, 42)
    pacman = Pacman(5, 3)
    pacman.init_pacman_position(maze.pacman_spawn)
    manager = GhostManager(create_ghosts(maze, 4.5), 1.0)
    rng = random.Random(5)
    entities: list[Entity] = [pacman, *manager.ghosts]
    last_cell = {id(entity): entity.cell for entity in entities}
    for frame in range(1800):
        if frame % 20 == 0:
            pacman.set_direction(rng.choice(MOVES))
        if frame == 600:
            manager.frighten_all(5, maze)
        if frame == 700:
            manager.eat(manager.blinky, 200)
        pacman.update(maze, 1 / 60)
        manager.update(maze, 1 / 60, pacman.position, pacman.direction)
        for entity in entities:
            (old_x, old_y), (new_x, new_y) = last_cell[id(entity)], entity.cell
            assert not maze.is_block((new_x, new_y))
            if (old_x, old_y) == (new_x, new_y):
                continue
            step = next(d for d in MOVES if (d.dx, d.dy) == (new_x - old_x, new_y - old_y))
            assert not maze.walls[old_y][old_x] & WALL_BIT[step]
            last_cell[id(entity)] = (new_x, new_y)


def touch_ghost(session: GameSession, index: int = 0) -> None:
    """Put a ghost on top of Pac-Man."""
    position = session.pacman.position
    session.ghost_manager.ghosts[index].position = Position(position.x, position.y)


def put_item_under_pacman(session: GameSession, item: Item) -> None:
    """Place ``item`` on Pac-Man's cell."""
    x, y = session.pacman.cell
    session.maze.items[y][x] = item
    session.maze.items_left += 1


def test_spawns_follow_the_subject() -> None:
    session = GameSession(GameConfig())
    width, height = session.maze.width, session.maze.height
    x, y = session.pacman.cell
    assert abs(x - width // 2) <= 3
    assert abs(y - height // 2) <= 3
    corners = {(0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1)}
    assert {ghost.cell for ghost in session.ghost_manager.ghosts} == corners


def test_scoring_uses_the_config() -> None:
    config = GameConfig(points_per_pacgum=3, points_per_super_pacgum=7, points_per_ghost=100)
    session = GameSession(config)
    put_item_under_pacman(session, Item.DOT)
    session.eat_item_under_pacman()
    put_item_under_pacman(session, Item.SUPER_DOT)
    session.eat_item_under_pacman()
    assert session.score == 10
    assert session.ghost_manager.ghosts[1].is_edible
    touch_ghost(session)
    session.check_ghost_collisions()
    assert session.score == 110


def test_ghost_and_timer_cost_lives() -> None:
    session = GameSession(GameConfig(lives=2, level_max_time=5))
    touch_ghost(session)
    assert session.check_ghost_collisions() == Event.LIFE_LOST
    assert session.pacman.lives == 1
    assert session.update(6) == Event.GAME_OVER
    session = GameSession(GameConfig(level_max_time=5))
    assert session.update(6) == Event.LIFE_LOST
    assert session.time_left == 5


def test_levels_keep_score_and_lives() -> None:
    session = GameSession(GameConfig(level_count=3, seed=1))
    session.score = 500
    session.pacman.lives = 2
    for row in session.maze.items:
        for index in range(len(row)):
            row[index] = Item.NONE
    session.maze.items_left = 0
    assert session.update(1 / 60) == Event.LEVEL_CLEARED
    assert (session.level, session.score, session.pacman.lives) == (2, 500, 2)
    assert session.go_to_next_level() == Event.LEVEL_CLEARED
    assert session.go_to_next_level() == Event.VICTORY


def test_cheats() -> None:
    normal = GameSession(GameConfig())
    cheater = GameSession(GameConfig())
    for cheat in Cheat:
        cheater.toggle_cheat(cheat)
    touch_ghost(cheater)
    assert cheater.check_ghost_collisions() == Event.NOTHING
    way = next(d for d in MOVES if normal.maze.can_move(normal.pacman.cell, d))
    ghost_cells = [ghost.cell for ghost in cheater.ghost_manager.ghosts]
    for session in (normal, cheater):
        session.pacman.set_direction(way)
        session.update(0.1)
    spawn = Position.from_cell(normal.pacman.spawn)
    cheater_distance = cheater.pacman.position.get_distance_squared(spawn)
    normal_distance = normal.pacman.position.get_distance_squared(spawn)
    assert cheater_distance > normal_distance
    assert [ghost.cell for ghost in cheater.ghost_manager.ghosts] == ghost_cells


def test_name_rules() -> None:
    assert clean_name(" Bob ") == "Bob"
    assert clean_name("a" * 11) is None
    assert clean_name("é") is None
    assert clean_name(5) is None
    assert is_valid_name_char(" ")
    assert not is_valid_name_char("-")


@pytest.mark.parametrize("content", ["{x", "[]", '{"highscores": 5}'])
def test_corrupt_highscore_file(tmp_path: Path, content: str) -> None:
    assert Highscores(write_file(tmp_path, "h.json", content)).entries == []


def test_highscore_table(tmp_path: Path) -> None:
    path = str(tmp_path / "h.json")
    table = Highscores(path)
    for index in range(12):
        table.add(f"P{index}", index * 100)
    assert len(table.entries) == MAX_ENTRIES
    assert table.entries[0].score == 1100
    assert Highscores(path).entries == table.entries
    assert not table.add("bad!", 9999)
    assert not table.add("Low", 5)
    rows = [{"name": "Ok", "score": 1}, {"name": "x", "score": True}, 3]
    mixed = write_file(tmp_path, "h2.json", json.dumps({"highscores": rows}))
    assert [entry.name for entry in Highscores(mixed).entries] == ["Ok"]


def test_highscore_save_failure(tmp_path: Path) -> None:
    folder = tmp_path / "folder"
    folder.mkdir()
    table = Highscores(str(folder))
    assert not table.save()
    assert table.add("Bob", 1)
    assert not [name for name in os.listdir(tmp_path) if name.startswith(".highscores-")]


@pytest.fixture
def engine(tmp_path: Path) -> GameEngine:
    """An engine whose highscores live in a temporary file."""
    return GameEngine(GameConfig(highscore_filename=str(tmp_path / "h.json"), level_count=2))


def press(engine: GameEngine, *keys: int, text: str = "") -> None:
    """Press keys, type text, then run and draw one frame."""
    for key in keys:
        engine.handle_key(key)
    for char in text:
        engine.handle_key(pygame.K_a, char)
    engine.update(1 / 60)
    engine.draw()


def screen_of(engine: GameEngine) -> Screen:
    """Read the screen through a call (stops mypy from over-narrowing)."""
    return engine.screen


def running_session(engine: GameEngine) -> GameSession:
    """The running session (fails the test if there is none)."""
    assert engine.session is not None
    return engine.session


def test_menus(engine: GameEngine) -> None:
    press(engine, pygame.K_UP)
    assert engine.main_menu_index == len(MAIN_MENU_OPTIONS) - 1
    for name, page in (("HIGHSCORES", Screen.HIGHSCORES), ("INSTRUCTIONS", Screen.INSTRUCTIONS)):
        engine.main_menu_index = MAIN_MENU_OPTIONS.index(name)
        press(engine, pygame.K_RETURN)
        assert screen_of(engine) == page
        press(engine, pygame.K_ESCAPE)
        assert screen_of(engine) == Screen.MAIN_MENU
    press(engine, pygame.K_DOWN, pygame.K_RETURN)
    assert not engine.running


def test_pause_freezes_the_game(engine: GameEngine) -> None:
    press(engine, pygame.K_RETURN)
    engine.ready_time_left = 0
    press(engine, pygame.K_p)
    time_left = running_session(engine).time_left
    for _ in range(20):
        press(engine)
    assert screen_of(engine) == Screen.PAUSED
    assert running_session(engine).time_left == time_left
    press(engine, pygame.K_RETURN)
    assert screen_of(engine) == Screen.PLAYING
    press(engine, pygame.K_ESCAPE, pygame.K_DOWN, pygame.K_RETURN)
    assert screen_of(engine) == Screen.MAIN_MENU
    assert engine.session is None


def test_victory_and_name_entry(engine: GameEngine) -> None:
    press(engine, pygame.K_RETURN, pygame.K_k)
    assert running_session(engine).pacman.lives == 4
    press(engine, pygame.K_l)
    assert running_session(engine).level == 2
    assert engine.ready_time_left > 0
    running_session(engine).score = 1234
    press(engine, pygame.K_l)
    assert screen_of(engine) == Screen.VICTORY
    press(engine, text=" Bob!!_42 is too long")
    assert engine.typed_name == "Bob42 is t"
    press(engine, *[pygame.K_BACKSPACE] * 5, pygame.K_RETURN)
    assert screen_of(engine) == Screen.MAIN_MENU
    assert [(entry.name, entry.score) for entry in engine.highscores.entries] == [("Bob42", 1234)]


def test_game_over_needs_a_name_or_escape(engine: GameEngine) -> None:
    press(engine, pygame.K_RETURN)
    running_session(engine).pacman.lives = 1
    engine.ready_time_left = 0
    touch_ghost(running_session(engine))
    press(engine)
    assert screen_of(engine) == Screen.GAME_OVER
    press(engine, pygame.K_RETURN)
    assert screen_of(engine) == Screen.GAME_OVER
    press(engine, pygame.K_ESCAPE)
    assert screen_of(engine) == Screen.MAIN_MENU


@pytest.mark.parametrize("sheet", ["assets/spritesheet.png", "missing.png"])
def test_every_screen_draws(sheet: str) -> None:
    renderer = Renderer(24, sheet)
    session = GameSession(GameConfig())
    renderer.init_window(session.maze)
    assert (renderer.sprites is not None) == (sheet != "missing.png")
    for mode in GhostMode:
        for ghost in session.ghost_manager.ghosts:
            ghost.mode = mode
            ghost.frightened_time_left = 1
        renderer.draw_game(session)
    renderer.draw_pause_menu(["A", "B"], 0)
    renderer.draw_level_banner(1)
    renderer.draw_main_menu(["A"], 0, [("B", 1)])
    renderer.draw_text_page("T", ["H", "x"])
    renderer.draw_end_screen(True, 1, "x")
    renderer.show_frame()


def test_eaten_pacgum_is_erased_from_background() -> None:
    renderer = Renderer(24, "missing.png")
    session = GameSession(GameConfig())
    renderer.init_window(session.maze)
    renderer.draw_game(session)
    corner = session.maze.corners[0]
    left, top = renderer.get_cell_pixels(corner)
    centre = (left + renderer.cell_size // 2, top + renderer.cell_size // 2)
    assert renderer.background.get_at(centre) != pygame.Color("black")
    session.maze.eat_item(corner)
    renderer.draw_game(session)
    assert renderer.background.get_at(centre) == pygame.Color("black")


def test_window_size_limits() -> None:
    renderer = Renderer(32, "missing.png")
    renderer.init_window(Maze.generate(5, 5, 1))
    assert renderer.window_size == (560, 520)
    renderer.init_window(Maze.generate(100, 100, 1))
    assert renderer.width <= 1600
    assert renderer.height <= 1000


def test_sprite_frames() -> None:
    sprites = Sprites("assets/spritesheet.png", 20)
    for direction in Direction:
        assert sprites.get_pacman_frame(direction, 0.3).get_size() == (20, 20)
