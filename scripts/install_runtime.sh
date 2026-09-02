#!/bin/bash
set -euo pipefail
SRC="$(cd "$(dirname "$0")/.." && pwd)"
ROOT="${LEGOPI_HOME:-/home/ty}"
REPO="$ROOT/legopi"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP="$ROOT/legopi-backups/$STAMP"
PYTHON="$ROOT/legopi-venv/bin/python"
mkdir -p "$BACKUP"
sudo systemctl stop legopi-jarvis.service legopi-live.service 2>/dev/null || true
for f in jarvis-full.py jarvis-intent-router.py legopi-live-server-final.py elevenlabs-speak-final.py reboot-button.py; do [ -f "$ROOT/$f" ] && cp -a "$ROOT/$f" "$BACKUP/"; done
[ -d "$REPO" ] && cp -a "$REPO" "$BACKUP/legopi" || true
[ -d "$ROOT/legopi-data" ] && cp -a "$ROOT/legopi-data" "$BACKUP/legopi-data" || true
rm -rf "$REPO"; mkdir -p "$REPO"; cp -a "$SRC/." "$REPO/"
rm -f "$REPO/legopi-data/lego_inventory.db"
cp "$SRC/jarvis-full.py" "$ROOT/jarvis-full.py"
cp "$SRC/jarvis-intent-router.py" "$ROOT/jarvis-intent-router.py"
cp "$SRC/legopi-live-server-final.py" "$ROOT/legopi-live-server-final.py"
cp "$SRC/elevenlabs-speak-final.py" "$ROOT/elevenlabs-speak-final.py"
cp "$SRC/reboot-button.py" "$ROOT/reboot-button.py"
sudo install -m 755 "$SRC/bin/legopi-volume" /usr/local/bin/legopi-volume
sudo install -m 755 "$SRC/bin/legopi-ollama-warm" /usr/local/bin/legopi-ollama-warm
sudo install -m 644 "$SRC/systemd/legopi-live.service" /etc/systemd/system/legopi-live.service
sudo install -m 644 "$SRC/systemd/legopi-jarvis.service" /etc/systemd/system/legopi-jarvis.service
sudo install -m 644 "$SRC/systemd/legopi-reboot-button.service" /etc/systemd/system/legopi-reboot-button.service
sudo install -m 644 "$SRC/systemd/legopi-ollama-warm.service" /etc/systemd/system/legopi-ollama-warm.service
chmod +x "$ROOT"/{jarvis-full.py,jarvis-intent-router.py,legopi-live-server-final.py,elevenlabs-speak-final.py,reboot-button.py}
"$PYTHON" -m py_compile "$ROOT/jarvis-full.py" "$ROOT/jarvis-intent-router.py" "$ROOT/legopi-live-server-final.py" "$ROOT/elevenlabs-speak-final.py" "$ROOT/legopi/runtime/"*.py "$ROOT/legopi/demo/demo_database.py"
sudo systemctl daemon-reload
sudo systemctl enable legopi-live.service legopi-jarvis.service legopi-ollama-warm.service
echo "INSTALL COMPLETE"; echo "ROLLBACK BACKUP: $BACKUP"; echo "REAL INVENTORY WAS PRESERVED: $ROOT/legopi-data/lego_inventory.db"
