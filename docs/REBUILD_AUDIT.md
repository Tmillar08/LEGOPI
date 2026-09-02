# Rebuild Audit

## Problems found in the supplied stack

1. `jarvis-full.py` imported `dude_personality`, but that module was not present in the
   supplied archive.
2. The live server imported `demo.demo_database` from a top-level script launched with
   `/home/ty` as its working directory. That produced `ModuleNotFoundError: No module named 'demo'`.
3. The intent router had already been changed to Ollama/Qwen, but every non-fast command
   could wait on a cold 1.5B CPU model. The supplied Pi measurements showed direct Ollama
   calls taking 15–35 seconds when cold or stalled.
4. Demo mode had duplicated implementations in `jarvis-full.py`: one block directly edited
   the JSON state and a second block used `demo_database.py`.
5. Inventory DB paths were duplicated as hard-coded strings.
6. Rebuild operations used a different SQLite database from the inventory selector, so Demo
   Mode did not fully isolate build-session writes.
7. The original ElevenLabs script performed an unnecessary first ffmpeg conversion before
   doing the real playback conversion.
8. The original live server repeated Brickognize, color extraction, and database plumbing
   across multiple routes.
9. The old repository contained a second, largely unused architecture under `src/legopi`
   whose assumptions no longer matched the proven August 29 runtime.
10. The archive contained credentials/configuration files. They are excluded from the clean
    returned stack.

## Rebuild decisions

- Keep the proven 48 kHz microphone / openWakeWord / OpenAI transcription path.
- Keep the calibrated HSV color classifier unchanged in substance.
- Keep Brickognize for visual part identification.
- Keep OpenAI vision for general camera description.
- Keep ElevenLabs for speech output.
- Keep the existing HTTP route surface.
- Keep all previously defined command actions.
- Make the local rule router the first decision layer.
- Keep Qwen 1.5B as a bounded fallback for commands that the rule router cannot classify.
- Centralize path and mode selection.
- Isolate demo inventory and demo rebuild databases from real databases.
- Make demo state writes atomic.
- Add a clean deployment and rollback procedure.
