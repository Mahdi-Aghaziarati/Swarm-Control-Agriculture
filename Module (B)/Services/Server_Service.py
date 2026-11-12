#!/usr/bin/env python3
import json, math, socket, threading, time
import rospy
from technic import srv
from std_srvs.srv import Trigger
from led_msgs.srv import SetLEDs
from led_msgs.msg import LEDState, LEDStateArray

HOST, PORT = "0.0.0.0", 3000
FRAME = "aruco_map"
X_LIM, Y_LIM = 3.0, 1.5
Z_MIN, Z_MAX = 0.5, 3.0
SPEED_MAX = 1.0
LAND_SETTLE_S = 8.0
ARRIVE_TOL_M = 0.30
SAG_Z_M = 0.40
FLOOR_Z_M = 0.35
TAKEOFF_TOL_M = 0.20
DEDUP_M = 0.5
TELEM_TIMEOUT_S = 1.0

rospy.init_node("quad_simple")
navigate = rospy.ServiceProxy("navigate", srv.Navigate)
get_telemetry = rospy.ServiceProxy("get_telemetry", srv.GetTelemetry)
land_srv = rospy.ServiceProxy("land", Trigger)
set_leds = rospy.ServiceProxy("led/set_leds", SetLEDs)

emergency = threading.Event()
busy = threading.Lock()
airborne = False
last = [0.0, 0.0, 0.0]
conn = None
send_lock = threading.Lock()
user_vars = {"a": 0.0, "b": 0.0}
led_color = [0, 0, 0]
targets = []
targets_lock = threading.Lock()


def send(obj):
    c = conn
    if c is None:
        return
    try:
        with send_lock:
            c.sendall((json.dumps(obj) + "\n").encode())
    except Exception:
        pass


def log(*a):
    print("[quad]", *a, flush=True)


def info(m, what, ok, msg, **kw):
    d = {"type": "info", "id": m.get("id"), "what": what, "ok": ok, "msg": msg}
    d.update(kw)
    send(d)


def detect_led_count():
    try:
        msg = rospy.wait_for_message("led/state", LEDStateArray, timeout=2.0)
        return max(1, len(msg.leds))
    except Exception:
        return 1


LED_COUNT = detect_led_count()


def set_led(r, g, b, index=None):
    ids = range(LED_COUNT) if index is None else [index]
    try:
        res = set_leds([LEDState(index=i, r=r, g=g, b=b) for i in ids])
    except Exception as e:
        log("led error", e)
        return False, "led error: %s" % e
    ok = bool(getattr(res, "success", True))
    if ok and index is None:
        led_color[:] = [r, g, b]
    return ok, "ok" if ok else str(getattr(res, "message", "failed"))


def set_vars(m):
    for k in ("a", "b"):
        if k in m:
            user_vars[k] = float(m[k])


def check_extras(m):
    if "led" in m:
        c = m["led"]
        if not isinstance(c, (list, tuple)) or len(c) != 3 or not all(ok_num(v, 0, 255) for v in c):
            return "bad led"
    for k in ("a", "b"):
        if k in m and not ok_num(m[k], -1e9, 1e9):
            return "bad var %s" % k
    return None


def apply_extras(m):
    if "led" in m:
        set_led(int(m["led"][0]), int(m["led"][1]), int(m["led"][2]))
    set_vars(m)


def add_target(x, y, z=None, label=""):
    if not (ok_num(x, -1e6, 1e6) and ok_num(y, -1e6, 1e6)):
        return False
    x, y = round(float(x), 3), round(float(y), 3)
    z = round(float(z), 3) if ok_num(z, -1e6, 1e6) else None
    label = str(label)[:32]
    with targets_lock:
        for p in targets:
            if p["label"] == label and math.dist((p["x"], p["y"]), (x, y)) < DEDUP_M:
                return False
        p = {"x": x, "y": y, "z": z, "label": label, "t": round(time.time(), 1)}
        targets.append(p)
    send({"type": "targets", "points": [p]})
    return True


def report_detection(x, y, z, label="fire"):
    return add_target(x, y, z, label)


def telem(timeout=TELEM_TIMEOUT_S):
    box = {}
    def run():
        try:
            box["v"] = get_telemetry(frame_id=FRAME)
        except Exception:
            pass
    t = threading.Thread(target=run, daemon=True)
    t.start()
    t.join(timeout)
    return box.get("v")


def valid(t):
    if t is None:
        return False
    try:
        return (t.x == t.x) and (t.y == t.y) and (t.z == t.z)
    except Exception:
        return False


