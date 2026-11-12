#!/usr/bin/env python3
import json, math, os, queue, socket, sys, threading, time

DRONE_IP = "192.168.0.86"
# DRONE_IP = "192.168.0.240"
DRONE_PORT = 3000
SPEED = 0.7
DEFAULT_Z = 2.1
DEFAULT_DELAY = 8
short_time_delay = 2
TAKEOFF_Z = 2.1
TAKEOFF_DELAY = 1.0
GOTO_TIMEOUT = 150.0
TAKEOFF_TIMEOUT = 70.0
LAND_TIMEOUT = 90.0
MISSION_FILE = "mission.json"
DETECTIONS_FILE = "detections.json"


X_LIM, Y_LIM = 3.0, 1.5
Z_MIN, Z_MAX = 0.5, 3.0

inbox = queue.Queue()
sock = None
send_lock = threading.Lock()
run_id = [0]
found = []
found_lock = threading.Lock()
typed = []
COLORS = {"red": (255, 0, 0), "green": (0, 255, 0), "blue": (0, 0, 255),
          "yellow": (255, 255, 0), "white": (255, 255, 255), "purple": (255, 0, 255),
          "cyan": (0, 255, 255), "orange": (255, 100, 0), "off": (0, 0, 0)}


def connect():
    global sock
    sock = socket.create_connection((DRONE_IP, DRONE_PORT), timeout=5.0)
    sock.settimeout(1.0)
    sock.sendall(b'{"cmd":"ping"}\n')
    th = threading.Thread(target=reader, daemon=True)
    th.start()
    print("connected to %s:%d" % (DRONE_IP, DRONE_PORT))


def reader():
    buf = b""
    while True:
        try:
            d = sock.recv(4096)
        except socket.timeout:
            continue
        except Exception:
            return
        if not d:
            print("\n[gs] drone closed the connection")
            return
        buf += d
        while b"\n" in buf:
            line, buf = buf.split(b"\n", 1)
            if not line.strip():
                continue
            try:
                m = json.loads(line)
            except Exception:
                print("[gs] bad line:", line[:100])
                continue
            kind = m.get("type")
            if kind == "state":
                print("\n[drone] airborne=%s emergency=%s busy=%s pos=(%s, %s, %s) led=%s a=%s b=%s targets=%s" % (
                    m.get("airborne"), m.get("emergency"), m.get("busy"),
                    m.get("x"), m.get("y"), m.get("z"),
                    m.get("led"), m.get("a"), m.get("b"), m.get("targets")))
            elif kind == "targets":
                for p in m.get("points", []):
                    add_found(p)
            elif kind == "info":
                print("\n[drone] %s %s: %s" % (m.get("what"), "OK" if m.get("ok") else "FAIL", m.get("msg", "")))
            else:
                inbox.put(m)


def send(obj):
    if sock is None:
        print("\n[gs] not connected")
        return False
    try:
        with send_lock:
            sock.sendall((json.dumps(obj) + "\n").encode())
        return True
    except OSError as e:
        print("\n[gs] send failed (link down?):", e)
        return False


def next_id():
    run_id[0] += 1
    return run_id[0]


def key_hit():
    try:
        import msvcrt
        if msvcrt.kbhit():
            ch = msvcrt.getch()
            if ch in (b"\x00", b"\xe0"):
                msvcrt.getch()
                return ""
            return ch.decode(errors="ignore").lower()
        return None
    except ImportError:
        pass
    try:
        import select
        r, _, _ = select.select([sys.stdin], [], [], 0)
        if r:
            return sys.stdin.read(1).lower()
    except Exception:
        pass
    return None


def live_input():
    while True:
        k = key_hit()
        if k is None:
            return None
        if not k:
            continue
        if k == "e" and not typed:
            return "e"
        if k in ("\r", "\n"):
            line = "".join(typed).strip()
            del typed[:]
            print()
            if line:
                return line
            continue
        if k in ("\x08", "\x7f"):
            if typed:
                typed.pop()
                print("\b \b", end="", flush=True)
            continue
        if k.isprintable():
            typed.append(k)
            print(k, end="", flush=True)


