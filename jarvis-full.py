#!/home/ty/legopi-venv/bin/python
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "legopi"
sys.path.insert(0, str(ROOT))

from runtime.intent import route  # noqa: E402
from runtime.jarvis import dispatch  # noqa: E402
from runtime.tts import load_env_file, speak  # noqa: E402
from runtime.config import ELEVENLABS_ENV, OPENAI_ENV  # noqa: E402
from runtime.voice import VoiceEngine  # noqa: E402


def main() -> None:
    os.environ.update(load_env_file(OPENAI_ENV))
    os.environ.update(load_env_file(ELEVENLABS_ENV))
    voice = VoiceEngine(speak)
    while True:
        try:
            voice.wait_for_wake()
            speak("Yes?")
            time.sleep(0.10)
            command = voice.record_command()
            if command:
                dispatch(command)
            voice.rearm()
            print('\nReady. Say "Hey Jarvis".', flush=True)
        except KeyboardInterrupt:
            print("Shutting down.", flush=True)
            return
        except Exception as exc:
            print(f"VOICE LOOP ERROR: {exc}", flush=True)
            time.sleep(2)


if __name__ == "__main__":
    main()
