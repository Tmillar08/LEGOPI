from __future__ import annotations

import subprocess

from .config import CAPABILITIES_RESPONSE
from .intent import route
from .mode import mode, set_demo
from .tts import speak
from .volume import set_volume

def start_rebuild(set_num: str | None, set_name: str | None) -> None:
    from .rebuild import resolve_set, start_session
    if not set_num and set_name:
        set_num = resolve_set(set_name)
    if set_num:
        ok, text = start_session(str(set_num) if "-" in str(set_num) else f"{set_num}-1")
        print(f"ACTIVE REBUILD: {text}", flush=True)
        speak(text)
    else:
        speak("I understood that you want to start a rebuild, but I could not identify one owned set.")

def dispatch(text: str) -> None:
    t = text.strip().lower().rstrip(".!?,")
    fast = route(t)
    print(f"INTENT: action={fast.action} source={fast.source}", flush=True)
    action = fast.action

    if action == "DEMO_MODE_ON":
        set_demo(True)
        print("ACTION: DEMO_MODE_ON", flush=True)
        speak("Demo Mode is now active. I will use the demonstration inventory and will not modify your real inventory.")
        return
    if action == "DEMO_MODE_OFF":
        set_demo(False)
        print("ACTION: DEMO_MODE_OFF", flush=True)
        speak("Demo Mode is now off. I am back to your normal inventory.")
        return
    if action == "DEMO_STATUS":
        m = mode()
        print(f"ACTION: MODE_STATUS ({m})", flush=True)
        speak("Yes. Demo Mode is active. I am using the demonstration inventory." if m == "DEMO" else "No. Demo Mode is off. I am using your normal inventory.")
        return
    if action == "DEMO_RESET":
        from demo.demo_database import reset_demo
        reset_demo()
        print("ACTION: DEMO_RESET", flush=True)
        speak("The demo has been reset. The demonstration inventory is back to its starting state.")
        return
    if action == "WHAT_CAN_YOU_DO":
        print("ACTION: CAPABILITIES", flush=True)
        speak(CAPABILITIES_RESPONSE)
        return
    if action == "SET_VOLUME":
        level = fast.level
        if level is not None and set_volume(level):
            print(f"ACTION: SET_VOLUME {level}", flush=True)
            speak(f"Volume set to {level}.")
        else:
            speak("I couldn't change the volume.")
        return
    if action == "SCAN_BRICK":
        print("ACTION: BRICKOGNIZE_SCAN", flush=True)
        _post("/scan")
        return
    if action == "ADD_INVENTORY":
        print("ACTION: INVENTORY_ADD", flush=True)
        _post("/inventory/add")
        return
    if action == "LOOKUP_INVENTORY":
        print("ACTION: INVENTORY_LOOKUP", flush=True)
        _post("/inventory")
        return
    if action == "GENERAL_VISION":
        print("ACTION: GENERAL_VISION", flush=True)
        _post("/vision")
        return
    if action == "START_REBUILD":
        print("ACTION: START_REBUILD", flush=True)
        start_rebuild(fast.set_num, fast.set_name)
        return
    if action == "GET_ACTIVE_SET":
        from .rebuild import active_set
        name = active_set()
        speak(f"The active rebuild set is {name}." if name else "There is no active rebuild set.")
        return
    if action == "CHECK_VISIBLE_PIECES":
        speak("I understand that you want me to check the visible pieces against the active set. Multi piece recognition is the next vision function we are adding.")
        return
    if action == "MARK_FOUND":
        speak("I understand that you want those pieces marked as found, but I will not change the build inventory until the multi piece scanner is connected.")
        return
    if action == "SYNC_REBRICKABLE":
        speak("I understand the Rebrickable sync request. For now, use the Rebrickable sync button.")
        return

    print(f"ACTION: UNKNOWN for transcript: {t}", flush=True)
    speak("I heard you, but I am not sure what you want me to do.")


def _post(path: str) -> None:
    result = subprocess.run(["curl", "-s", "--max-time", "35", "-X", "POST", f"http://127.0.0.1:5000{path}"], capture_output=True, text=True, check=False)
    if result.stdout:
        print(result.stdout.strip(), flush=True)
