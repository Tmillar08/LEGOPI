import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from runtime.intent import fast_route

CASES = {
    "put me in demo mode": "DEMO_MODE_ON",
    "switch back to normal mode": "DEMO_MODE_OFF",
    "what mode are you in": "DEMO_STATUS",
    "reset the demonstration": "DEMO_RESET",
    "what can you do": "WHAT_CAN_YOU_DO",
    "what do you have this brick stored?": "LOOKUP_INVENTORY",
    "put this piece in my inventory": "ADD_INVENTORY",
    "what brick is this": "SCAN_BRICK",
    "what do you see": "GENERAL_VISION",
    "volume ten": "SET_VOLUME",
    "set volume to five": "SET_VOLUME",
    "start rebuilding set 42110": "START_REBUILD",
    "start rebuilding set four two one one zero": "START_REBUILD",
    "what set are we building": "GET_ACTIVE_SET",
}


def test_fast_routes():
    for text, action in CASES.items():
        result = fast_route(text)
        assert result is not None
        assert result.action == action, (text, result)


def test_spoken_set_number():
    assert fast_route("start rebuilding set four two one one zero").set_num == "42110"


def test_volume_levels():
    assert fast_route("set volume to five").level == 5
    assert fast_route("volume 10").level == 10
