import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_python_syntax():
    files = list((ROOT / "runtime").glob("*.py")) + list((ROOT / "demo").glob("*.py")) + [
        ROOT / "jarvis-full.py",
        ROOT / "jarvis-intent-router.py",
        ROOT / "legopi-live-server-final.py",
        ROOT / "elevenlabs-speak-final.py",
    ]
    for path in files:
        py_compile.compile(str(path), doraise=True)