def flush_keys():
    while key_hit() is not None:
        pass


def default_mission():
    return {
        "takeoff": {"x": -1.75, "y": -1.5, "z": TAKEOFF_Z, "delay_s": TAKEOFF_DELAY},
        "waypoints": [

            {"x": -1.75, "y": -1.5, "z": DEFAULT_Z, "delay_s": 10},
            {"x": -1.75, "y":  1.5, "z": DEFAULT_Z, "delay_s": 10},
            {"x": -1.875, "y": 0.375, "z": DEFAULT_Z, "delay_s": 10},
            {"x":  -1.75, "y":  -1.5, "z": DEFAULT_Z, "delay_s": 10},


            # {"x": -3, "y": -1.5, "z": DEFAULT_Z, "delay_s": 7},
            # {"x": 3, "y":  -1.5, "z": DEFAULT_Z, "delay_s": DEFAULT_DELAY},
            # {"x": 3, "y":  0, "z": DEFAULT_Z, "delay_s": short_time_delay},
            # {"x":  -3, "y":  0, "z": DEFAULT_Z, "delay_s": DEFAULT_DELAY},
            # {"x":  -3, "y":  1.5, "z": DEFAULT_Z, "delay_s": short_time_delay},
            # {"x":  3, "y":  1.5, "z": DEFAULT_Z, "delay_s": DEFAULT_DELAY},
            # {"x":  0.0, "y":  0.0, "z": DEFAULT_Z, "delay_s": 0.0},
        ],
        "land": {"x": -1.75, "y": -1.5},
    }


def load_mission():
    if not os.path.exists(MISSION_FILE):
        return default_mission()
    try:
        with open(MISSION_FILE, "r", encoding="utf-8") as f:
            m = json.load(f)
    except Exception as e:
        print("[gs] cannot read %s (%s), using default" % (MISSION_FILE, e))
        return default_mission()
    m.setdefault("takeoff", default_mission()["takeoff"])
    m.setdefault("waypoints", default_mission()["waypoints"])
    m.setdefault("land", {"x": 0.0, "y": 0.0})
    tk = m["takeoff"]
    tk.setdefault("x", 0.0); tk.setdefault("y", 0.0)
    tk.setdefault("z", TAKEOFF_Z); tk.setdefault("delay_s", 0.0)
    for w in m["waypoints"]:
        w.setdefault("z", DEFAULT_Z)
        w.setdefault("delay_s", 0.0)
    m["land"].setdefault("x", 0.0); m["land"].setdefault("y", 0.0)
    return m


def save_mission(m):
    try:
        with open(MISSION_FILE, "w", encoding="utf-8") as f:
            json.dump(m, f, indent=2)
        print("[gs] saved %d waypoints to %s" % (len(m["waypoints"]), MISSION_FILE))
    except Exception as e:
        print("[gs] save failed:", e)


def show(m):
    tk = m["takeoff"]
    print("\n--- mission ---")
    print(" takeoff  (%.2f, %.2f) z=%.2f  delay=%.1fs" %
          (tk["x"], tk["y"], tk["z"], tk["delay_s"]))
    for i, w in enumerate(m["waypoints"]):
        print("  %2d  (%.2f, %.2f) z=%.2f  delay=%.1f%s" %
              (i, w["x"], w["y"], w["z"], w["delay_s"], extra_text(w)))
    print(" land     (%.2f, %.2f)" % (m["land"]["x"], m["land"]["y"]))
    print(" total path %.1f m" % path_len(m) + "\n")


def extra_text(w):
    s = ""
    if "led" in w:
        s += "  led=" + str(w["led"])
    if "a" in w or "b" in w:
        s += "  vars=(%s, %s)" % (w.get("a", "-"), w.get("b", "-"))
    return s


def path_len(m):
    pts = [(m["takeoff"]["x"], m["takeoff"]["y"])]
    pts += [(w["x"], w["y"]) for w in m["waypoints"]]
    pts.append((m["land"]["x"], m["land"]["y"]))
    return sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))


