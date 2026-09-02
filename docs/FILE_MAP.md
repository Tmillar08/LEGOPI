# Clean Stack File Map

| File | Purpose |
|---|---|
| `jarvis-full.py` | Bootable voice loop compatibility launcher |
| `jarvis-intent-router.py` | CLI testable local intent router |
| `legopi-live-server-final.py` | Bootable Flask/camera compatibility launcher |
| `elevenlabs-speak-final.py` | ElevenLabs TTS playback |
| `reboot-button.py` | Physical reboot button service |
| `runtime/config.py` | All runtime paths/settings |
| `runtime/intent.py` | Fast command matching + Qwen fallback |
| `runtime/jarvis.py` | Action dispatcher |
| `runtime/voice.py` | Wake word, command capture, STT, re-arm logic |
| `runtime/live_server.py` | Camera, vision, Brickognize, color and inventory routes |
| `runtime/inventory.py` | Inventory DB operations |
| `runtime/rebuild.py` | Rebuild/owned-set DB operations |
| `runtime/mode.py` | Normal/Demo state selector |
| `runtime/db_paths.py` | Dynamic DB selection |
| `runtime/tts.py` | TTS environment/process helper |
| `runtime/volume.py` | Volume command parsing/control |
| `demo/demo_database.py` | Demo seed/reset and database isolation |
| `demo/demo_inventory.db` | Demo physical inventory |
| `demo/legopi_demo.sqlite3` | Demo rebuild/catalog database |
| `systemd/*.service` | Service definitions |
| `bin/legopi-volume` | ALSA volume control |
| `bin/legopi-ollama-warm` | Optional Qwen warm-up |
| `scripts/install_runtime.sh` | Automated Pi deployment/backup |
| `docs/DEPLOYMENT.md` | Manual deployment and rollback |
| `docs/ARCHITECTURE.md` | Runtime architecture |
| `docs/COMMANDS.md` | Voice command reference |
| `docs/REBUILD_AUDIT.md` | Findings and rebuild decisions |
| `tests/` | Offline unit/syntax/route/isolation tests |
