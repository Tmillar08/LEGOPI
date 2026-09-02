from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .config import ELEVENLABS_ENV, TTS_SCRIPT


def load_env_file(path: Path) -> dict[str, str]:
    env = os.environ.copy()
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            env[key.strip()] = value.strip()
    except OSError:
        pass
    return env


def speak(text: str, wait: bool = True) -> None:
    text = str(text).strip()
    if not text:
        return
    cmd = ["/home/ty/legopi-venv/bin/python", str(TTS_SCRIPT), text]
    if wait:
        subprocess.run(cmd, env=load_env_file(ELEVENLABS_ENV), check=False)
    else:
        subprocess.Popen(cmd, env=load_env_file(ELEVENLABS_ENV))
