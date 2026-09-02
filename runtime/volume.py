from __future__ import annotations

import re
import subprocess
from pathlib import Path

from .config import VOLUME_COMMAND

WORDS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4,
    "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}


def parse_level(text: str) -> int | None:
    m = re.fullmatch(
        r"(?:set |change )?volume(?: to)?\s+([0-9]{1,2}|zero|one|two|three|four|five|six|seven|eight|nine|ten)",
        text.strip().lower(),
    )
    if not m:
        return None
    raw = m.group(1)
    level = WORDS.get(raw, int(raw)) if raw.isdigit() else WORDS[raw]
    return level if 0 <= level <= 10 else None


def set_volume(level: int) -> bool:
    if not 0 <= int(level) <= 10:
        return False
    return subprocess.run([VOLUME_COMMAND, str(int(level))], check=False).returncode == 0