def in_field(x, y):
    return -X_LIM <= x <= X_LIM and -Y_LIM <= y <= Y_LIM


def wait_for(cid, timeout, label):
    t0 = time.time()
    while time.time() - t0 < timeout:
        line = live_input()
        if line == "e":
            print("\n[gs] abort requested -> emergency landing")
            emergency()
            return False
        if line:
            parts = line.split()
            if not quick(parts[0].lower(), parts[1:]):
                print("\n[gs] live commands: led, vars, targets, mark, fetch, e")
        try:
            m = inbox.get(timeout=0.2)
        except queue.Empty:
            continue
        if m.get("id") != cid:
            print("[gs] (stale reply id=%s %s)" % (m.get("id"), m.get("type")))
            continue
        if m.get("type") == "done":
            ok = bool(m.get("ok"))
            print("[%s] %s  %s" % (label, "OK " if ok else "FAIL", m.get("msg", "")))
            return ok
    print("[%s] TIMEOUT after %.0fs" % (label, timeout))
    return False


def emergency():
    try:
        send({"cmd": "emergency"})
    except Exception as e:
        print("[gs] emergency send failed:", e)


def add_extras(src, msg):
    for k in ("led", "a", "b"):
        if k in src:
            msg[k] = src[k]


def add_found(p):
    try:
        x, y = float(p["x"]), float(p["y"])
    except (KeyError, TypeError, ValueError):
        return False
    if not (math.isfinite(x) and math.isfinite(y)):
        return False
    try:
        z = float(p.get("z"))
    except (TypeError, ValueError):
        z = None
    label = str(p.get("label", ""))
    with found_lock:
        for q in found:
            if q["label"] == label and math.dist((q["x"], q["y"]), (x, y)) < 0.05:
                return False
        found.append({"x": x, "y": y, "z": z, "label": label})
        n = len(found) - 1
        save_detections()
    print("\n[target] #%d (%.2f, %.2f) z=%s %s" % (n, x, y, "-" if z is None else "%.2f" % z, label))
    return True


def save_detections():
    rows = [{"label": p["label"], "x": p["x"], "y": p["y"], "z": p["z"],
             "text": "%s detected at x=%.2f y=%.2f z=%s" % (
                 p["label"], p["x"], p["y"], "-" if p["z"] is None else "%.2f" % p["z"])}
            for p in found]
    try:
        tmp = DETECTIONS_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(rows, f, indent=2, ensure_ascii=False)
        os.replace(tmp, DETECTIONS_FILE)
    except OSError as e:
        print("[gs] cannot save detections:", e)


def show_found():
    with found_lock:
        pts = list(found)
    print("\n--- targets from drone ---")
    if not pts:
        print("  (none)")
    for i, p in enumerate(pts):
        print("  %2d  (%.2f, %.2f) z=%s  %s" % (
            i, p["x"], p["y"], "-" if p["z"] is None else "%.2f" % p["z"], p["label"]))
    print()


def parse_color(args):
    if not args:
        return None
    if args[0].lower() in COLORS:
        rgb = COLORS[args[0].lower()]
        rest = args[1:]
    else:
        if len(args) < 3:
            return None
        try:
            rgb = tuple(int(v) for v in args[:3])
        except ValueError:
            return None
        rest = args[3:]
    if any(not 0 <= v <= 255 for v in rgb):
        return None
    index = None
    if rest:
        try:
            index = int(rest[0])
        except ValueError:
            return None
        if index < 0:
            return None
    return rgb, index


def quick(c, args):
    if c == "led":
        p = parse_color(args)
        if not p:
            print("usage: led R G B [INDEX] | led NAME [INDEX]  names: " + " ".join(COLORS))
            return True
        rgb, idx = p
        msg = {"cmd": "led", "id": next_id(), "r": rgb[0], "g": rgb[1], "b": rgb[2]}
        if idx is not None:
            msg["index"] = idx
        send(msg)
        return True
    if c == "vars":
        try:
            a, b = float(args[0]), float(args[1])
        except (IndexError, ValueError):
            print("usage: vars A B")
            return True
        send({"cmd": "vars", "id": next_id(), "a": a, "b": b})
        return True
    if c == "targets":
        show_found()
        return True
    if c == "fetch":
        send({"cmd": "targets", "id": next_id()})
        return True
    if c == "mark":
        send({"cmd": "mark", "id": next_id(), "label": (" ".join(args)[:32] or "mark")})
        return True
    return False


