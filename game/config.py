"""Game configuration: JSON with comments, validated key by key with safe defaults"""

import json
import sys
from typing import Any, NamedTuple, Optional

from pydantic import BaseModel, Field, ValidationError


class LevelConfig(BaseModel):
    """Optional overrides for one level; missing values come from the main config"""

    width: Optional[int] = Field(default=None, ge=5, le=100)
    height: Optional[int] = Field(default=None, ge=5, le=100)
    level_max_time: Optional[float] = Field(default=None, gt=0, le=3600)
    seed: Optional[int] = None


class LevelSettings(NamedTuple):
    """Final settings of one level (overrides merged with the defaults)"""

    width: int
    height: int
    max_time: float
    seed: int


class GameConfig(BaseModel):
    """Every tunable setting, with its default and allowed range"""

    highscore_filename: str = "highscores.json"
    spritesheet_path: str = "assets/spritesheet.png"
    width: int = Field(default=19, ge=5, le=100)
    height: int = Field(default=21, ge=5, le=100)
    cell_size: int = Field(default=32, ge=8, le=120)
    lives: int = Field(default=3, ge=1, le=99)
    points_per_pacgum: int = Field(default=10, ge=0)
    points_per_super_pacgum: int = Field(default=50, ge=0)
    points_per_ghost: int = Field(default=200, ge=0)
    player_speed: float = Field(default=5.0, gt=0, le=20)
    ghost_speed: float = Field(default=4.5, gt=0, le=20)
    seed: int = 42
    level_count: int = Field(default=10, ge=1, le=100)
    pacgum: int = Field(default=0, ge=0)
    pacgum_percent: float = Field(default=100, gt=0, le=100)
    level_max_time: float = Field(default=90.0, gt=0, le=3600)
    frightened_duration: float = Field(default=7.0, gt=0, le=60)
    ghost_respawn_delay: float = Field(default=5.0, ge=0, le=60)
    levels: list[LevelConfig] = Field(default_factory=list)

    @property
    def total_levels(self) -> int:
        """Number of levels: ``level_count``, or more if ``levels`` lists more"""
        return max(self.level_count, len(self.levels))

    def get_level_settings(self, number: int) -> LevelSettings:
        """Fully resolved settings of level ``number`` (1-based)

        Level 1 uses ``seed``; later levels are random (seed 0) unless the
        ``levels`` list says otherwise
        """
        override = self.levels[number - 1] if (number <= len(self.levels)) else LevelConfig()
        default_seed = self.seed if number == 1 else 0
        return LevelSettings(
            width=override.width or self.width,
            height=override.height or self.height,
            max_time=override.level_max_time or self.level_max_time,
            seed=default_seed if override.seed is None else override.seed,
        )


def strip_json_comments(text: str) -> str:
    """Remove ``# ...``, ``// ...`` and ``/* ... */`` comments that are outside strings"""
    result: list[str] = []
    index = 0
    inside_string = False
    while index < len(text):
        char = text[index]
        if inside_string:
            if char == "\\":                       # keep escaped characters as they are
                result.append(text[index:index + 2])
                index += 2
                continue
            inside_string = char != '"'
            result.append(char)
        elif char == "#" or text.startswith("//", index):
            index = len(text) if text.find("\n", index) == -1 else text.find("\n", index)
            continue
        elif text.startswith("/*", index):
            index = (len(text) if text.find("*/", index + 2) == -1
                     else text.find("*/", index + 2) + 2)
            continue
        else:
            inside_string = char == '"'
            result.append(char)
        index += 1
    return "".join(result)


def load_config(path: str) -> GameConfig:
    """Read ``path``; any problem is reported on stderr and replaced by defaults

    Unknown keys are ignored. An invalid value only resets that key
    """
    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.loads(strip_json_comments(file.read()))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        _warn(f"cannot read config '{path}': {error}. Using defaults.")
        return GameConfig()
    if not isinstance(data, dict):
        _warn("config root must be a JSON object. Using defaults.")
        return GameConfig()
    return _validate(data)


def _validate(data: dict[str, Any]) -> GameConfig:
    """Build the config; every key with an invalid value is dropped with a warning"""
    known = {key: value for key, value in data.items() if key in GameConfig.model_fields}
    while True:
        try:
            return GameConfig.model_validate(known)
        except ValidationError as error:
            problems = {str(problem["loc"][0]): problem["msg"]
                        for problem in error.errors() if problem["loc"]}
            invalid_keys = problems.keys() & known.keys()
            if not invalid_keys:
                return GameConfig()
            for key in invalid_keys:
                default = GameConfig.model_fields[key].get_default(call_default_factory=True)
                _warn(f"config key '{key}': {problems[key]} (got {known.pop(key)!r}). "
                      f"Using default {default!r}.")


def _warn(message: str) -> None:
    """Print a configuration warning on stderr"""
    print(f"[WARN] {message}", file=sys.stderr)
