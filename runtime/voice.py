from __future__ import annotations

import json
import subprocess
import time
import wave

import numpy as np
import sounddevice as sd
from openwakeword.model import Model as WakeModel
from scipy.signal import resample_poly

from .config import (
    AUDIO_DEVICE,
    BLOCK_SIZE,
    CAPTURE_RATE,
    COMMAND_MAX_SECONDS,
    COMMAND_SILENCE_SECONDS,
    STT_RATE,
    VOSK_MODEL_PATH,
    WAKE_MODEL_PATH,
    WAKE_THRESHOLD,
)
from .intent import normalize


def resample_to_16khz(audio: np.ndarray) -> np.ndarray:
    samples = audio[:, 0].astype(np.float32)
    resampled = resample_poly(samples, up=1, down=3)
    return np.clip(resampled, -32768, 32767).astype(np.int16)


class VoiceEngine:
    def __init__(self, speak):
        self.speak = speak
        self.wake_model = WakeModel(wakeword_model_paths=[str(WAKE_MODEL_PATH)])

    def wait_for_wake(self) -> None:
        print('Ready. Say "Hey Jarvis".', flush=True)
        with sd.InputStream(
            device=AUDIO_DEVICE,
            channels=1,
            samplerate=CAPTURE_RATE,
            dtype="int16",
            blocksize=BLOCK_SIZE,
        ) as stream:
            while True:
                audio, overflowed = stream.read(BLOCK_SIZE)
                if overflowed:
                    print("WAKE AUDIO OVERFLOW", flush=True)
                samples = resample_to_16khz(audio)
                prediction = self.wake_model.predict(samples)
                score = max(prediction.values())
                rms = float(np.sqrt(np.mean(samples.astype(np.float32) ** 2)))
                if score >= WAKE_THRESHOLD:
                    print(
                        f"WAKE DIAGNOSTIC: score={score:.3f} rms={rms:.1f} peak={int(np.max(np.abs(samples)))}",
                        flush=True,
                    )
                    print(f"HEY JARVIS DETECTED - score {score:.3f}", flush=True)
                    return

    def record_command(self) -> str | None:
        """Record until silence after speech, with a hard maximum.

        The old implementation always captured six seconds. This keeps the same OpenAI
        transcription path but stops early after a real silence, reducing dead air.
        """
        wav_path = "/tmp/jarvis-command.wav"
        print("Listening for conversational command...", flush=True)
        started = time.monotonic()
        chunks: list[np.ndarray] = []
        heard_speech = False
        silent_since: float | None = None

        with sd.InputStream(
            device=AUDIO_DEVICE,
            channels=2,
            samplerate=CAPTURE_RATE,
            dtype="int32",
            blocksize=9600,
        ) as stream:
            while time.monotonic() - started < COMMAND_MAX_SECONDS:
                audio, overflowed = stream.read(9600)
                if overflowed:
                    print("COMMAND AUDIO OVERFLOW", flush=True)
                chunks.append(audio.copy())
                mono = audio[:, 0].astype(np.float32)
                rms = float(np.sqrt(np.mean(mono * mono)))
                if rms > 120:
                    heard_speech = True
                    silent_since = None
                elif heard_speech:
                    if silent_since is None:
                        silent_since = time.monotonic()
                    elif time.monotonic() - silent_since >= COMMAND_SILENCE_SECONDS:
                        break

        if not chunks:
            return None
        audio = np.concatenate(chunks, axis=0)
        print(f"TIMING: microphone capture END ({time.monotonic() - started:.3f}s)", flush=True)

        with wave.open(wav_path, "wb") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(4)
            wf.setframerate(CAPTURE_RATE)
            wf.writeframes(audio.tobytes())

        converted = "/tmp/jarvis-command-16k.wav"
        conv = subprocess.run(
            ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", wav_path,
             "-ac", "1", "-ar", str(STT_RATE), "-c:a", "pcm_s16le", converted],
            check=False,
        )
        if conv.returncode:
            print("COMMAND AUDIO CONVERSION FAILED", flush=True)
            return None

        # Keep the proven cloud STT path for transcription quality. Routing is local and
        # therefore does not add another network hop for common commands.
        code = """
from openai import OpenAI
client = OpenAI()
with open('/tmp/jarvis-command-16k.wav', 'rb') as f:
    result = client.audio.transcriptions.create(model='gpt-4o-mini-transcribe', file=f)
print(result.text.strip())
"""
        started = time.monotonic()
        result = subprocess.run(
            ["/home/ty/legopi-venv/bin/python", "-c", code],
            capture_output=True,
            text=True,
            timeout=20,
        )
        print(f"TIMING: transcription END ({time.monotonic() - started:.3f}s)", flush=True)
        if result.returncode:
            print("TRANSCRIPTION ERROR:", result.stderr.strip(), flush=True)
            return None
        text = normalize(result.stdout)
        if text:
            print("HEARD:", text, flush=True)
            return text
        return None

    def rearm(self) -> None:
        self._wait_for_audio_to_finish()
        self._wait_for_quiet()
        self.wake_model.reset()
        with sd.InputStream(
            device=AUDIO_DEVICE, channels=1, samplerate=CAPTURE_RATE,
            dtype="int16", blocksize=BLOCK_SIZE
        ) as stream:
            for _ in range(4):
                stream.read(BLOCK_SIZE)
        time.sleep(0.10)

    @staticmethod
    def _wait_for_audio_to_finish() -> None:
        while True:
            tts = subprocess.run(["pgrep", "-f", "elevenlabs-speak"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            aplay = subprocess.run(["pgrep", "-x", "aplay"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if tts.returncode != 0 and aplay.returncode != 0:
                return
            time.sleep(0.10)

    @staticmethod
    def _wait_for_quiet() -> None:
        quiet_needed = 0.60
        quiet_start: float | None = None
        with sd.InputStream(device=AUDIO_DEVICE, channels=1, samplerate=CAPTURE_RATE, dtype="int16", blocksize=BLOCK_SIZE) as stream:
            while True:
                audio, _ = stream.read(BLOCK_SIZE)
                samples = resample_to_16khz(audio)
                rms = float(np.sqrt(np.mean(samples.astype(np.float32) ** 2)))
                if rms < 450:
                    quiet_start = quiet_start or time.monotonic()
                    if time.monotonic() - quiet_start >= quiet_needed:
                        return
                else:
                    quiet_start = None
