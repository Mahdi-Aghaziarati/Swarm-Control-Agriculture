"""Bounded, asynchronous HTTP camera monitor (MJPEG or JPEG/PNG snapshots).
Only the most recent decoded frame crosses into the GUI; there is no frame queue.
"""
import threading
import time
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

from PyQt5.QtCore import Qt, QThread, QTimer, QRectF, QBuffer, QByteArray, QIODevice
from PyQt5.QtGui import QImageReader, QPainter, QColor, QPen, QFont
from effects import CommandButton
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                             QDialog, QFormLayout, QLineEdit, QComboBox,
                             QDialogButtonBox)

CAMERA_TOPICS = ['/main_camera/image_raw', '/second_camera/second_camera/image_raw',
                 '/aruco_detect/debug', '/aruco_map/image', '/aruco_map/debug',
                 '/optical_flow/debug', '/main_camera/image_raw_throttled']
MAX_FRAME_BYTES = 8 * 1024 * 1024


def stream_url(base, topic):
    """web_video_server convention; endpoints remain user-editable."""
    parts = urlsplit(base)
    if parts.scheme not in ('http', 'https') or not parts.hostname:
        raise ValueError('Use a complete http:// or https:// camera URL.')
    _ = parts.port  # Validate malformed or out-of-range explicit ports.
    if parts.fragment:
        raise ValueError('Camera URLs must not contain a #fragment.')
    if parts.path not in ('', '/') or parts.query:
        return base  # Explicit stream / snapshot URL is used verbatim.
    return base.rstrip('/') + '/stream?' + urlencode({'topic': topic, 'type': 'mjpeg'})


class JpegBuffer:
    """Extract JPEG frames across arbitrary multipart/chunk boundaries."""
    def __init__(self):
        self.data = bytearray()

    def feed(self, chunk):
        self.data.extend(chunk)
        frames = []
        while True:
            start = self.data.find(b'\xff\xd8')
            if start < 0:
                self.data[:] = self.data[-1:]
                break
            if start:
                del self.data[:start]
            end = self.data.find(b'\xff\xd9', 2)
            if end < 0:
                if len(self.data) > MAX_FRAME_BYTES:
                    self.data.clear()
                    raise ValueError('Camera frame exceeds 8 MB limit')
                break
            if end + 2 > MAX_FRAME_BYTES:
                self.data.clear()
                raise ValueError('Camera frame exceeds 8 MB limit')
            frames.append(bytes(self.data[:end + 2]))
            del self.data[:end + 2]
        return frames


class CameraWorker(QThread):
    def __init__(self, url, parent=None):
        super().__init__(parent)
        self.url = url
        self.cancel = threading.Event()
        self.lock = threading.Lock()
        self.latest = None
        self.status = 'Connecting…'
        self.frames = 0
        self.last_frame = 0

    def stop(self):
        # Read timeout bounds socket stalls; never wait/join from the GUI thread.
        self.cancel.set()

    def snapshot(self):
        with self.lock:
            return self.latest, self.status, self.frames, self.last_frame

    def state(self, text):
        with self.lock:
            self.status = text

    def decode(self, payload):
        buffer = QBuffer()
        buffer.setData(QByteArray(payload))
        buffer.open(QIODevice.ReadOnly)
        reader = QImageReader(buffer)
        size = reader.size()
        if (not size.isValid() or size.width() > 16384 or size.height() > 16384
                or size.width() * size.height() > 24_000_000):
            raise ValueError('Unsupported image or excessive camera resolution')
        reader.setScaledSize(size.scaled(1280, 720, Qt.KeepAspectRatio))
        image = reader.read()
        if image.isNull():
            raise ValueError('Endpoint did not return a supported image')
        # Decoding and scaling stay in this worker; retain only the latest frame.
        image = image.scaled(1280, 720, Qt.KeepAspectRatio, Qt.FastTransformation)
        with self.lock:
            self.latest = image
            self.frames += 1
            self.last_frame = time.monotonic()
            self.status = 'Live'

    def run(self):
        while not self.cancel.is_set():
            try:
                self.state('Connecting…')
                req = Request(self.url, headers={'User-Agent': 'TECHNIC-Camera/3',
                                                'Accept': 'multipart/x-mixed-replace,image/jpeg,image/png'})
                with urlopen(req, timeout=2) as response:
                    kind = response.headers.get('Content-Type', '').lower()
                    if 'text/html' in kind:
                        raise ValueError('HTML page, not an image endpoint. Use port 8080 or a direct stream URL.')
                    if 'multipart' not in kind:
                        payload = response.read(MAX_FRAME_BYTES + 1)
                        if len(payload) > MAX_FRAME_BYTES:
                            raise ValueError('Snapshot exceeds 8 MB limit')
                        self.decode(payload)
                    else:
                        parser = JpegBuffer()
                        last_decode = 0
                        # read1 returns available bytes rather than waiting for a full chunk.
                        read = getattr(response, 'read1', response.read)
                        while not self.cancel.is_set():
                            chunk = read(32768)
                            if not chunk:
                                raise ConnectionError('Camera stream ended')
                            frames = parser.feed(chunk)
                            now = time.monotonic()
                            if frames and now - last_decode >= .12:
                                self.decode(frames[-1])
                                last_decode = now
                self.cancel.wait(.15)  # Snapshot polling, at most ~6 fps.
            except Exception as exc:
                self.state('Retrying · ' + str(exc)[:180])
                self.cancel.wait(2)
        self.state('Stopped')


