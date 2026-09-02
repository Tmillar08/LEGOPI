import hashlib
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from demo import demo_database
from runtime import config


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def test_demo_reset_never_changes_real_inventory(monkeypatch):
    monkeypatch.setenv("LEGOPI_HOME", str(ROOT))
    before = sha(config.REAL_INVENTORY_DB)
    demo_database.reset_demo()
    assert sha(config.REAL_INVENTORY_DB) == before
    assert demo_database.get_mode() == "NORMAL"