def sleep_abortable(sec):
    end = time.time() + sec
    while time.time() < end:
        if emergency.is_set() or rospy.is_shutdown():
            return False
        time.sleep(0.1)
    return True


def do_land_now():
    global airborne
    for i in range(5):
        try:
            r = land_srv()
            log("land ->", r.success, r.message)
            if r.success:
                break
        except Exception as e:
            log("land error", e)
        time.sleep(0.3)
    airborne = False


def ok_num(v, lo, hi):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and lo <= v <= hi


def check_xyz(m):
    if not ok_num(m.get("x"), -X_LIM, X_LIM): return "x out of range"
    if not ok_num(m.get("y"), -Y_LIM, Y_LIM): return "y out of range"
    if not ok_num(m.get("z"), Z_MIN, Z_MAX): return "z out of range"
    return None


def hold(sec):
    if sec and sec > 0:
        log("hold %.1fs" % sec)
        return sleep_abortable(sec)
    return True


def wait_takeoff(z, limit=20.0):
    t0 = time.time()
    while time.time() - t0 < limit:
        if emergency.is_set() or rospy.is_shutdown():
            return False, "emergency"
        t = telem()
        if valid(t) and t.z >= z - TAKEOFF_TOL_M:
            log("takeoff done z=%.2f in %.1fs" % (t.z, time.time() - t0))
            return True, "ok"
        time.sleep(0.2)
    log("takeoff altitude timeout (z target %.2f)" % z)
    return True, "takeoff timeout"


def move(x, y, z, speed, wait_s=None):
    dist = math.dist(last, (x, y, z))
    limit = wait_s if wait_s else min(90.0, 8.0 + dist / (speed * 0.5))

    r = navigate(x=x, y=y, z=z, yaw=float("nan"), speed=speed,
                 frame_id=FRAME, auto_arm=False)
    log("navigate (%.2f,%.2f,%.2f) ok=%s limit=%.1fs" % (x, y, z, r.success, limit))
    if not r.success:
        return False, "navigate rejected: %s" % r.message

    last[:] = [x, y, z]
    t0 = time.time()
    last_fix = t0
    while time.time() - t0 < limit:
        if emergency.is_set() or rospy.is_shutdown():
            return False, "emergency"
        t = telem()
        if valid(t):
            if t.z < FLOOR_Z_M:
                log("on the ground during move (z=%.2f) -> aborting move" % t.z)
                return False, "landed unexpectedly (z=%.2f)" % t.z
            d = math.dist((t.x, t.y, t.z), (x, y, z))
            if d < ARRIVE_TOL_M and time.time() - t0 > 0.5:
                return True, "arrived d=%.2f" % d
            if t.z < z - SAG_Z_M and time.time() - last_fix > 2.0:
                log("altitude sag z=%.2f (target %.2f) -> re-sending" % (t.z, z))
                navigate(x=x, y=y, z=z, yaw=float("nan"), speed=speed,
                         frame_id=FRAME, auto_arm=False)
                last_fix = time.time()
        time.sleep(0.2)

    t = telem()
    pos = "(%.2f,%.2f,%.2f)" % (t.x, t.y, t.z) if valid(t) else "unknown"
    log("arrival timeout at", pos)
    return True, "timeout, pos=%s" % pos


