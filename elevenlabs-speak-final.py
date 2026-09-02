#!/home/ty/legopi-venv/bin/python
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "legopi"))
from runtime.config import ELEVENLABS_ENV, VOICE_ID, VOICE_MODEL
from runtime.tts import load_env_file


def normalize_for_speech(text: str) -> str:
    # Preserve the proven LEGO dimension pronunciation behavior.
    text = re.sub(r"\b(\d+)\s*[xX×]\s*(\d+)\b", r"\1 by \2", text)
    return text.strip()


def main() -> None:
    text = normalize_for_speech(" ".join(sys.argv[1:]))
    if not text:
        raise SystemExit("No text provided")
    from elevenlabs.client import ElevenLabs

    env = load_env_file(ELEVENLABS_ENV)
    api_key = env.get("ELEVENLABS_API_KEY")
    if not api_key:
        raise SystemExit("ELEVENLABS_API_KEY is not configured")

    client = ElevenLabs(api_key=api_key)
    audio = client.text_to_speech.convert(
        voice_id=VOICE_ID,
        model_id=VOICE_MODEL,
        text=text,
        output_format="mp3_44100_128",
        voice_settings={"stability":0.65,"similarity_boost":0.80,"style":0.20,"use_speaker_boost":True},
    )
    fd, mp3_path = tempfile.mkstemp(prefix="legopi-tts-", suffix=".mp3")
    os.close(fd)
    try:
        with open(mp3_path, "wb") as f:
            for chunk in audio:
                f.write(chunk)
        ffmpeg = subprocess.Popen([
            "ffmpeg","-hide_banner","-loglevel","error","-i",mp3_path,
            "-filter:a","volume=0.35","-ac","2","-ar","48000","-c:a","pcm_s32le","-f","wav","-"
        ], stdout=subprocess.PIPE)
        subprocess.run(["aplay","-D","hw:0,0"], stdin=ffmpeg.stdout, check=False)
        if ffmpeg.stdout:
            ffmpeg.stdout.close()
        ffmpeg.wait()
    finally:
        try: os.unlink(mp3_path)
        except OSError: pass


if __name__ == "__main__":
    main()
