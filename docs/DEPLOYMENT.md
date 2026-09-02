# LEGO Pi Clean Stack — Raspberry Pi Deployment

This document updates an existing LEGO Pi installation in place while preserving the real
inventory database. Run the commands in order and stop if a verification step fails.

## 1. Copy the returned stack to the Pi

From Windows PowerShell, assuming the archive is in Downloads:

```powershell
scp "$env:USERPROFILE\Downloads\legopi-clean-stack.tar.gz" ty@lego-pi.local:/home/ty/
```

SSH to the Pi:

```bash
ssh ty@lego-pi.local
```

## 2. Stop the two application services

```bash
sudo systemctl stop legopi-jarvis.service legopi-live.service
sudo systemctl reset-failed legopi-jarvis.service legopi-live.service
```

## 3. Create a complete rollback backup

```bash
STAMP=$(date +%Y%m%d-%H%M%S)
mkdir -p /home/ty/legopi-backups/$STAMP
cp -a /home/ty/jarvis-full.py /home/ty/jarvis-intent-router.py /home/ty/legopi-live-server-final.py /home/ty/elevenlabs-speak-final.py /home/ty/legopi /home/ty/legopi-data /home/ty/.config/legopi /home/ty/legopi-backups/$STAMP/
```

## 4. Extract the clean stack to a temporary directory

```bash
rm -rf /home/ty/legopi-clean-deploy
mkdir -p /home/ty/legopi-clean-deploy
tar -xzf /home/ty/legopi-clean-stack.tar.gz -C /home/ty/legopi-clean-deploy
```

## 5. Install the clean runtime

```bash
BACKUP=$(find /home/ty/legopi-backups -mindepth 1 -maxdepth 1 -type d | sort | tail -1)
LIVE_CATALOG=/home/ty/legopi/data/db/legopi.sqlite3
if [ -f "$LIVE_CATALOG" ]; then cp -a "$LIVE_CATALOG" "$BACKUP/live-legopi.sqlite3"; fi
rm -rf /home/ty/legopi
mkdir -p /home/ty/legopi
cp -a /home/ty/legopi-clean-deploy/legopi/. /home/ty/legopi
if [ -f "$BACKUP/live-legopi.sqlite3" ]; then cp -a "$BACKUP/live-legopi.sqlite3" /home/ty/legopi/data/db/legopi.sqlite3; fi
cp /home/ty/legopi-clean-deploy/jarvis-full.py /home/ty/jarvis-full.py
cp /home/ty/legopi-clean-deploy/jarvis-intent-router.py /home/ty/jarvis-intent-router.py
cp /home/ty/legopi-clean-deploy/legopi-live-server-final.py /home/ty/legopi-live-server-final.py
cp /home/ty/legopi-clean-deploy/elevenlabs-speak-final.py /home/ty/elevenlabs-speak-final.py
cp /home/ty/legopi-clean-deploy/reboot-button.py /home/ty/reboot-button.py
sudo install -m 755 /home/ty/legopi-clean-deploy/bin/legopi-volume /usr/local/bin/legopi-volume
sudo install -m 755 /home/ty/legopi-clean-deploy/bin/legopi-ollama-warm /usr/local/bin/legopi-ollama-warm
sudo install -m 644 /home/ty/legopi-clean-deploy/systemd/legopi-live.service /etc/systemd/system/legopi-live.service
sudo install -m 644 /home/ty/legopi-clean-deploy/systemd/legopi-jarvis.service /etc/systemd/system/legopi-jarvis.service
sudo install -m 644 /home/ty/legopi-clean-deploy/systemd/legopi-reboot-button.service /etc/systemd/system/legopi-reboot-button.service
sudo install -m 644 /home/ty/legopi-clean-deploy/systemd/legopi-ollama-warm.service /etc/systemd/system/legopi-ollama-warm.service
```

## 6. Protect secrets

The returned clean stack deliberately does not contain API keys. Keep the existing files:

```text
/home/ty/.config/legopi/openai.env
/home/ty/.config/legopi/elevenlabs.env
```

Verify permissions:

```bash
chmod 600 /home/ty/.config/legopi/openai.env /home/ty/.config/legopi/elevenlabs.env
```

## 7. Verify the real database was not replaced