def execute(m):
    global airborne
    cmd, cid = m["cmd"], m.get("id")
    try:
        if cmd == "takeoff":
            z = m.get("z", 2.0)
            if not ok_num(z, Z_MIN, Z_MAX):
                return send({"type": "done", "id": cid, "ok": False, "msg": "bad z"})
            bad = check_extras(m)
            if bad:
                return send({"type": "done", "id": cid, "ok": False, "msg": bad})
            apply_extras(m)
            airborne = True
            navigate(x=float("nan"), y=float("nan"), z=z, yaw=float("nan"),
                     speed=0.5, frame_id="body", auto_arm=True)
            last[:] = [m.get("x", 0.0), m.get("y", 0.0), z]
            ok, tmsg = wait_takeoff(z)
            if not ok:
                return send({"type": "done", "id": cid, "ok": False, "msg": tmsg})
            if "x" in m and "y" in m:
                bad = check_xyz({"x": m["x"], "y": m["y"], "z": z})
                if bad:
                    return send({"type": "done", "id": cid, "ok": False, "msg": bad})
                ok, msg = move(m["x"], m["y"], z, 0.5)
                if ok:
                    ok = hold(m.get("delay_s", 0))
                return send({"type": "done", "id": cid, "ok": ok, "msg": msg})
            ok = hold(m.get("delay_s", 0))
            return send({"type": "done", "id": cid, "ok": ok, "msg": tmsg})

        if cmd == "goto":
            bad = check_xyz(m) or check_extras(m)
            sp = m.get("speed", 0.5)
            if bad or not ok_num(sp, 0.1, SPEED_MAX):
                return send({"type": "done", "id": cid, "ok": False,
                             "msg": bad or "bad speed"})
            if not airborne:
                return send({"type": "done", "id": cid, "ok": False, "msg": "not airborne"})
            dl = m.get("delay_s", 0)
            if not ok_num(dl, 0, 600):
                return send({"type": "done", "id": cid, "ok": False, "msg": "bad delay_s"})
            apply_extras(m)
            ok, msg = move(m["x"], m["y"], m["z"], sp, m.get("wait_s"))
            if ok:
                ok = hold(dl)
                if dl:
                    msg = msg + (", held %.1fs" % dl)
            return send({"type": "done", "id": cid, "ok": ok, "msg": msg})

        if cmd == "land":
            bad = check_extras(m)
            if bad:
                return send({"type": "done", "id": cid, "ok": False, "msg": bad})
            apply_extras(m)
            if "x" in m and "y" in m:
                if not airborne:
                    return send({"type": "done", "id": cid, "ok": False, "msg": "not airborne"})
                z = m.get("z", last[2] if last[2] >= Z_MIN else 1.5)
                bad = check_xyz({"x": m["x"], "y": m["y"], "z": z})
                if bad:
                    return send({"type": "done", "id": cid, "ok": False, "msg": bad})
                ok, msg = move(m["x"], m["y"], z, 0.5)
                if not ok:
                    return send({"type": "done", "id": cid, "ok": False, "msg": msg})
            do_land_now()
            if not emergency.is_set():
                sleep_abortable(LAND_SETTLE_S)
            return send({"type": "done", "id": cid, "ok": True, "msg": "landed"})

        send({"type": "done", "id": cid, "ok": False, "msg": "unknown cmd: %s" % cmd})
    except Exception as e:
        log("execute error", e)
        send({"type": "done", "id": cid, "ok": False, "msg": "error: %s" % e})


def worker(m):
    with busy:
        execute(m)


def handle(m):
    cmd = m.get("cmd")
    if cmd == "emergency":
        emergency.set()
        log("EMERGENCY LAND")
        do_land_now()
        send({"type": "ack", "id": m.get("id"), "ok": True, "msg": "emergency landing"})
        return
    if cmd == "reset":
        if not busy.locked():
            emergency.clear()
        send({"type": "ack", "id": m.get("id"), "ok": not emergency.is_set(), "msg": "reset"})
        return
    if cmd == "ping":
        t = telem()
        send({"type": "state", "airborne": airborne, "emergency": emergency.is_set(),
              "busy": busy.locked(),
              "x": getattr(t, "x", None), "y": getattr(t, "y", None),
              "z": getattr(t, "z", None),
              "led": list(led_color), "a": user_vars["a"], "b": user_vars["b"],
              "targets": len(targets)})
        return
    if cmd == "led":
        c = [m.get("r"), m.get("g"), m.get("b")]
        idx = m.get("index")
        idx_ok = idx is None or (isinstance(idx, int) and not isinstance(idx, bool) and 0 <= idx < LED_COUNT)
        if not all(ok_num(v, 0, 255) for v in c) or not idx_ok:
            return info(m, "led", False, "bad led values")
        ok, msg = set_led(int(c[0]), int(c[1]), int(c[2]), idx)
        return info(m, "led", ok, "%s %s" % (c, msg))
    if cmd == "vars":
        bad = check_extras(m)
        if bad:
            return info(m, "vars", False, bad)
        set_vars(m)
        return info(m, "vars", True, "a=%s b=%s" % (user_vars["a"], user_vars["b"]))
    if cmd == "mark":
        t = telem()
        if not valid(t):
            return info(m, "mark", False, "no telemetry")
        added = add_target(t.x, t.y, t.z, str(m.get("label", "mark")))
        return info(m, "mark", added, "marked" if added else "duplicate or invalid")
    if cmd == "targets":
        with targets_lock:
            pts = list(targets)
        send({"type": "targets", "points": pts})
        return info(m, "targets", True, "%d targets" % len(pts))
    if cmd == "clear_targets":
        with targets_lock:
            del targets[:]
        return info(m, "clear_targets", True, "cleared")
    if cmd in ("takeoff", "goto", "land"):
        if emergency.is_set():
            return send({"type": "done", "id": m.get("id"), "ok": False,
                         "msg": "emergency active, send reset"})
        if busy.locked():
            return send({"type": "done", "id": m.get("id"), "ok": False, "msg": "busy"})
        send({"type": "ack", "id": m.get("id"), "ok": True, "msg": "accepted"})
        threading.Thread(target=worker, args=(m,), daemon=True).start()
        return
    send({"type": "ack", "id": m.get("id"), "ok": False,
          "msg": "unknown cmd: %s" % cmd})


