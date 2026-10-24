"""Highscores: the persistent top-10 table

Stored as JSON: {"highscores": [{"name": "Bob", "score": 1200}, ...]}

It never crashes the game: a missing file means "no scores yet", a broken file
or an invalid entry is reported and skipped, a failed save is only reported
"""

import json
import os
import re
import sys
import tempfile
from typing import Any, NamedTuple, Optional, TypeGuard

MAX_NAME_LENGTH = 10
MAX_ENTRIES = 10
NAME_PATTERN = re.compile(r"[A-Za-z0-9 ]+")     # letters, digits and spaces


class HighscoreEntry(NamedTuple):
    """One line of the table"""

    name: str
    score: int


class Highscores:
    """The best ``MAX_ENTRIES`` scores, highest first, saved in a JSON file"""

    def __init__(self, path: str) -> None:
        """Load the table from ``path``."""
        self.path = path
        self.entries: list[HighscoreEntry] = []
        self.load()

    def load(self) -> None:
        """Read the file; problems give an empty (or partial) table and a warning"""
        self.entries = []
        try:
            with open(self.path, "r", encoding="utf-8") as file:
                rows = json.load(file).get("highscores")
        except FileNotFoundError:
            return
        except (OSError, ValueError, AttributeError) as error:
            _warn(f"cannot read highscores '{self.path}' ({error}). Starting empty.")
            return
        for row in rows if isinstance(rows, list) else []:
            entry = _get_entry_from_json(row)
            if entry is None:
                _warn(f"ignoring invalid highscore entry {row!r}")
            else:
                self.entries.append(entry)
        self._sort_and_trim()

    def is_high_enough(self, score: int) -> bool:
        """True if ``score`` would enter the table"""
        if not is_valid_score(score):
            return False
        return len(self.entries) < MAX_ENTRIES or score > self.entries[-1].score

    def add(self, name: str, score: int) -> bool:
        """Insert the entry if it is valid and high enough, then save. True if added"""
        valid_name = clean_name(name)
        if valid_name is None or not self.is_high_enough(score):
            return False
        self.entries.append(HighscoreEntry(valid_name, score))
        self._sort_and_trim()
        self.save()
        return True

    def save(self) -> bool:
        """Write the table safely (temporary file, then rename). False on failure"""
        data = {"highscores": [entry._asdict() for entry in self.entries]}
        temporary_path = ""
        try:
            folder = os.path.dirname(os.path.abspath(self.path))
            with tempfile.NamedTemporaryFile("w", dir=folder, prefix=".highscores-",
                                             delete=False, encoding="utf-8") as file:
                temporary_path = file.name
                json.dump(data, file, indent=2)
            os.replace(temporary_path, self.path)
            return True
        except OSError as error:
            _warn(f"cannot save highscores '{self.path}' ({error})")
            if temporary_path and os.path.exists(temporary_path):
                os.remove(temporary_path)
            return False

    def _sort_and_trim(self) -> None:
        """Highest first (equal scores keep their order), at most ``MAX_ENTRIES``"""
        self.entries.sort(key=lambda entry: entry.score, reverse=True)
        del self.entries[MAX_ENTRIES:]


def is_valid_name_char(char: str) -> bool:
    """True if ``char`` may be typed into a name"""
    return len(char) == 1 and NAME_PATTERN.fullmatch(char) is not None


def clean_name(name: Any) -> Optional[str]:
    """The name without surrounding spaces if it is valid (1-10 letters, digits, spaces)"""
    if not isinstance(name, str):
        return None
    stripped: str = name.strip()
    if 0 < len(stripped) <= MAX_NAME_LENGTH and NAME_PATTERN.fullmatch(stripped):
        return stripped
    return None


def is_valid_score(score: Any) -> TypeGuard[int]:
    """True for a non-negative integer (``True`` / ``False`` do not count)"""
    return isinstance(score, int) and not isinstance(score, bool) and score >= 0


def _get_entry_from_json(row: Any) -> Optional[HighscoreEntry]:
    """An entry from one JSON object, or None if its name or score is invalid"""
    if not isinstance(row, dict):
        return None
    name = clean_name(row.get("name"))
    score = row.get("score")
    if name is None or not is_valid_score(score):
        return None
    return HighscoreEntry(name, score)


def _warn(message: str) -> None:
    """Print a warning on stderr"""
    print(f"[WARN] {message}", file=sys.stderr)
