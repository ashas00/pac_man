"""Renderer: the window and everything drawn in it

Only simple primitives are used (filled rectangles, lines, circles, text and
image copies), each with an MLX equivalent. The renderer never changes the game

The maze is drawn once per level into a background image; every frame only
copies that image, erases eaten pacgums from it and draws the moving parts
"""

import pygame
import sys

from typing import Optional, Sequence

from game.entity import Entity
from game.geometry import Cell, Direction
from game.maze import Item, Maze
from game.session import GameSession
from game.sprites import Sprites


Color = tuple[int, int, int]
BLACK: Color = (0, 0, 0)
WHITE: Color = (255, 255, 255)
GREY: Color = (150, 150, 150)
YELLOW: Color = (255, 255, 0)
RED: Color = (255, 0, 0)
CYAN: Color = (0, 255, 255)
WALL_COLOR: Color = (33, 33, 255)
BLOCK_COLOR: Color = (33, 33, 160)       # the closed cells of the "42"
PACGUM_COLOR: Color = (255, 183, 174)
BOX_COLOR: Color = (20, 20, 40)
GHOST_COLORS: tuple[Color, ...] = (RED, (252, 181, 255), CYAN, (253, 161, 37))

HUD_HEIGHT = 40
MIN_WINDOW_SIZE = (560, 520)      # menus always fit
MAX_WINDOW_SIZE = (1600, 1000)    # cells shrink for huge mazes
MIN_CELL_SIZE = 8
LINE_HEIGHT = 36                  # between menu options


