# GitHub Repository Setup

This is the sanitized LEGO Pi clean-stack source distribution.

Included: runtime code, compatibility launchers, Flask routes, Brickognize/OpenAI/ElevenLabs
integration hooks, voice/wake/STT orchestration, Normal/Demo isolation, rebuild logic,
Qwen/Ollama bounded fallback, systemd units, deployment scripts, tests, documentation, and
a public Rebrickable catalog snapshot.

Intentionally excluded: API keys/passwords/tokens, the live personal inventory database,
virtual environments, private backups, and the raw `inventory_parts.csv` export. The shipped
SQLite catalog contains the data required by the runtime and is under GitHub's 100 MB single-
file limit, although Git LFS is recommended for long-term database versioning.

```bash
git init
git add .
git commit -m "Initial LEGO Pi clean stack"
git branch -M main
git remote add origin <YOUR_GITHUB_REPOSITORY>
git push -u origin main
```
