"""Persistent connections; all socket I/O takes place outside the GUI thread."""
import json
import socket
import threading
from collections import deque
from queue import Queue, Empty
from PyQt5.QtCore import QThread
import websocket


class DroneConnection(QThread):
    def __init__(self, host, port):
        super().__init__()
        self.host, self.port = host, port
        self.endpoint = f'{host}:{port}'
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._logs = deque(maxlen=2000)
        self._dropped = 0
        self._snapshot = {'online': False, 'battery': '--', 'altitude': '--', 'received': 0}
        self._requests = Queue()
        self._topics = {'/mavros/battery', '/mavros/altitude'}

    def snapshot(self):
        with self._lock:
            return dict(self._snapshot)

    def drain_logs(self, limit=100):
        with self._lock:
            lines = [self._logs.popleft() for _ in range(min(limit, len(self._logs)))]
            dropped, self._dropped = self._dropped, 0
        if dropped:
            lines.insert(0, f'[LOG] {dropped} old messages discarded (display buffer full)')
        return lines

    def _log(self, text):
        with self._lock:
            if len(self._logs) == self._logs.maxlen:
                self._dropped += 1
            # Never let image/base64 payloads make the UI unresponsive.
            self._logs.append(text[:4000] + (' … [truncated]' if len(text) > 4000 else ''))

    def subscribe(self, topic):
        self._requests.put(('subscribe', topic))

    def unsubscribe(self, topic):
        if topic not in {'/mavros/battery', '/mavros/altitude'}:
            self._requests.put(('unsubscribe', topic))

    def stop(self):
        # Do not close/wait on a socket from the GUI thread.
        self._stop_event.set()

    def _apply_requests(self, ws):
        while True:
            try:
                op, topic = self._requests.get_nowait()
            except Empty:
                return
            if op == 'subscribe':
                if topic in self._topics:
                    continue
                self._topics.add(topic)
            else:
                if topic not in self._topics:
                    continue
                self._topics.remove(topic)
            ws.send(json.dumps({'op': op, 'topic': topic, 'throttle_rate': 100,
                                'queue_length': 1}))

    def run(self):
        while not self._stop_event.is_set():
            ws = None
            try:
                ws = websocket.create_connection(
                    f'ws://{self.host}:{self.port}', timeout=1.5,
                    enable_multithread=True,
                    sockopt=((socket.IPPROTO_TCP, socket.TCP_NODELAY, 1),))
                ws.settimeout(0.1)
                for topic in tuple(self._topics):
                    ws.send(json.dumps({'op': 'subscribe', 'topic': topic,
                                        'throttle_rate': 100, 'queue_length': 1}))
                with self._lock:
                    self._snapshot['online'] = True
                self._log('[CONNECTED]')
                while not self._stop_event.is_set():
                    self._apply_requests(ws)
                    try:
                        raw = ws.recv()
                    except websocket.WebSocketTimeoutException:
                        continue
                    if not raw:
                        break
                    if isinstance(raw, bytes):
                        raw = raw.decode('utf-8', errors='replace')
                    with self._lock:
                        self._snapshot['received'] += 1
                    self._log(raw)
                    try:
                        message = json.loads(raw)
                        if not isinstance(message, dict):
                            continue
                        data = message.get('msg', {})
                        if not isinstance(data, dict):
                            continue
                        with self._lock:
                            if message.get('topic') == '/mavros/battery':
                                v, p = data.get('voltage'), data.get('percentage')
                                text = f'{float(v):.1f} V' if v is not None else '--'
                                if isinstance(p, (int, float)) and 0 <= p <= 1:
                                    text += f' ({p * 100:.0f}%)'
                                self._snapshot['battery'] = text
                            elif message.get('topic') == '/mavros/altitude':
                                self._snapshot['altitude'] = f"{float(data['relative']):.2f} m"
                    except (ValueError, TypeError, KeyError):
                        pass
            except Exception as exc:
                self._log(f'[ERROR] {exc}')
            finally:
                with self._lock:
                    self._snapshot.update(online=False, battery='--', altitude='--')
                if ws is not None:
                    # shutdown releases the socket without a WebSocket close handshake.
                    try:
                        ws.shutdown()
                    except Exception:
                        pass
                self._log('[DISCONNECTED]')
            self._stop_event.wait(1.0)
