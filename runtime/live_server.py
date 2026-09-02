from __future__ import annotations

import base64
import os
import sqlite3
import subprocess
import threading
import time
from typing import Any

import cv2
import numpy as np
import requests
from flask import Flask, Response, jsonify, send_file
from openai import OpenAI
from picamera2 import Picamera2

from .config import CAMERA_FPS, CAMERA_HEIGHT, CAMERA_WIDTH, LIVE_HOST, LIVE_PORT, TTS_SCRIPT
from .db_paths import inventory_db_path
from .mode import mode
from .tts import load_env_file
from .config import ELEVENLABS_ENV

app = Flask(__name__)
client = OpenAI()

picam2 = Picamera2()
config = picam2.create_video_configuration(
    main={"size": (CAMERA_WIDTH, CAMERA_HEIGHT), "format": "RGB888"},
    controls={"FrameRate": CAMERA_FPS, "AfMode": 2},
)
picam2.configure(config)
picam2.start()
time.sleep(1)
try:
    picam2.set_controls({
        "AfMode": 2,
        "AfSpeed": 1,
        "AwbEnable": False,
        "ColourGains": (1.5474, 2.3381),
    })
except Exception:
    # Some camera/tuning combinations do not expose every focus control. The stream still works.
    pass
time.sleep(1)

frame_lock = threading.Lock()
latest_frame: np.ndarray | None = None

COLOR_REFERENCES = {
    "red": ("sat", (171.0, 143.0, 187.0)),
    "orange": ("sat", (17.0, 255.0, 235.0)),
    "yellow": ("sat", (28.0, 231.0, 225.0)),
    "green": ("sat", (78.5, 216.0, 163.0)),
    "blue": ("sat", (105.0, 254.0, 208.0)),
    "tan": ("full", (45.0, 20.0, 218.0)),
    "black": ("full", (102.0, 86.0, 79.0)),
    "dark gray": ("full", (97.5, 64.0, 143.0)),
    "light gray": ("full", (97.5, 33.0, 185.0)),
    "white": ("full", (63.0, 7.0, 248.0)),
}


def _hsv_distance(sample, reference):
    h, s, v = sample
    rh, rs, rv = reference
    hue_delta = min(abs(float(h) - float(rh)), 180.0 - abs(float(h) - float(rh)))
    dh = hue_delta / 90.0
    ds = (float(s) - float(rs)) / 255.0
    dv = (float(v) - float(rv)) / 255.0
    return (dh * 2.5) ** 2 + (ds * 1.4) ** 2 + (dv * 1.2) ** 2


def classify_lego_color(crop):
    if crop is None or crop.size == 0:
        return "unknown"
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    full_hsv = np.median(hsv.reshape(-1, 3), axis=0)
    mask = (hsv[:, :, 1] >= 50) & (hsv[:, :, 2] >= 40) & (hsv[:, :, 2] <= 250)
    saturated = hsv[mask]
    sat_hsv = np.median(saturated, axis=0) if len(saturated) else full_hsv
    full_h, full_s, full_v = map(float, full_hsv)
    if full_v < 110:
        return "black"
    if full_s < 18 and full_v > 225:
        return "white"
    samples = {"full": full_hsv, "sat": sat_hsv}
    scores = {name: _hsv_distance(samples[mode], ref) for name, (mode, ref) in COLOR_REFERENCES.items()}
    return min(scores, key=scores.get)


def _capture_loop():
    global latest_frame
    while True:
        try:
            frame = picam2.capture_array()
            with frame_lock:
                latest_frame = frame.copy()
        except Exception as exc:
            print(f"CAMERA CAPTURE ERROR: {exc}", flush=True)
            time.sleep(0.25)
            continue
        time.sleep(0.05)


threading.Thread(target=_capture_loop, daemon=True, name="camera-capture").start()


def _frame_copy():
    with frame_lock:
        return None if latest_frame is None else latest_frame.copy()


def _encode_frame(frame):
    ok, jpg = cv2.imencode(".jpg", frame)
    if not ok:
        raise RuntimeError("JPEG encode failed")
    return jpg.tobytes()


def _speak_async(text: str):
    env = load_env_file(ELEVENLABS_ENV)
    subprocess.Popen([
        "/home/ty/legopi-venv/bin/python", str(TTS_SCRIPT), str(text)
    ], env=env)