def fly(m):
    print("\n=== mission start ===")
    tk = m["takeoff"]
    cid = next_id()
    msg = {"cmd": "takeoff", "id": cid, "x": tk["x"], "y": tk["y"],
           "z": tk["z"], "delay_s": tk["delay_s"]}
    add_extras(tk, msg)
    send(msg)
    if not wait_for(cid, TAKEOFF_TIMEOUT + tk["delay_s"], "takeoff"):
        print("=== aborted: takeoff failed ===")
        return False

    for i, w in enumerate(m["waypoints"]):
        cid = next_id()
        msg = {"cmd": "goto", "id": cid, "x": w["x"], "y": w["y"], "z": w["z"],
               "speed": SPEED, "delay_s": w["delay_s"]}
        add_extras(w, msg)
        send(msg)
        if not wait_for(cid, GOTO_TIMEOUT + w["delay_s"], "wp%02d" % i):
            print("=== aborted at waypoint %d ===" % i)
            emergency()
            return False

    cid = next_id()
    send({"cmd": "land", "id": cid, "x": m["land"]["x"], "y": m["land"]["y"]})
    wait_for(cid, LAND_TIMEOUT, "land")
    print("=== mission end ===")
    return True


def parse_pair(args):
    if len(args) < 2:
        return None
    try:
        return float(args[0]), float(args[1])
    except ValueError:
        return None