class CameraCanvas(QWidget):
    """Letterboxed camera with an animated standby HUD; never fake video."""
    def __init__(self):
        super().__init__()
        self.image = None
        self.phase = 0
        self.motion = True
        self.caption = 'CAMERA STANDBY'
        self.setMinimumSize(280, 136)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self.rect().adjusted(1, 1, -1, -1)
        p.fillRect(r, QColor('#050d17'))
        if self.image is not None:
            size = self.image.size().scaled(r.size(), Qt.KeepAspectRatio)
            target = QRectF((self.width()-size.width())/2, (self.height()-size.height())/2,
                            size.width(), size.height())
            p.drawImage(target, self.image)
        else:
            p.setPen(QPen(QColor('#142c40'), 1))
            for x in range(0, self.width(), 24):
                p.drawLine(x, 0, x, self.height())
            for y in range(0, self.height(), 24):
                p.drawLine(0, y, self.width(), y)
            if self.motion:
                y = int(self.phase % max(1, self.height()))
                p.setPen(QPen(QColor(98, 229, 245, 75), 2))
                p.drawLine(0, y, self.width(), y)
            p.setPen(QColor('#69889f'))
            p.setFont(QFont('Segoe UI', 9))
            p.drawText(r, Qt.AlignCenter, 'NO CAMERA FRAMES\nStart camera to connect')
        p.fillRect(0, 0, self.width(), 24, QColor(4, 12, 22, 205))
        p.setPen(QColor('#87e7e7' if self.caption == 'LIVE' else '#e7c88c'))
        p.setFont(QFont('Consolas', 8))
        p.drawText(10, 16, self.caption)
        p.setPen(QPen(QColor('#355a70'), 1))
        for x, y, sx, sy in [(1, 1, 1, 1), (self.width()-2, 1, -1, 1),
                              (1, self.height()-2, 1, -1), (self.width()-2, self.height()-2, -1, -1)]:
            p.drawLine(x, y, x+12*sx, y)
            p.drawLine(x, y, x, y+12*sy)
        p.end()


class CameraPanel(QWidget):
    def __init__(self, host, owner):
        super().__init__()
        self.owner = owner
        self.base = f'http://[{host}]:8080' if ':' in host else f'http://{host}:8080'
        self.topic = CAMERA_TOPICS[0]
        self.worker = None
        self.last_count = -1
        self.motion = True
        box = QVBoxLayout(self)
        box.setContentsMargins(8, 7, 8, 7)
        box.setSpacing(5)
        self.canvas = CameraCanvas()
        box.addWidget(self.canvas, 1)
        tools = QHBoxLayout()
        self.toggle = CommandButton('Start camera')
        self.configure = CommandButton('Configure')
        for b in (self.toggle, self.configure):
            b.setMinimumWidth(b.sizeHint().width() + 12)
            b.setCursor(Qt.PointingHandCursor)
            tools.addWidget(b)
        self.toggle.clicked.connect(self.toggle_stream)
        self.configure.clicked.connect(self.settings)
        box.addLayout(tools)
        self.note = QLabel('HTTP :8080 · main camera')
        self.note.setObjectName('Micro')
        self.note.setWordWrap(True)
        box.addWidget(self.note)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(125)

    def toggle_stream(self):
        if self.worker:
            self.stop()
        else:
            self.start()

    def start(self):
        if self.worker:
            return
        self.worker = CameraWorker(stream_url(self.base, self.topic))
        self.last_count = -1
        self.worker.start()
        self.toggle.setText('Stop camera')
        self.configure.setEnabled(False)

    def stop(self):
        if self.worker:
            self.worker.stop()
            self.owner.retiring.append(self.worker)
            self.worker = None
        self.toggle.setText('Start camera')
        self.configure.setEnabled(True)
        self.canvas.image = None
        self.canvas.caption = 'CAMERA STOPPED'
        self.canvas.update()

    def shutdown(self):
        self.stop()
        self.timer.stop()

    def refresh(self):
        if not self.isVisible():
            return
        if self.worker:
            image, status, count, stamp = self.worker.snapshot()
            fresh = bool(stamp and time.monotonic() - stamp < 3)
            if count != self.last_count:
                self.canvas.image = image
                self.last_count = count
            self.canvas.caption = 'LIVE' if fresh else ('STALE FRAME' if image is not None else 'CONNECTING')
            self.note.setText((self.topic if fresh else status)[:100])
            self.note.setToolTip(self.worker.url + '\n' + status)
        if self.motion:
            self.canvas.phase += 5
        self.canvas.motion = self.motion
        self.canvas.update()

    def settings(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('Camera stream settings')
        dialog.setMinimumWidth(520)
        layout = QFormLayout(dialog)
        hint = QLabel('Use the image server base URL, not the HTML gallery.\n'
                      'A complete MJPEG or JPEG/PNG snapshot URL can also be used.')
        hint.setWordWrap(True)
        layout.addRow(hint)
        url = QLineEdit(self.base)
        topics = QComboBox()
        topics.setEditable(True)
        topics.addItems(CAMERA_TOPICS)
        topics.setCurrentText(self.topic)
        layout.addRow('Server / direct URL', url)
        layout.addRow('ROS image topic', topics)
        error = QLabel('')
        error.setWordWrap(True)
        layout.addRow(error)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        layout.addRow(buttons)
        def save():
            try:
                stream_url(url.text().strip(), topics.currentText().strip())
            except ValueError as exc:
                error.setText(str(exc))
                return
            self.base, self.topic = url.text().strip(), topics.currentText().strip()
            self.note.setText(self.topic)
            dialog.accept()
        buttons.accepted.connect(save)
        buttons.rejected.connect(dialog.reject)
        dialog.exec_()
