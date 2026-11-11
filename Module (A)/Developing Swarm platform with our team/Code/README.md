# TECHNIC / Flight Operations Workspace

A multi-file **PyQt5** dashboard for one leader and multiple child devices.
The interface is entirely in English, with an original dark/neon design,
animated quadcopter artwork, and a live WebSocket console.

> **PRINT-ONLY DEMO:** Every command in `actions.py`, including emergency
> and safety commands, only prints to the terminal. No flight commands are
> transmitted. This application is not an operational flight safety system.

## Quick start

Requires Python **3.9+** and a desktop environment.

```bash
cd technic_dashboard
python -m venv .venv
```

Activate the environment:

```bash
# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate
```

Install and launch:

```bash
python -m pip install -r requirements.txt
python main.py
```

Alternatively, use `run.bat` on Windows or `bash run.sh` on Linux/macOS
**after installing the dependencies**. Keep the terminal open to see command output.
The WebSocket package is named `websocket-client`, not `websocket`.

## Design and navigation

- Two-second animated introduction with neon rotor rings and a moving scan line.
  The progress line represents the introduction, **not** device initialization
  or a preflight safety check.
- Original vector-rendered quadcopter illustration: sharp at high DPI,
  no remote images, no downloaded fonts, and no internet dependency for artwork.
- Cyan/teal workspace with a separate violet leader node and leader command card.
- **Leader commands are first in the command deck:** Scan area, Return to nest,
  and Immediate land. Their independent functions live in `actions.py`.
- Registered, online, selected, and received-messages-per-second cards.
- A traffic chart derived from **actual received WebSocket frames**. There is
  no generated battery data, invented positioning, or simulated flight telemetry.
- Overview / Fleet nodes / Live stream navigation in the left rail.
- Scrollable fleet workspace and command deck; draggable console and deck splitters.
- Turn off **Visual motion** to stop the local artwork, schematic topology,
  and camera overlay animations. Camera reception continues normally.
- The fleet topology is a schematic of registered devices, not GPS positioning.
- SVG navigation icons and app icon are bundled in `assets/`.

## Connecting devices

1. Enter a valid IPv4 or IPv6 address and WebSocket port (default `9090`).
2. Choose **Add leader** or **Add child**. Only one leader is permitted.
3. The application connects to `ws://HOST:PORT` using the ROS rosbridge protocol.
4. Battery (`/mavros/battery`) and altitude (`/mavros/altitude`) are subscribed
   automatically. Until valid data arrives, the table shows `--`.
5. Choose **Inspect**, filter the predefined topic list, and double-click a topic
   to subscribe. The latest matching JSON message appears in the inspector.
6. Remove the current leader before replacing it. Repeated endpoints are rejected.

The TOPICS column is the number of predefined topics available to inspect,
not the number of discovered or currently active ROS topics. The application
does not perform ROS topic discovery. It uses one persistent connection per
device, including when an inspector is open.

The illustration is a **concept visual**, not a map, camera feed, aircraft
identification, or live attitude display. The RX chart measures message traffic,
not connection latency or command delivery time.

## Live cameras

Each device has its own camera preview in its table row. Camera connections
are independent of WebSocket connections and start only when you press **Start**.

- The default camera server is `http://DEVICE_IP:8080`, using the ROS
  `web_video_server` MJPEG endpoint for the editable image topic.
- Use **Camera settings** to change the server URL and image topic. A direct
  HTTP(S) MJPEG stream or JPEG/PNG snapshot URL is also supported.
- The server must already be running on the device and be reachable from this
  computer. The dashboard does not install or launch a camera server.
- Each camera receives and decodes images in its own worker. The GUI polls the
  latest frame rather than queueing every image. Memory and decoded image
  dimensions are bounded; failed connections retry automatically.
- **Stop** closes only that camera preview; removing a device stops its camera
  and WebSocket workers. HTML pages are rejected, not treated as video.
- This is an HTTP image-stream viewer, not an RTSP, WebRTC, H.264, or video-file
  player. Camera URLs are user-configured network destinations; use trusted
  endpoints and do not expose unauthenticated camera/rosbridge servers publicly.

