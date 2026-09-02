from __future__ import annotations

import json
import re
import urllib.request
from dataclasses import dataclass

from .config import OLLAMA_MODEL, OLLAMA_TIMEOUT, OLLAMA_URL

ACTIONS = {
    "SCAN_BRICK", "ADD_INVENTORY", "LOOKUP_INVENTORY", "START_REBUILD",
    "GET_ACTIVE_SET", "CHECK_VISIBLE_PIECES", "MARK_FOUND", "SYNC_REBRICKABLE",
    "GENERAL_VISION", "DEMO_MODE_ON", "DEMO_MODE_OFF", "DEMO_STATUS", "DEMO_RESET",
    "SET_VOLUME", "WHAT_CAN_YOU_DO", "UNKNOWN",
}

WORD_NUMBERS = {
    "zero":"0", "one":"1", "two":"2", "three":"3", "four":"4", "five":"5",
    "six":"6", "seven":"7", "eight":"8", "nine":"9", "ten":"10",
}

@dataclass(frozen=True)
class Intent:
    action: str
    set_num: str | None = None
    set_name: str | None = None
    part_num: str | None = None
    color: str | None = None
    level: int | None = None
    source: str = "rules"


def normalize(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    text = text.rstrip(".!?,")
    return text


def _spoken_number_phrase_to_digits(text: str) -> str | None:
    words = {
        "zero":"0", "one":"1", "two":"2", "three":"3", "four":"4",
        "five":"5", "six":"6", "seven":"7", "eight":"8", "nine":"9",
    }
    parts = text.split()
    if parts and all(p in words for p in parts):
        value = "".join(words[p] for p in parts)
        return value if len(value) >= 3 else None
    return None


def _contains_any(text: str, phrases: tuple[str, ...]) -> bool:
    return any(p in text for p in phrases)


def fast_route(text: str) -> Intent | None:
    t = normalize(text)
    if not t:
        return Intent("UNKNOWN")

    if _contains_any(t, ("what can you do", "what are your capabilities", "what are you capable of", "tell me what you can do")):
        return Intent("WHAT_CAN_YOU_DO")

    if _contains_any(t, ("reset demo", "reset the demo", "reset demo mode", "restore demo", "restore the demo", "start the demo over", "reset the demonstration", "start the demonstration over")):
        return Intent("DEMO_RESET")

    if _contains_any(t, ("demo mode", "demonstration mode", "demo")) and _contains_any(t, ("on", "start", "enable", "enter", "put me", "turn")):
        return Intent("DEMO_MODE_ON")
    if _contains_any(t, ("normal mode", "demo mode off", "exit demo", "stop demo", "leave demo", "switch back to normal", "return to normal")):
        return Intent("DEMO_MODE_OFF")
    if _contains_any(t, ("are you in demo", "are we in demo", "is demo mode on", "is demo mode active", "what mode are you in", "what mode are we in")):
        return Intent("DEMO_STATUS")
    m = re.fullmatch(r"(?:set |change )?volume(?: to)?\s+([0-9]{1,2}|zero|one|two|three|four|five|six|seven|eight|nine|ten)", t)
    if m:
        raw = m.group(1)
        level = int(raw) if raw.isdigit() else int(WORD_NUMBERS[raw])
        if 0 <= level <= 10:
            return Intent("SET_VOLUME", level=level)
    if t in {"volume up", "turn the volume up", "increase volume", "make it louder"}:
        return Intent("SET_VOLUME", level=10)
    if t in {"volume down", "turn the volume down", "decrease volume", "make it quieter"}:
        return Intent("SET_VOLUME", level=3)

    if _contains_any(t, ("what do you see", "what are you looking at", "describe what you see", "look at this")):
        return Intent("GENERAL_VISION")
    if _contains_any(t, ("where do i have", "where is this piece stored", "where is this brick stored", "where did i put", "what do you have this brick stored")):
        return Intent("LOOKUP_INVENTORY")
    if _contains_any(t, ("add this", "put this", "add that", "put that")) and _contains_any(t, ("brick", "piece", "part", "inventory")):
        return Intent("ADD_INVENTORY")
    if _contains_any(t, ("scan this", "scan the", "what brick is this", "what piece is this", "what part is this", "identify this", "identify the")) and _contains_any(t, ("brick", "piece", "part", "lego")):
        return Intent("SCAN_BRICK")

    if _contains_any(t, ("start rebuilding", "start the rebuild", "rebuild set", "build set", "start building")):
        m = re.search(r"\b(\d{3,7}(?:-\d+)?)\b", t)
        if m:
            return Intent("START_REBUILD", set_num=m.group(1))
        remainder = re.sub(r"start rebuilding|start the rebuild|rebuild set|build set|start building", "", t).strip()
        remainder = re.sub(r"^set\s+", "", remainder)
        spoken = _spoken_number_phrase_to_digits(remainder)
        if spoken:
            return Intent("START_REBUILD", set_num=spoken)
        return Intent("START_REBUILD", set_name=remainder or None)

    if _contains_any(t, ("active rebuild", "current rebuild", "what set are we building", "what set is active")):
        return Intent("GET_ACTIVE_SET")
    if _contains_any(t, ("check the visible pieces", "check visible pieces", "what pieces do i have for this build", "compare the visible pieces")):
        return Intent("CHECK_VISIBLE_PIECES")
    if _contains_any(t, ("mark those pieces found", "mark them found", "mark found", "mark these found")):
        return Intent("MARK_FOUND")
    if _contains_any(t, ("sync rebrickable", "sync rebrickable data", "update rebrickable")):
        return Intent("SYNC_REBRICKABLE")

    return None


def _qwen_prompt(text: str) -> str:
    return (
        "Classify one LEGO Pi voice command. Return JSON only, exactly one action.\n"
        "Actions: SCAN_BRICK, ADD_INVENTORY, LOOKUP_INVENTORY, START_REBUILD, GET_ACTIVE_SET, "
        "CHECK_VISIBLE_PIECES, MARK_FOUND, SYNC_REBRICKABLE, GENERAL_VISION, DEMO_MODE_ON, "
        "DEMO_MODE_OFF, DEMO_STATUS, DEMO_RESET, SET_VOLUME, WHAT_CAN_YOU_DO, UNKNOWN.\n"
        "Examples: 'put me in demo mode' => DEMO_MODE_ON; 'switch back to normal mode' => DEMO_MODE_OFF; "
        "'reset the demonstration' => DEMO_RESET; 'what do you have this brick stored?' => LOOKUP_INVENTORY; "
        "'set volume to five' => SET_VOLUME with level 5; 'what can you do' => WHAT_CAN_YOU_DO.\n"
        f"User: {text}\nJSON:"
    )


def qwen_route(text: str) -> Intent:
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": _qwen_prompt(text),
        "stream": False,
        "format": "json",
        "keep_alive": "10m",
        "options": {"temperature": 0, "num_predict": 24},
    }
    request = urllib.request.Request(
        f"{OLLAMA_URL}/api/generate",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=OLLAMA_TIMEOUT) as response:
        body = json.loads(response.read().decode())
    data = json.loads(body.get("response", "{}"))
    action = data.get("action", "UNKNOWN")
    if action not in ACTIONS:
        action = "UNKNOWN"
    level = data.get("level")
    try:
        level = int(level) if level is not None else None
    except (TypeError, ValueError):
        level = None
    return Intent(action, set_num=data.get("set_num"), set_name=data.get("set_name"), level=level, source="qwen")


def route(text: str) -> Intent:
    fast = fast_route(text)
    if fast is not None:
        return fast
    try:
        return qwen_route(text)
    except Exception:
        return Intent("UNKNOWN", source="fallback")
