from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .config import DEMO_STATE_FILE


def _load() -> dict[str, Any]:
    try:
        with DEMO_STATE_FILE.open(encoding="utf-8") as f:
            state = json.load(f)
        if not isinstance(state, dict):
            raise ValueError("demo state must be an object")
    except (FileNotFoundError, json.JSONDecodeError, OSError, ValueError):
        state = {"enabled": False, "session": None}
    state.setdefault("enabled", False)
    state.setdefault("session", None)
    return state


def _save(state: dict[str, Any]) -> None:
    DEMO_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = DEMO_STATE_FILE.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
        f.write("\n")
    os.replace(tmp, DEMO_STATE_FILE)


def enabled() -> bool:
    return bool(_load().get("enabled", False))


def mode() -> str:
    return "DEMO" if enabled() else "NORMAL"


def set_demo(active: bool) -> str:
    state = _load()
    state["enabled"] = bool(active)
    if not active:
        state["session"] = None
    _save(state)
    return mode()
