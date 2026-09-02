from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def test_required_routes_present():
    text = (ROOT / "runtime/live_server.py").read_text()
    required = [
        "/", "/video", "/vision", "/scan", "/inventory", "/inventory/add",
        "/color-test-frame", "/color-test", "/color-sample", "/camera-metadata",
    ]
    for route in required:
        assert re.search(rf'@app\.route\("{re.escape(route)}"', text)