def _brickognize(frame):
    jpg = _encode_frame(frame)
    response = requests.post(
        "https://api.brickognize.com/predict/parts/",
        files={"query_image": ("lego.jpg", jpg, "image/jpeg")},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    items = data.get("items", [])
    color = "unknown"
    bbox = data.get("bounding_box")
    if bbox:
        h, w = frame.shape[:2]
        bw = bbox.get("image_width") or w
        bh = bbox.get("image_height") or h
        sx, sy = w / bw, h / bh
        x1 = max(0, int(bbox["left"] * sx))
        y1 = max(0, int(bbox["upper"] * sy))
        x2 = min(w, int(bbox["right"] * sx))
        y2 = min(h, int(bbox["lower"] * sy))
        color = classify_lego_color(frame[y1:y2, x1:x2])
    return data, items, color


def _inventory_lookup(part_num: str, color: str):
    db = inventory_db_path()
    con = sqlite3.connect(db, timeout=10)
    con.row_factory = sqlite3.Row
    try:
        exact = []
        if color != "unknown":
            exact = con.execute(
                """
                SELECT i.part_name,i.color_name,i.quantity,i.location_id,l.spoken_location
                FROM inventory i JOIN locations l ON l.location_id=i.location_id
                WHERE lower(i.rebrickable_part_num)=lower(?) AND lower(i.color_name)=lower(?)
                ORDER BY i.quantity DESC
                """, (part_num, color)
            ).fetchall()
        if exact:
            return "exact", exact[0]
        rows = con.execute(
            """
            SELECT i.part_name,i.color_name,i.quantity,i.location_id,l.spoken_location
            FROM inventory i JOIN locations l ON l.location_id=i.location_id
            WHERE lower(i.rebrickable_part_num)=lower(?) ORDER BY i.quantity DESC
            """, (part_num,)
        ).fetchall()
        return "part", rows[0] if rows else None
    finally:
        con.close()


def _inventory_add(part_num: str, part_name: str, color: str):
    db = inventory_db_path()
    con = sqlite3.connect(db, timeout=10)
    con.row_factory = sqlite3.Row
    try:
        exact = con.execute(
            """
            SELECT i.inventory_id,i.quantity,i.location_id,l.spoken_location
            FROM inventory i JOIN locations l ON l.location_id=i.location_id
            WHERE lower(i.rebrickable_part_num)=lower(?) AND lower(i.color_name)=lower(?)
            ORDER BY i.quantity DESC LIMIT 1
            """, (part_num, color)
        ).fetchone()
        if exact:
            new_qty = int(exact["quantity"]) + 1
            con.execute("UPDATE inventory SET quantity=?,last_verified=datetime('now') WHERE inventory_id=?", (new_qty, exact["inventory_id"]))
            location_id, spoken, action = exact["location_id"], exact["spoken_location"] or exact["location_id"], "ADD_EXISTING"
        else:
            same_part = con.execute(
                """
                SELECT i.location_id,l.spoken_location FROM inventory i JOIN locations l ON l.location_id=i.location_id
                WHERE lower(i.rebrickable_part_num)=lower(?) ORDER BY i.quantity DESC LIMIT 1
                """, (part_num,)
            ).fetchone()
            if same_part:
                location_id, spoken, action = same_part["location_id"], same_part["spoken_location"] or same_part["location_id"], "ADD_NEW_COLOR"
            else:
                location = con.execute(
                    """
                    SELECT l.location_id,l.spoken_location FROM locations l
                    WHERE NOT EXISTS (SELECT 1 FROM inventory i WHERE i.location_id=l.location_id)
                    ORDER BY l.unit,l.drawer,l.y_row,l.x_column LIMIT 1
                    """
                ).fetchone()
                if not location:
                    raise RuntimeError("no_unused_locations")
                location_id, spoken, action = location["location_id"], location["spoken_location"] or location["location_id"], "ADD_NEW_PART"
            con.execute(
                """
                INSERT INTO inventory(rebrickable_part_num,part_name,color_id,color_name,quantity,location_id,rebrickable_set_num,last_verified,notes)
                VALUES(?,?,NULL,?,1,?,NULL,datetime('now'),'Added by Jarvis scan')
                """, (part_num, part_name, color, location_id)
            )
            new_qty = 1
        con.execute(
            """
            INSERT INTO inventory_history(timestamp,action,rebrickable_part_num,color_name,quantity_change,old_location_id,new_location_id,source,spoken_command,notes)
            VALUES(datetime('now'),?,?,?,1,NULL,?,'voice','add this brick',?)
            """, (action, part_num, color, location_id, part_name)
        )
        con.commit()
        return {"action": action, "quantity": new_qty, "location_id": location_id, "spoken_location": spoken}
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


@app.route("/")
def index():
    return """
    <html><body style="margin:0;background:#111;color:white;font-family:sans-serif;">
      <img src="/video" style="width:100%;height:auto;">
      <div style="padding:12px;"><button onclick="scan()">Scan LEGO</button><p id="result"></p></div>
      <script>async function scan(){document.getElementById('result').innerText='Scanning...';const r=await fetch('/scan',{method:'POST'});const d=await r.json();document.getElementById('result').innerText=d.result||d.error||'Error';}</script>
    </body></html>
    """


@app.route("/health")
def health():
    return jsonify({"status": "ok", "mode": mode(), "camera_frame": _frame_copy() is not None})


@app.route("/mode")
def mode_route():
    return jsonify({"mode": mode(), "database": str(inventory_db_path())})


@app.route("/video")
def video():
    def stream():
        while True:
            frame = _frame_copy()
            if frame is None:
                time.sleep(0.05)
                continue
            try:
                jpg = _encode_frame(frame)
            except RuntimeError:
                continue
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpg + b"\r\n"
            time.sleep(0.08)
    return Response(stream(), mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/vision", methods=["POST"])
def vision():
    frame = _frame_copy()
    if frame is None:
        return jsonify({"error": "No frame available"}), 503
    b64 = base64.b64encode(_encode_frame(frame)).decode()
    response = client.responses.create(
        model="gpt-5.4-mini",
        input=[{"role":"user", "content":[
            {"type":"input_text", "text":"Briefly describe what you see in this camera image."},
            {"type":"input_image", "image_url":f"data:image/jpeg;base64,{b64}"},
        ]}],
    )
    text = response.output_text.strip()
    _speak_async(text)
    return jsonify({"result": text})


@app.route("/scan", methods=["POST"])
def scan():
    frame = _frame_copy()
    if frame is None:
        return jsonify({"result":"No camera frame available."}), 503
    start = time.time()
    try:
        data, items, color = _brickognize(frame)
    except requests.RequestException as exc:
        return jsonify({"result":"Brick identification service failed.","error":str(exc)}), 502
    if not items:
        text = "No LEGO part identified"
    else:
        best = items[0]
        text = f'That one is a {best["id"]} - {color} - {best["name"]}'
    _speak_async(text.replace(" - ", ", "))
    return jsonify({"result":text, "seconds":round(time.time()-start,2)})


@app.route("/inventory", methods=["POST"])
def inventory_lookup_route():
    frame = _frame_copy()
    if frame is None:
        return jsonify({"result":"No camera frame available."}), 503
    try:
        data, items, color = _brickognize(frame)
    except requests.RequestException as exc:
        return jsonify({"result":"Brick identification service failed.","error":str(exc)}), 502
    if not items:
        text = "I couldn't identify that brick."
        _speak_async(text)
        return jsonify({"result":text}), 404
    best = items[0]
    part_num, part_name = str(best["id"]), best["name"]
    kind, row = _inventory_lookup(part_num, color)
    if kind == "exact" and row:
        location = row["spoken_location"] or row["location_id"]
        text = f"That is part {part_num}, {color}. You have {row['quantity']} of them in {location}."
    elif kind == "part" and row:
        location = row["spoken_location"] or row["location_id"]
        text = f"That is part {part_num}, {color}. I don't have that color recorded yet. I do have {row['quantity']} {row['color_name']} ones in {location}."
    else:
        text = f"I identified part {part_num}, {color}, {part_name}, but I don't have a storage location recorded for it yet."
    _speak_async(text)
    return jsonify({"result":text,"part_num":part_num,"part_name":part_name,"detected_color":color})


@app.route("/inventory/add", methods=["POST"])
def inventory_add_route():
    frame = _frame_copy()
    if frame is None:
        return jsonify({"result":"No camera frame available."}), 503
    try:
        data, items, color = _brickognize(frame)
    except requests.RequestException as exc:
        return jsonify({"result":"Brick identification service failed.","error":str(exc)}), 502
    if not items:
        text = "I couldn't identify that brick, so I didn't add anything."
        _speak_async(text)
        return jsonify({"result":text}), 404
    best = items[0]
    part_num, part_name = str(best["id"]), best["name"]
    if color == "unknown":
        text = f"I identified part {part_num}, {part_name}, but I couldn't determine the color, so I didn't add it."
        _speak_async(text)
        return jsonify({"result":text,"part_num":part_num,"part_name":part_name,"detected_color":color}), 422
    try:
        result = _inventory_add(part_num, part_name, color)
    except RuntimeError as exc:
        if str(exc) == "no_unused_locations":
            text = f"I identified a {color} {part_num}, {part_name}, but there are no unused storage locations available."
            _speak_async(text)
            return jsonify({"result":text}), 409
        raise
    text = f"That's a {color} {part_num}, {part_name}. I added one to inventory. You now have {result['quantity']}. Put it in {result['spoken_location']}." if result["action"] == "ADD_EXISTING" else f"That's a {color} {part_num}, {part_name}. I added it to inventory. Put it in {result['spoken_location']}."
    _speak_async(text)
    return jsonify({"result":text,"part_num":part_num,"part_name":part_name,"detected_color":color,**result})


@app.route("/color-test-frame")
def color_test_frame():
    frame = _frame_copy()
    if frame is None:
        return jsonify({"error":"No frame available"}), 503
    path = "/tmp/legopi-color-test-frame.jpg"
    cv2.imwrite(path, frame)
    return send_file(path, mimetype="image/jpeg")


@app.route("/color-test")
def color_test():
    return """
    <html><body style="margin:0;background:#111;color:white;font-family:sans-serif;">
    <div style="position:relative;width:100%;max-width:1280px;margin:auto;">
      <img src="/video" style="width:100%;height:auto;display:block;">
      <div style="position:absolute;left:40%;top:40%;width:20%;height:20%;border:4px solid red;box-sizing:border-box;pointer-events:none;"></div>
      <div style="position:absolute;left:50%;top:50%;width:20px;height:2px;background:red;transform:translate(-50%,-50%);pointer-events:none;"></div>
      <div style="position:absolute;left:50%;top:50%;width:2px;height:20px;background:red;transform:translate(-50%,-50%);pointer-events:none;"></div>
    </div><p style="padding:12px;text-align:center;">Center one LEGO brick inside the red box and fill as much of the box as possible.</p>
    </body></html>
    """


@app.route("/color-sample")
def color_sample():
    frame = _frame_copy()
    if frame is None:
        return jsonify({"error":"No frame available"}), 503
    h, w = frame.shape[:2]
    crop = frame[int(h*.45):int(h*.55), int(w*.45):int(w*.55)]
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    full_b, full_g, full_r = np.median(crop.reshape(-1,3),axis=0)
    full_h, full_s, full_v = np.median(hsv.reshape(-1,3),axis=0)
    mask = (hsv[:,:,1]>=50)&(hsv[:,:,2]>=40)&(hsv[:,:,2]<=250)
    pixels, hsv_pixels = crop[mask], hsv[mask]
    result: dict[str, Any] = {"full_rgb":{"r":round(float(full_r),1),"g":round(float(full_g),1),"b":round(float(full_b),1)},"full_hsv":{"h":round(float(full_h),1),"s":round(float(full_s),1),"v":round(float(full_v),1)},"saturated_coverage_percent":round(100*len(pixels)/(crop.shape[0]*crop.shape[1]),1)}
    if len(pixels):
        b,g,r=np.median(pixels,axis=0); hh,ss,vv=np.median(hsv_pixels,axis=0)
        result["saturated_rgb"]={"r":round(float(r),1),"g":round(float(g),1),"b":round(float(b),1)}
        result["saturated_hsv"]={"h":round(float(hh),1),"s":round(float(ss),1),"v":round(float(vv),1)}
    return jsonify(result)


@app.route("/camera-metadata")
def camera_metadata():
    m = picam2.capture_metadata()
    gains = m.get("ColourGains")
    return jsonify({"colour_gains":list(gains) if gains else None,"colour_temperature":m.get("ColourTemperature"),"exposure_time":m.get("ExposureTime"),"analogue_gain":m.get("AnalogueGain")})


if __name__ == "__main__":
    app.run(host=LIVE_HOST, port=LIVE_PORT, threaded=True)