```bash
ls -lh /home/ty/legopi-data/lego_inventory.db
sqlite3 /home/ty/legopi-data/lego_inventory.db "SELECT COUNT(*) FROM inventory;"
sqlite3 /home/ty/legopi-data/lego_inventory.db "SELECT rebrickable_part_num,color_name,quantity,location_id FROM inventory WHERE rebrickable_part_num='3039';"
```

The real database must still contain your existing 3039 test record and the rest of the
inventory before continuing.

## 8. Reset demo data once

```bash
cd /home/ty/legopi
/home/ty/legopi-venv/bin/python -c 'from demo.demo_database import reset_demo; reset_demo(); print("DEMO RESET OK")'
```

Verify:

```bash
cat /home/ty/legopi/demo/demo_state.json
/home/ty/legopi-venv/bin/python /home/ty/legopi/demo/demo_database.py
```

Expected initial mode:

```text
MODE: NORMAL
```

## 9. Verify the local router without speaking

```bash
/home/ty/legopi-venv/bin/python /home/ty/jarvis-intent-router.py "put me in demo mode"
/home/ty/legopi-venv/bin/python /home/ty/jarvis-intent-router.py "what do you have this brick stored?"
/home/ty/legopi-venv/bin/python /home/ty/jarvis-intent-router.py "switch back to normal mode"
/home/ty/legopi-venv/bin/python /home/ty/jarvis-intent-router.py "what can you do"
/home/ty/legopi-venv/bin/python /home/ty/jarvis-intent-router.py "reset the demonstration"
```

These five commands should return immediately from the fast local router. They should not
need Ollama.

## 10. Verify Qwen fallback separately

First confirm Ollama:

```bash
systemctl is-active ollama
curl -s --max-time 5 http://127.0.0.1:11434/
ollama list
```

Then test a deliberately indirect request:

```bash
time /home/ty/legopi-venv/bin/python /home/ty/jarvis-intent-router.py "could you show me where this part is kept"
```

If Qwen is cold, this may take several seconds. That delay is isolated to the fallback path;
normal commands do not wait for it.

## 11. Verify Python syntax

```bash
/home/ty/legopi-venv/bin/python -m py_compile \
  /home/ty/jarvis-full.py \
  /home/ty/jarvis-intent-router.py \
  /home/ty/legopi-live-server-final.py \
  /home/ty/elevenlabs-speak-final.py \
  /home/ty/legopi/runtime/*.py \
  /home/ty/legopi/demo/demo_database.py
```

## 12. Reload systemd and start services

```bash
sudo systemctl daemon-reload
sudo systemctl enable legopi-live.service legopi-jarvis.service
sudo systemctl enable legopi-ollama-warm.service
sudo systemctl start legopi-live.service
sleep 8
sudo systemctl start legopi-jarvis.service
```

## 13. Verify live server

```bash
systemctl is-active legopi-live.service
ss -ltnp | grep ':5000'
curl -s http://127.0.0.1:5000/health
curl -s http://127.0.0.1:5000/mode
```

Expected:

```text
status=ok
mode=NORMAL
```

## 14. Verify the camera and inventory path

```bash
curl -X POST --max-time 45 http://127.0.0.1:5000/inventory
```

Hold a known test piece under the camera first. For the current verified test piece, use
LEGO part `3039` rather than assuming the real inventory contains a red 3001.

## 15. Verify voice commands

Say:

1. `Hey Jarvis` → `Yes?`
2. `What can you do?`
3. `Volume three`
4. `Volume ten`
5. `Put me in demo mode`
6. `Are you in demo mode?`
7. `Switch back to normal mode`
8. `Reset the demonstration`
9. `Add this brick`
10. `Where do I have this brick?`

## 16. Verify demo isolation

Put Jarvis in Demo Mode, add/lookup a demo piece, then switch back to Normal Mode.
Compare counts:

```bash
sqlite3 /home/ty/legopi-data/lego_inventory.db "SELECT COUNT(*) FROM inventory;"
sqlite3 /home/ty/legopi/demo/demo_inventory.db "SELECT COUNT(*) FROM inventory;"
```

Demo operations must change only the demo database.

## Rollback

If a verification step fails:

```bash
sudo systemctl stop legopi-jarvis.service legopi-live.service
```

Restore the files from the timestamped directory created in step 3, then:

```bash
sudo systemctl daemon-reload
sudo systemctl start legopi-live.service
sudo systemctl start legopi-jarvis.service
```

Do not restore the real inventory database unless the failure specifically damaged it. The
clean stack is designed not to overwrite it.