def get_local_ips():
    """Collect local IP addresses for the startup log."""
    ips = []
    try:
        # hostname lookup
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        if local_ip and local_ip not in ips:
            ips.append(local_ip)
    except Exception:
        pass

    # UDP connect trick to find the primary LAN address
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        if ip and ip not in ips:
            ips.append(ip)
        s.close()
    except Exception:
        pass

    return ips if ips else ["127.0.0.1"]


def main():
    global conn
    srv_sock = socket.socket()
    srv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv_sock.bind((HOST, PORT))
    srv_sock.listen(1)

    # print server address and port
    ips = get_local_ips()
    log(f"Server started on port {PORT}. Available IPs:")
    for ip in ips:
        log(f"  -> http://{ip}:{PORT}  or socket connection to {ip}:{PORT}")

    while not rospy.is_shutdown():
        srv_sock.settimeout(1.0)
        try:
            c, addr = srv_sock.accept()
        except socket.timeout:
            continue
        log("GS connected", addr)
        conn = c
        c.settimeout(1.0)
        buf = b""
        try:
            while not rospy.is_shutdown():
                try:
                    d = c.recv(4096)
                except socket.timeout:
                    continue
                if not d:
                    break
                buf += d
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    if not line.strip():
                        continue
                    try:
                        handle(json.loads(line))
                    except Exception as e:
                        log("bad message", e)
        except Exception as e:
            log("conn error", e)
        try:
            c.close()
        except Exception:
            pass
        conn = None
        log("GS disconnected")
        if airborne and not emergency.is_set():
            log("link lost while airborne -> landing")
            emergency.set()
            do_land_now()


if __name__ == "__main__":
    main()

# ===== FUNCTION REFERENCE (quad_simple_new.py) =====
# report_detection(x, y, z, label="fire") -> bool
#     Send a detection (map-frame x, y, z in metres) to the ground station, which stores it in detections.json.
#     Returns False if invalid or duplicate (same label within DEDUP_M). Example: report_detection(1.2, -0.5, 1.8, "fire")
# add_target(x, y, z=None, label="") -> bool : same as report_detection (base implementation, thread-safe).
# set_led(r, g, b, index=None) -> (ok, msg) : set all LEDs, or one LED if index is given. Values 0-255.
# set_vars(m) : m is a dict with "a" and/or "b"; stores them in user_vars. Read with user_vars["a"].
# check_extras(m) -> None or error text : validates "led", "a", "b" keys of a command.
# apply_extras(m) : applies "led" and "a"/"b" from a command dict.
# info(m, what, ok, msg, **kw) : send an info message to the ground station.
# send(obj) : send any JSON-serialisable dict to the ground station (no-op if disconnected).
# log(*a) : print a "[quad]" console line.
# detect_led_count() -> int : read LED count from led/state (falls back to 1).
# telem(timeout) -> telemetry or None : current position/yaw from get_telemetry.
# valid(t) -> bool : True if telemetry has finite x, y, z.
# ok_num(v, lo, hi) -> bool : True if v is a real number within [lo, hi].
# check_xyz(m) -> None or error text : validates x, y, z against field limits.
# sleep_abortable(sec) : sleep that returns early on emergency.
# hold(sec) : wait after arrival, abortable.
# wait_takeoff(z, limit) : wait until the takeoff altitude is reached.
# move(x, y, z, speed, wait_s=None) -> (ok, msg) : fly to a point and wait for arrival (drone must be airborne).
# do_land_now() : land immediately.
# execute(m) : run one takeoff/goto/land command in the worker thread.
# worker(m) : thread wrapper around execute.
# handle(m) : dispatch an incoming command (led, vars, mark, targets, clear_targets, takeoff, goto, land, emergency, reset, ping).
# main() : start the TCP server on port 5000 and handle the connection.