def cmd_loop(m):
    print("commands: h=help  fly  list  add  ins  del  delay  takeoff_delay  "
          "clear  save  load  ping  led  vars  wpled  wpvars  targets  fetch  mark  use  tclear  e=EMERGENCY  q=quit")
    while True:
        try:
            line = input("gs> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return m
        if not line:
            continue
        parts = line.split()
        c, args = parts[0].lower(), parts[1:]

        if quick(c, args):
            continue

        if c in ("q", "quit", "exit"):
            if input("quit? mission is saved already (y/n): ").strip().lower() == "y":
                return m
            continue
        if c in ("h", "help", "?"):
            print("""  list                       show waypoints
  add X Y [Z [DELAY]]        append a waypoint (default z=%.1f, delay=%.1f)
  ins I X Y [Z [DELAY]]      insert before index I
  del I                      delete waypoint I
  delay I S                  set hold time of waypoint I
  takeoff_delay S            hold time after takeoff
  takeoff X Y Z              set takeoff point/altitude
  land X Y                   set landing point (default 0 0)
  clear                      delete all waypoints
  pattern XMIN XMAX YMIN YMAX [STEP]   rebuild lawnmower
  save | load                mission.json
  fly                        run the mission
  ping                       ask the drone for its state
  led R G B [INDEX]          set LED colour now (also: led NAME, names: red green blue yellow white purple cyan orange off)
  vars A B                   send two numbers to the drone now
  wpled I R G B | wpled I NAME | wpled I none    LED colour applied when waypoint I starts
  wpvars I A B | wpvars I none                   two numbers applied when waypoint I starts
  targets                    show targets reported by the drone
  fetch                      ask the drone to resend all its targets
  mark [LABEL]               drone records its current position as a target
  use [I ...]                append targets (all or listed) as waypoints
  tclear                     clear targets on drone and here
  while flying, type: led.. / vars.. / targets / mark / fetch + Enter, or e alone to abort
  e                          EMERGENCY LAND (also works during flight)
  q                          quit""" % (DEFAULT_Z, DEFAULT_DELAY))
            continue
        if c == "list":
            show(m); continue
        if c == "ping":
            send({"cmd": "ping"}); continue
        if c == "e":
            emergency(); continue
        if c == "save":
            save_mission(m); continue
        if c == "load":
            m = load_mission(); show(m); continue
        if c == "clear":
            m["waypoints"] = []; show(m); continue
        if c == "takeoff_delay":
            try:
                m["takeoff"]["delay_s"] = max(0.0, float(args[0]))
                print("takeoff delay = %.1fs" % m["takeoff"]["delay_s"])
            except (IndexError, ValueError):
                print("usage: takeoff_delay SECONDS")
            continue
        if c == "takeoff":
            p = parse_pair(args)
            try:
                z = float(args[2]) if len(args) > 2 else m["takeoff"]["z"]
            except ValueError:
                z = m["takeoff"]["z"]
            if not p or not (Z_MIN <= z <= Z_MAX) or not in_field(*p):
                print("usage: takeoff X Y [Z]   (inside +-3.0 / +-1.5, z %.1f..%.1f)"
                      % (Z_MIN, Z_MAX))
                continue
            m["takeoff"].update({"x": p[0], "y": p[1], "z": z})
            show(m); continue
        if c == "land":
            p = parse_pair(args)
            if not p or not in_field(*p):
                print("usage: land X Y")
                continue
            m["land"].update({"x": p[0], "y": p[1]})
            show(m); continue
        if c == "delay":
            try:
                i, s = int(args[0]), max(0.0, float(args[1]))
            except (IndexError, ValueError):
                print("usage: delay INDEX SECONDS"); continue
            if not 0 <= i < len(m["waypoints"]):
                print("no waypoint %d" % i); continue
            m["waypoints"][i]["delay_s"] = s
            print("wp%02d delay = %.1fs" % (i, s)); continue
        if c == "del":
            try:
                i = int(args[0])
            except (IndexError, ValueError):
                print("usage: del INDEX"); continue
            if not 0 <= i < len(m["waypoints"]):
                print("no waypoint %d" % i); continue
            m["waypoints"].pop(i); show(m); continue
        if c in ("add", "ins"):
            try:
                if c == "add":
                    idx = len(m["waypoints"]); rest = args
                else:
                    idx = int(args[0]); rest = args[1:]
                x, y = float(rest[0]), float(rest[1])
                z = float(rest[2]) if len(rest) > 2 else DEFAULT_Z
                dl = float(rest[3]) if len(rest) > 3 else DEFAULT_DELAY
            except (IndexError, ValueError):
                print("usage: %s [INDEX] X Y [Z [DELAY]]" % c); continue
            if not in_field(x, y):
                print("outside the field (+-3.0 / +-1.5)"); continue
            if not Z_MIN <= z <= Z_MAX:
                print("z must be %.1f..%.1f" % (Z_MIN, Z_MAX)); continue
            idx = max(0, min(idx, len(m["waypoints"])))
            m["waypoints"].insert(idx, {"x": x, "y": y, "z": z,
                                        "delay_s": max(0.0, dl)})
            show(m); continue
        if c == "pattern":
            try:
                x0, x1, y0, y1 = (float(a) for a in args[:4])
                step = float(args[4]) if len(args) > 4 else 1.0
            except (IndexError, ValueError):
                print("usage: pattern XMIN XMAX YMIN YMAX [STEP]"); continue
            m["waypoints"] = build_lawnmower(x0, x1, y0, y1, step, m["waypoints"][0]["z"]
                                             if m["waypoints"] else DEFAULT_Z)
            show(m); continue
        if c in ("wpled", "wpvars"):
            try:
                i = int(args[0])
            except (IndexError, ValueError):
                print("usage: %s INDEX ..." % c); continue
            if not 0 <= i < len(m["waypoints"]):
                print("no waypoint %d" % i); continue
            w = m["waypoints"][i]
            keys = ("led",) if c == "wpled" else ("a", "b")
            if len(args) >= 2 and args[1].lower() == "none":
                for k in keys:
                    w.pop(k, None)
                show(m); continue
            if c == "wpled":
                p = parse_color(args[1:])
                if not p or p[1] is not None:
                    print("usage: wpled INDEX R G B | NAME | none"); continue
                w["led"] = list(p[0])
            else:
                try:
                    w["a"], w["b"] = float(args[1]), float(args[2])
                except (IndexError, ValueError):
                    print("usage: wpvars INDEX A B | none"); continue
            show(m); continue
        if c == "tclear":
            send({"cmd": "clear_targets", "id": next_id()})
            with found_lock:
                del found[:]
            continue
        if c == "use":
            with found_lock:
                pts = list(found)
            if args:
                try:
                    pts = [pts[int(a)] for a in args if 0 <= int(a) < len(pts)]
                except ValueError:
                    print("usage: use [INDEX ...]"); continue
            n = 0
            for p in pts:
                if not in_field(p["x"], p["y"]):
                    print("skipped (outside field): (%.2f, %.2f)" % (p["x"], p["y"]))
                    continue
                m["waypoints"].append({"x": p["x"], "y": p["y"], "z": DEFAULT_Z,
                                       "delay_s": DEFAULT_DELAY})
                n += 1
            print("added %d waypoints" % n)
            show(m); continue
        if c == "fly":
            if not m["waypoints"]:
                print("no waypoints; add some first"); continue
            fly(m); continue
        print("unknown command '%s' (h for help)" % c)


def build_lawnmower(x0, x1, y0, y1, step, z, delay=None):
    if delay is None:
        delay = DEFAULT_DELAY
    x0, x1 = min(x0, x1), max(x0, x1)
    y0, y1 = min(y0, y1), max(y0, y1)
    step = max(0.3, step)
    rows = [y0]
    y = y0
    while y + step <= y1 + 1e-9:
        y += step
        rows.append(y)
    pts = []
    left_to_right = True
    for y in rows:
        if left_to_right:
            pts += [(x0, y), (x1, y)]
        else:
            pts += [(x1, y), (x0, y)]
        left_to_right = not left_to_right
    out = []
    for i, (x, y) in enumerate(pts):
        if out and abs(out[-1]["x"] - x) < 1e-6 and abs(out[-1]["y"] - y) < 1e-6:
            continue
        out.append({"x": round(x, 3), "y": round(y, 3), "z": z, "delay_s": delay})
    return out


def main():
    global sock
    try:
        connect()
    except Exception as e:
        print("[gs] cannot connect to %s:%d -> %s" % (DRONE_IP, DRONE_PORT, e))
        print("     power on the drone, wait for WiFi, check the IP.")
        return
    flush_keys()
    m = load_mission()
    show(m)
    try:
        cmd_loop(m)
    finally:
        try:
            sock.close()
        except Exception:
            pass
        print("bye")


if __name__ == "__main__":
    main()

# ===== FUNCTION REFERENCE (gs_simple_new.py) =====
# add_found(p) -> bool : store a detection dict {x, y, z, label} sent by the drone, print it and write detections.json.
#     Called automatically by reader() for every "targets" message. Duplicates (same label within 5 cm) are ignored.
# save_detections() : rewrite detections.json with every detection and a text such as "fire detected at x=1.20 y=-0.50 z=1.80".
# show_found() : print all detections.
# connect() : open the TCP connection to the drone and start reader().
# reader() : background thread that parses drone messages (state, targets, info, ack/done).
# send(obj) : send a dict to the drone. next_id() : unique command id.
# quick(c, args) -> bool : run a live command (led, vars, targets, fetch, mark). Example: quick("mark", ["fire"])
# parse_color(args) : parse "red [idx]" or "R G B [idx]" into ((r, g, b), idx).
# add_extras(src, msg) : copy led/a/b from a waypoint into a command message.
# key_hit() / live_input() / flush_keys() : non-blocking keyboard input; lone "e" = emergency.
# default_mission() / load_mission() / save_mission(m) : mission file handling (mission.json).
# show(m), extra_text(w), path_len(m), in_field(x, y) : display and field-limit helpers.
# wait_for(cid, timeout, label) : wait for the done message of a command.
# emergency() : send the emergency command.
# fly(m) -> bool : run the mission; False if aborted.
# parse_pair(args), cmd_loop(m) : the interactive menu.
# build_lawnmower(x0, x1, y0, y1, step, z, delay=None) : create a scan-pattern waypoint list.
# main() : entry point.