## Command scope

- Selected-device actions use checked rows from both tables.
- **Select all devices** and **Clear selection** apply to both tables.
- **Land ALL** and **Disarm ALL** receive all registered endpoints.
- Leader commands receive only the leader endpoint, regardless of row selection.
- The delay and altitude fields only pass values to print-only demo functions.
  The delay does not schedule a real operation.
- Implement any future device command transport outside the UI thread and test
  it separately with appropriate safeguards. Do not replace print statements
  with blocking socket calls or flight logic in the Qt event loop.

## Responsiveness and logs

- Socket connect/receive/subscribe/reconnect operations run in device workers,
  not in the GUI thread.
- GUI updates are batched every 100 ms. The artwork runs at 25 fps only when
  visible, and traffic samples are added about once a second.
- The traffic counter includes received frames even when display logs overflow
  or display is paused. Connection-status log lines do not count as RX frames.
- Each connection keeps at most 2,000 pending display messages. Older messages
  are discarded when full, with a drop-count notice.
- The console keeps 3,000 text blocks. Individual display messages are limited
  to 4,000 characters to avoid huge image/base64 payloads overwhelming Qt.
  This is a bounded monitor, not a complete archival logger.
- **Pause display** drops incoming display lines during the pause; it does not
  pause transport, telemetry, counters, or the topic inspector. There is no replay.
- Log timestamps mark the GUI batch display time, not exact network arrival time.
- Inspector subscriptions use the same connection. Closing the inspector removes
  its chosen subscription; battery and altitude subscriptions remain active.
- Window shutdown and device removal do not call a blocking worker `wait()`
  from the GUI thread. The application polls workers until they finish.

Responsiveness still depends on fleet size, hardware, payload sizes, and network
conditions. Real flight-command latency cannot be measured by these print-only
buttons. Disconnected devices reconnect automatically.

## Project files

```text
technic_dashboard/
  main.py             Application, layout, device tables, console, inspectors
  visuals.py          Original quadcopter artwork, splash, cards, RX chart
  effects.py          Schematic topology, animated buttons, responsive tables
  camera.py           Per-device threaded HTTP image preview and controls
  theme.py            Shared dark/neon style sheet
  connection.py       Persistent threaded WebSocket / rosbridge transport
  actions.py          Independent print-only operation functions
  topics.py           Predefined ROS topic catalog
  assets/             Original bundled SVG icons
  requirements.txt    Runtime dependencies
  run.bat             Windows launcher
  run.sh              Linux/macOS launcher
  test_transport.py   Mocked transport unit tests; works without Qt
  test_ui.py          Optional headless PyQt5 UI smoke tests
  test_camera.py      Camera parsing, local HTTP streaming and lifecycle tests
  README.md           This guide
```

## Tests

```bash
python -m unittest -v test_transport.py
python -m py_compile *.py
```

With PyQt5 installed, run the UI tests without a display:

```bash
# Linux/macOS
QT_QPA_PLATFORM=offscreen python -m unittest -v test_ui.py

# Windows PowerShell
$env:QT_QPA_PLATFORM="offscreen"
python -m unittest -v test_ui.py
```

Or run all tests: `python -m unittest discover -v`.

Transport tests use a fake socket. UI tests mock device workers and cover
leader limits, multiple children, invalid and duplicate endpoints, selection,
logs and pause, metrics, inspector subscriptions, leader actions, removal,
navigation, minimum-width controls, per-row camera panels, and artwork/splash
rendering. Camera tests use a local HTTP server for real JPEG/MJPEG reception,
HTML rejection, URL validation, parser limits, and worker shutdown. Qt-dependent
tests are explicitly skipped when PyQt5 is unavailable. No test validates a
real aircraft or ROS bridge.

### Validation in the delivery environment

All 14 tests and Python syntax checks passed, including headless Qt UI tests
and local HTTP camera-stream tests. This does not replace testing on your target
desktop with its actual camera server, ROS topics, network, and display scaling.
A real desktop/ROS connection test is still required.
