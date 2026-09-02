#!/home/ty/legopi-venv/bin/python
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "legopi"))
from runtime.intent import route  # noqa: E402

text = " ".join(sys.argv[1:]).strip()
if not text:
    print(json.dumps({"action":"UNKNOWN"}))
    raise SystemExit(0)

intent = route(text)
result = {"action": intent.action, "source": intent.source}
if intent.set_num: result["set_num"] = intent.set_num
if intent.set_name: result["set_name"] = intent.set_name
if intent.part_num: result["part_num"] = intent.part_num
if intent.color: result["color"] = intent.color
if intent.level is not None: result["level"] = intent.level
print(json.dumps(result))