class Renderer:
    """Opens the window and draws the game view and every menu screen"""

    def __init__(self, cell_size: int, spritesheet_path: str) -> None:
        """Open the window (its size is set by ``init_window``)

        Args:
            cell_size: Wanted size of one cell in pixels (may shrink to fit the screen)
            spritesheet_path: Sprite sheet image; plain shapes are drawn if it fails
        """
        pygame.init()
        pygame.display.set_caption("Pac-Man")
        self.wanted_cell_size = cell_size
        self.spritesheet_path = spritesheet_path
        self.clock = pygame.time.Clock()
        self.fonts = {size: pygame.font.SysFont("monospace", size, bold=True)
                      for size in (16, 20, 44)}
        self.animation_time = 0.0
        self.sprites: Optional[Sprites] = None
        self.window_size = MIN_WINDOW_SIZE
        self.screen = pygame.display.set_mode(self.window_size)
        self.cell_size = cell_size
        self.wall_thickness = 1
        self.maze_origin = (0, 0)
        self.board_size: tuple[int, int] = (0, 0)
        self.background = pygame.Surface(self.window_size)
        self.background_maze: Optional[Maze] = None
        self.erased_count = 0

    @property
    def width(self) -> int:
        """Window width in pixels"""
        return self.window_size[0]

    @property
    def height(self) -> int:
        """Window height in pixels"""
        return self.window_size[1]

    def init_window(self, maze: Maze) -> None:
        """Size the window and the sprites for ``maze`` (nothing to do if the size is the same)"""
        if self.board_size == (maze.width, maze.height):
            return
        self.board_size = (maze.width, maze.height)
        self.cell_size = max(MIN_CELL_SIZE, min(
            self.wanted_cell_size,
            MAX_WINDOW_SIZE[0] // maze.width,
            (MAX_WINDOW_SIZE[1] - HUD_HEIGHT) // maze.height,
        ))
        self.wall_thickness = max(1, self.cell_size // 12)
        maze_width = maze.width * self.cell_size + self.wall_thickness
        maze_height = maze.height * self.cell_size + self.wall_thickness
        self.window_size = (max(MIN_WINDOW_SIZE[0], maze_width),
                            max(MIN_WINDOW_SIZE[1], maze_height + HUD_HEIGHT))
        self.maze_origin = ((self.width - maze_width) // 2,
                            HUD_HEIGHT + (self.height - HUD_HEIGHT - maze_height) // 2)
        self.screen = pygame.display.set_mode(self.window_size)
        self.background_maze = None                     # redraw at the new size
        self.init_sprites()

    def init_sprites(self) -> None:
        """Cut the sprites for the current cell size, or fall back to plain shapes"""
        sprite_size = max(4, self.cell_size - self.wall_thickness - 2)
        try:
            self.sprites = Sprites(self.spritesheet_path, sprite_size)
        except (OSError, pygame.error) as error:
            self.sprites = None
            print(f"[WARN] sprites unavailable ({error}); drawing shapes instead.",
                  file=sys.stderr)

    def show_frame(self) -> None:
        """Put the drawn frame on the screen"""
        pygame.display.flip()

    def wait_for_next_frame(self, fps: int) -> float:
        """Keep ``fps`` frames per second; return the real frame time in seconds"""
        return self.clock.tick(fps) / 1000.0

    def close(self) -> None:
        """Close the window"""
        pygame.quit()

    def draw_game(self, session: GameSession) -> None:
        """Maze, ghosts, Pac-Man and the HUD"""
        self.update_background(session.maze)
        self.screen.blit(self.background, (0, 0))
        for ghost in session.ghost_manager.ghosts:
            ghost_frame = None
            if self.sprites is not None:
                ghost_frame = self.sprites.get_ghost_frame(ghost, self.animation_time)
            self.draw_entity(ghost, ghost_frame, GHOST_COLORS[ghost.number])
        pacman_frame = None
        if self.sprites is not None:
            pacman_frame = self.sprites.get_pacman_frame(session.pacman.direction,
                                                         self.animation_time)
        self.draw_entity(session.pacman, pacman_frame, YELLOW)
        self.draw_hud(session)

    def draw_hud(self, session: GameSession) -> None:
        """Score, lives, level and time on the left, active cheats on the right"""
        status = (f"SCORE {session.score}  LIVES {session.pacman.lives}  "
                  f"LEVEL {session.level}  TIME {int(session.time_left)}")
        self.screen.blit(self.fonts[16].render(status, True, WHITE), (10, 12))
        cheat_names = " ".join(sorted(cheat.name for cheat in session.cheats))
        cheats = self.fonts[16].render(cheat_names, True, RED)
        self.screen.blit(cheats, (self.width - cheats.get_width() - 10, 12))

    def update_background(self, maze: Maze) -> None:
        """Draw the maze once per level; afterwards only erase newly eaten pacgums"""
        if self.background_maze is not maze:
            self.background_maze = maze
            self.erased_count = 0
            self.background = pygame.Surface(self.window_size)
            for y in range(maze.height):
                for x in range(maze.width):
                    self.draw_cell((x, y), maze)
        for cell in maze.eaten_cells[self.erased_count:]:
            self.erase_item(cell)
        self.erased_count = len(maze.eaten_cells)

    def draw_cell(self, cell: Cell, maze: Maze) -> None:
        """Draw one cell onto the background: block, item and walls"""
        left, top = self.get_cell_pixels(cell)
        size = self.cell_size
        centre = (left + size // 2, top + size // 2)
        if maze.is_block(cell):
            pygame.draw.rect(self.background, BLOCK_COLOR, (left, top, size, size))
        item = maze.get_item(cell)
        if item == Item.DOT:
            pygame.draw.circle(self.background, PACGUM_COLOR, centre, max(1, size // 14))
        elif item == Item.SUPER_DOT:
            pygame.draw.circle(self.background, PACGUM_COLOR, centre, max(2, size // 6))
        corners = {
            Direction.UP: ((left, top), (left + size, top)),
            Direction.RIGHT: ((left + size, top), (left + size, top + size)),
            Direction.DOWN: ((left, top + size), (left + size, top + size)),
            Direction.LEFT: ((left, top), (left, top + size)),
        }
        for side, (start, end) in corners.items():
            if maze.has_wall(cell, side):
                pygame.draw.line(self.background, WALL_COLOR, start, end, self.wall_thickness)

    def erase_item(self, cell: Cell) -> None:
        """Paint the inside of ``cell`` black on the background (walls stay)"""
        left, top = self.get_cell_pixels(cell)
        margin = self.wall_thickness
        inner_size = self.cell_size - 2 * margin
        pygame.draw.rect(self.background, BLACK, (left + margin, top + margin,
                                                  inner_size, inner_size))

    def draw_entity(self, entity: Entity, frame: Optional[pygame.Surface],
                    fallback_color: Color) -> None:
        """Draw a sprite at the entity position, or a coloured disc without sprites"""
        margin = self.wall_thickness // 2 + 1
        left = int(self.maze_origin[0] + entity.position.x * self.cell_size + margin)
        top = int(self.maze_origin[1] + entity.position.y * self.cell_size + margin)
        if frame is not None:
            self.screen.blit(frame, (left, top))
            return
        half = self.cell_size // 2
        pygame.draw.circle(self.screen, fallback_color,
                           (left + half - margin, top + half - margin), max(2, half - 2))

    def get_cell_pixels(self, cell: Cell) -> tuple[int, int]:
        """Top-left pixel of ``cell``"""
        return (self.maze_origin[0] + cell[0] * self.cell_size,
                self.maze_origin[1] + cell[1] * self.cell_size)

    def draw_pause_menu(self, options: Sequence[str], selected: int) -> None:
        """The pause box in the middle of the frozen game"""
        self.draw_box("PAUSED", options, selected, self.height // 2)

    def draw_level_banner(self, level: int) -> None:
        """'LEVEL n / READY!' below Pac-Man before play starts"""
        self.draw_box(f"LEVEL {level}", ["READY!"], -1, self.height * 3 // 4)

    def draw_box(self, title: str, lines: Sequence[str], selected: int, centre_y: int) -> None:
        """A framed box with a title and menu lines"""
        box_width, box_height = 320, 70 + LINE_HEIGHT * len(lines)
        left, top = (self.width - box_width) // 2, centre_y - box_height // 2
        pygame.draw.rect(self.screen, BOX_COLOR, (left, top, box_width, box_height))
        pygame.draw.rect(self.screen, WHITE, (left, top, box_width, box_height), 2)
        self.draw_text(title, top + 30, YELLOW)
        self.draw_options(lines, selected, top + 75)

    def draw_main_menu(self, options: Sequence[str], selected: int,
                       best_scores: Sequence[tuple[str, int]]) -> None:
        """Title, menu and the best scores underneath"""
        self.draw_screen_frame("PAC-MAN", "UP/DOWN + ENTER")
        y = self.draw_options(options, selected, 150) + 20
        if best_scores:
            self.draw_text("HIGHSCORES", y, CYAN, 16)
            for rank, (name, score) in enumerate(best_scores, start=1):
                self.draw_text(f"{rank}. {name} - {score} pts", y + 24 * rank, WHITE, 16)

    def draw_text_page(self, title: str, lines: Sequence[str]) -> None:
        """A page of text (highscores, instructions); upper-case lines are headings"""
        self.draw_screen_frame(title, "ESC / ENTER: back")
        for index, line in enumerate(lines):
            self.draw_text(line, 120 + 26 * index, CYAN if line.isupper() else WHITE, 16)

    def draw_end_screen(self, won: bool, score: int, typed_name: str) -> None:
        """Game over or victory: final score and the name prompt"""
        title, color = ("YOU WIN!", YELLOW) if won else ("GAME OVER", RED)
        self.draw_screen_frame(title, "ENTER: save   ESC: skip", color)
        if won:
            self.draw_text("Congratulations, all levels cleared!", 120)
        self.draw_text(f"FINAL SCORE: {score}", 180, CYAN)
        self.draw_text("Enter your name (max 10, A-Z 0-9 space):", 250, WHITE, 16)
        cursor = "_" if int(self.animation_time * 2) % 2 == 0 else " "
        self.draw_text(typed_name + cursor, 290, YELLOW)

    def draw_screen_frame(self, title: str, hint: str, title_color: Color = YELLOW) -> None:
        """Clear the screen, big title at the top, grey hint at the bottom"""
        self.screen.fill(BLACK)
        self.draw_text(title, 60, title_color, 44)
        self.draw_text(hint, self.height - 25, GREY, 16)

    def draw_options(self, options: Sequence[str], selected: int, top: int) -> int:
        """A vertical list; the selected one is yellow. Return the y below the list"""
        y = top
        for index, option in enumerate(options):
            if index == selected:
                self.draw_text(f"> {option} <", y, YELLOW)
            else:
                self.draw_text(option, y, WHITE)
            y += LINE_HEIGHT
        return y

    def draw_text(self, text: str, y: int, color: Color = WHITE, size: int = 20) -> None:
        """``text`` centred horizontally at height ``y``"""
        surface = self.fonts[size].render(text, True, color)
        self.screen.blit(surface, surface.get_rect(center=(self.width // 2, y)))
