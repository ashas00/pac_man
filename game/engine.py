"""GameEngine: which screen is shown, what the keys do, and the main loop

Screen flow:

    MAIN_MENU -> PLAYING <-> PAUSED
                 PLAYING -> GAME_OVER / VICTORY -> (enter name) -> MAIN_MENU
    MAIN_MENU <-> HIGHSCORES, INSTRUCTIONS

The rules of the game itself are in ``GameSession``
"""

import pygame

from enum import Enum, auto
from typing import Optional

from game.config import GameConfig
from game.geometry import Direction
from game.highscores import MAX_NAME_LENGTH, Highscores, clean_name, is_valid_name_char
from game.renderer import Renderer
from game.session import Cheat, Event, GameSession


FPS = 60
MAX_FRAME_TIME = 0.05      # longer frames (window dragged...) are simulated as 50 ms
READY_DELAY = 1.5          # seconds of "READY!" before a level and after losing a life
MENU_BEST_SCORES = 5

MAIN_MENU_OPTIONS = ("START GAME", "HIGHSCORES", "INSTRUCTIONS", "EXIT")
PAUSE_MENU_OPTIONS = ("RESUME", "MAIN MENU")
INSTRUCTIONS = (
    "GOAL",
    "Eat every pacgum to clear a level.",
    "Super-pacgums (corners) make ghosts edible.",
    "A normal ghost costs a life, so does the timer.",
    "",
    "CONTROLS",
    "Arrows / WASD : move",
    "P / ESC       : pause menu",
    "",
    "CHEATS",
    "I invincible   Z freeze ghosts   B speed boost",
    "L skip level   K extra life      F frighten",
)

ENTER_KEYS = (pygame.K_RETURN, pygame.K_KP_ENTER)
CONFIRM_KEYS = (*ENTER_KEYS, pygame.K_SPACE)
BACK_KEYS = (pygame.K_ESCAPE, pygame.K_BACKSPACE, *CONFIRM_KEYS)
PAUSE_KEYS = (pygame.K_p, pygame.K_ESCAPE)
UP_KEYS = (pygame.K_UP, pygame.K_w)
DOWN_KEYS = (pygame.K_DOWN, pygame.K_s)
STEERING_KEYS = {
    pygame.K_UP: Direction.UP, pygame.K_w: Direction.UP,
    pygame.K_DOWN: Direction.DOWN, pygame.K_s: Direction.DOWN,
    pygame.K_LEFT: Direction.LEFT, pygame.K_a: Direction.LEFT,
    pygame.K_RIGHT: Direction.RIGHT, pygame.K_d: Direction.RIGHT,
}
CHEAT_KEYS = {pygame.K_i: Cheat.INVINCIBLE, pygame.K_z: Cheat.FREEZE, pygame.K_b: Cheat.BOOST}


class Screen(Enum):
    """What the window currently shows"""

    MAIN_MENU = auto()
    HIGHSCORES = auto()
    INSTRUCTIONS = auto()
    PLAYING = auto()
    PAUSED = auto()
    GAME_OVER = auto()
    VICTORY = auto()


