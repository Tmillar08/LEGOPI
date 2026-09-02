#!/home/ty/legopi-venv/bin/python
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "legopi"))
from runtime.config import LIVE_HOST, LIVE_PORT, OPENAI_ENV, ELEVENLABS_ENV  # noqa: E402
from runtime.tts import load_env_file  # noqa: E402
os.environ.update(load_env_file(OPENAI_ENV))
os.environ.update(load_env_file(ELEVENLABS_ENV))
from runtime.live_server import app  # noqa: E402

if __name__ == "__main__":
    app.run(host=LIVE_HOST, port=LIVE_PORT, threaded=True)
