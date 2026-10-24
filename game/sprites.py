"""Sprites: animation frames cut from ``assets/spritesheet.png``

The sheet is made of colour palettes; each palette is a block of 16x16 tiles
separated by 1-pixel lines. Tiles are copied pixel by pixel (scaled and, when
needed, mirrored), the same way one would write into an MLX image buffer
"""

import os
import pygame

from game.geometry import Direction
from game.ghost import Ghost, GhostMode


TILE_SIZE = 16
TILE_STRIDE = TILE_SIZE + 1                     # tile + separating line
PALETTE_WIDTH = 22 * 9 + 2
PALETTE_HEIGHT = 9 * 9 + 6 * TILE_STRIDE + 3
TILES_LEFT = 1                                  # offset of the 16x16 tiles in a palette
TILES_TOP = 9 * 9 + 2

PACMAN_PALETTE = (1, 3)
EYES_PALETTE = (1, 1)
FRIGHTENED_BLUE_PALETTE = (2, 0)
FRIGHTENED_WHITE_PALETTE = (0, 0)
GHOST_COLUMN = {Direction.RIGHT: 0, Direction.NONE: 0, Direction.DOWN: 2,
                Direction.LEFT: 4, Direction.UP: 6}

PACMAN_FRAME_TIME = 0.08     # seconds per chomp frame
GHOST_FRAME_TIME = 0.15      # seconds per ghost frame
FLASH_TIME = 0.2             # frightened ghosts flash white / blue ...
FLASH_WHEN_LEFT = 2.0        # ... during their last 2 seconds


class Sprites:
    """Every animation frame, cut from the sheet and scaled to ``size`` pixels"""

    def __init__(self, path: str, size: int) -> None:
        """Load the sheet and cut all frames

        Raises:
            FileNotFoundError: If ``path`` does not exist
            pygame.error: If the image cannot be read
        """
        if not os.path.isfile(path):
            raise FileNotFoundError(path)
        self.sheet = pygame.image.load(path)
        self.size = size

        closed = self.get_tile(PACMAN_PALETTE, 6, 5)
        self.pacman_frames = {
            Direction.NONE: [closed, self.get_tile(PACMAN_PALETTE, 6, 4),
                             self.get_tile(PACMAN_PALETTE, 6, 3)],
            Direction.RIGHT: [closed, self.get_tile(PACMAN_PALETTE, 6, 4),
                              self.get_tile(PACMAN_PALETTE, 6, 3)],
            Direction.LEFT: [closed, self.get_tile(PACMAN_PALETTE, 6, 4, mirror_x=True),
                             self.get_tile(PACMAN_PALETTE, 6, 3, mirror_x=True)],
            Direction.DOWN: [closed, self.get_tile(PACMAN_PALETTE, 7, 4),
                             self.get_tile(PACMAN_PALETTE, 7, 3)],
            Direction.UP: [closed, self.get_tile(PACMAN_PALETTE, 7, 4, mirror_y=True),
                           self.get_tile(PACMAN_PALETTE, 7, 3, mirror_y=True)],
        }
        self.ghost_frames = [
            {direction: [self.get_tile((number, 0), column, 0),
                         self.get_tile((number, 0), column + 1, 0)]
             for direction, column in GHOST_COLUMN.items()}
            for number in range(4)
        ]
        self.eyes_frames = {direction: self.get_tile(EYES_PALETTE, column, 0)
                            for direction, column in GHOST_COLUMN.items()}
        self.frightened_blue_frames = [self.get_tile(FRIGHTENED_BLUE_PALETTE, column, 5)
                                       for column in (0, 1)]
        self.frightened_white_frames = [self.get_tile(FRIGHTENED_WHITE_PALETTE, column, 5)
                                        for column in (0, 1)]

    def get_tile(self, palette: tuple[int, int], column: int, row: int,
                 mirror_x: bool = False, mirror_y: bool = False) -> pygame.Surface:
        """Copy one 16x16 tile, scaled to ``size``; black pixels become transparent"""
        left = palette[0] * PALETTE_WIDTH + TILES_LEFT + column * TILE_STRIDE
        top = palette[1] * PALETTE_HEIGHT + TILES_TOP + row * TILE_STRIDE
        image = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
        for y in range(self.size):
            source_y = y * TILE_SIZE // self.size
            if mirror_y:
                source_y = TILE_SIZE - 1 - source_y
            for x in range(self.size):
                source_x = x * TILE_SIZE // self.size
                if mirror_x:
                    source_x = TILE_SIZE - 1 - source_x
                color = self.sheet.get_at((left + source_x, top + source_y))
                if color.r or color.g or color.b:
                    image.set_at((x, y), color)
        return image

    def get_pacman_frame(self, direction: Direction, time: float) -> pygame.Surface:
        """Chomping animation: closed, half open, wide open, half open"""
        frame_order = (0, 1, 2, 1)
        return (self.pacman_frames[direction]
                [frame_order[int(time / PACMAN_FRAME_TIME) % len(frame_order)]])

    def get_ghost_frame(self, ghost: Ghost, time: float) -> pygame.Surface:
        """Body, frightened body (flashing at the end) or just the eyes"""
        if ghost.mode == GhostMode.EATEN:
            return self.eyes_frames[ghost.direction]
        if ghost.mode == GhostMode.FRIGHTENED:
            if ghost.frightened_time_left <= FLASH_WHEN_LEFT and int(time / FLASH_TIME) % 2 == 0:
                frames = self.frightened_white_frames
            else:
                frames = self.frightened_blue_frames
        else:
            frames = self.ghost_frames[ghost.number][ghost.direction]
        return frames[int(time / GHOST_FRAME_TIME) % 2]