class GameEngine:
    """Current screen, the running game, the highscores and the main loop"""

    def __init__(self, config: GameConfig) -> None:
        """Open the window and load the highscores"""
        self.config = config
        self.highscores = Highscores(config.highscore_filename)
        self.renderer = Renderer(config.cell_size, config.spritesheet_path)
        self.session: Optional[GameSession] = None
        self.screen = Screen.MAIN_MENU
        self.main_menu_index = 0
        self.pause_menu_index = 0
        self.ready_time_left = 0.0
        self.typed_name = ""
        self.running = True

    @property
    def score(self) -> int:
        """Score of the current (or just finished) game"""
        return self.session.score if self.session else 0

    def run(self) -> None:
        """Process input, update and draw until the player quits"""
        try:
            dt = 1.0 / FPS
            while self.running:
                self.handle_events()
                self.update(min(dt, MAX_FRAME_TIME))
                self.draw()
                dt = self.renderer.wait_for_next_frame(FPS)
        finally:
            self.renderer.close()

    def start_game(self) -> None:
        """A new game from level 1"""
        self.session = GameSession(self.config)
        self.show_level_intro()
        self.screen = Screen.PLAYING

    def show_level_intro(self) -> None:
        """Fit the window to the new maze and freeze on "READY!" for a moment"""
        if self.session is not None:
            self.renderer.init_window(self.session.maze)
        self.ready_time_left = READY_DELAY

    def end_game(self, won: bool) -> None:
        """Show the victory or game-over screen with an empty name prompt"""
        self.typed_name = ""
        self.screen = Screen.VICTORY if won else Screen.GAME_OVER

    def go_to_main_menu(self) -> None:
        """Forget the current game and show the main menu"""
        self.session = None
        self.main_menu_index = 0
        self.screen = Screen.MAIN_MENU

    def handle_events(self) -> None:
        """Read the window events (close button and key presses)"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                self.handle_key(event.key, event.unicode)

    def handle_key(self, key: int, char: str = "") -> None:
        """Send one key press to the handler of the current screen"""
        if self.screen == Screen.MAIN_MENU:
            self.handle_main_menu_key(key)
        elif self.screen in (Screen.HIGHSCORES, Screen.INSTRUCTIONS):
            self.handle_text_page_key(key)
        elif self.screen == Screen.PLAYING:
            self.handle_playing_key(key)
        elif self.screen == Screen.PAUSED:
            self.handle_pause_menu_key(key)
        else:
            self.handle_name_entry_key(key, char)

    def handle_main_menu_key(self, key: int) -> None:
        """Move the cursor; ENTER opens the chosen entry, ESC quits"""
        self.main_menu_index = get_cursor_index(key, self.main_menu_index, len(MAIN_MENU_OPTIONS))
        if key == pygame.K_ESCAPE:
            self.running = False
        if key not in CONFIRM_KEYS:
            return
        choice = MAIN_MENU_OPTIONS[self.main_menu_index]
        if choice == "START GAME":
            self.start_game()
        elif choice == "HIGHSCORES":
            self.screen = Screen.HIGHSCORES
        elif choice == "INSTRUCTIONS":
            self.screen = Screen.INSTRUCTIONS
        elif choice == "EXIT":
            self.running = False

    def handle_text_page_key(self, key: int) -> None:
        """Highscores / instructions page: any "back" key returns to the menu"""
        if key in BACK_KEYS:
            self.screen = Screen.MAIN_MENU

    def handle_playing_key(self, key: int) -> None:
        """Steering, pause and cheats"""
        session = self.session
        if session is None:
            return
        if key in PAUSE_KEYS:
            self.pause_menu_index = 0
            self.screen = Screen.PAUSED
        elif key in STEERING_KEYS:
            session.pacman.set_direction(STEERING_KEYS[key])
        elif key in CHEAT_KEYS:
            session.toggle_cheat(CHEAT_KEYS[key])
        elif key == pygame.K_k:
            session.add_life()
        elif key == pygame.K_f:
            session.frighten_ghosts()
        elif key == pygame.K_l:
            self.handle_session_event(session.go_to_next_level())

    def handle_pause_menu_key(self, key: int) -> None:
        """Resume the game or leave it for the main menu"""
        self.pause_menu_index = get_cursor_index(key, self.pause_menu_index,
                                                 len(PAUSE_MENU_OPTIONS))
        if key in PAUSE_KEYS:
            self.screen = Screen.PLAYING
        elif key in CONFIRM_KEYS:
            if PAUSE_MENU_OPTIONS[self.pause_menu_index] == "RESUME":
                self.screen = Screen.PLAYING
            else:
                self.go_to_main_menu()

    def handle_name_entry_key(self, key: int, char: str) -> None:
        """Type a name on the end screen: ENTER saves it, ESC skips"""
        if key == pygame.K_ESCAPE:
            self.go_to_main_menu()
        elif key in ENTER_KEYS:
            name = clean_name(self.typed_name)
            if name is not None:
                self.highscores.add(name, self.score)
                self.go_to_main_menu()
        elif key == pygame.K_BACKSPACE:
            self.typed_name = self.typed_name[:-1]
        elif self.can_type(char):
            self.typed_name += char

    def can_type(self, char: str) -> bool:
        """True if ``char`` may be added to the typed name"""
        if not is_valid_name_char(char) or len(self.typed_name) >= MAX_NAME_LENGTH:
            return False
        return not (char == " " and self.typed_name == "")

    def update(self, dt: float) -> None:
        """Advance the animations and, while playing, the game"""
        self.renderer.animation_time += dt
        if self.screen != Screen.PLAYING or self.session is None:
            return
        if self.ready_time_left > 0:
            self.ready_time_left = max(0.0, self.ready_time_left - dt)
            return
        self.handle_session_event(self.session.update(dt))

    def handle_session_event(self, event: Event) -> None:
        """React to what the game reported"""
        if event == Event.LEVEL_CLEARED:
            self.show_level_intro()
        elif event == Event.LIFE_LOST:
            self.ready_time_left = READY_DELAY
        elif event == Event.GAME_OVER:
            self.end_game(won=False)
        elif event == Event.VICTORY:
            self.end_game(won=True)

    def draw(self) -> None:
        """Draw the current screen"""
        scores = [(entry.name, entry.score) for entry in self.highscores.entries]
        if self.screen == Screen.MAIN_MENU:
            self.renderer.draw_main_menu(MAIN_MENU_OPTIONS, self.main_menu_index,
                                         scores[:MENU_BEST_SCORES])
        elif self.screen == Screen.HIGHSCORES:
            lines = [f"{rank:>2}. {name:<10} {score:>7}"
                     for rank, (name, score) in enumerate(scores, start=1)]
            self.renderer.draw_text_page("HIGHSCORES", lines or ["No scores yet!"])
        elif self.screen == Screen.INSTRUCTIONS:
            self.renderer.draw_text_page("HOW TO PLAY", INSTRUCTIONS)
        elif self.screen in (Screen.GAME_OVER, Screen.VICTORY):
            self.renderer.draw_end_screen(self.screen == Screen.VICTORY, self.score,
                                          self.typed_name)
        elif self.session is not None:
            self.renderer.draw_game(self.session)
            if self.screen == Screen.PAUSED:
                self.renderer.draw_pause_menu(PAUSE_MENU_OPTIONS, self.pause_menu_index)
            elif self.ready_time_left > 0:
                self.renderer.draw_level_banner(self.session.level)
        self.renderer.show_frame()


def get_cursor_index(key: int, index: int, option_count: int) -> int:
    """Move a menu cursor up or down (wrapping around)"""
    if key in UP_KEYS:
        return (index - 1) % option_count
    if key in DOWN_KEYS:
        return (index + 1) % option_count
    return index
