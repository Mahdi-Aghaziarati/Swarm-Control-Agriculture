"""Camera parser, local HTTP transport and lifecycle tests; no external network."""
import os
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
try:
    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtCore import QBuffer, QIODevice
    from PyQt5.QtGui import QImage, QColor
    from camera import CameraWorker, CameraPanel, JpegBuffer, stream_url, MAX_FRAME_BYTES
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False


@unittest.skipUnless(QT_AVAILABLE, 'PyQt5 is not installed or cannot be loaded')
class CameraTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        image = QImage(64, 48, QImage.Format_RGB32)
        image.fill(QColor('#224466'))
        buffer = QBuffer()
        buffer.open(QIODevice.WriteOnly)
        image.save(buffer, 'JPEG')
        cls.jpeg = bytes(buffer.data())
        jpeg = cls.jpeg

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                self.send_response(200)
                if self.path == '/gallery':
                    self.send_header('Content-Type', 'text/html')
                    self.end_headers()
                    self.wfile.write(b'<html>Not a camera stream</html>')
                elif self.path == '/mjpeg':
                    self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=frame')
                    self.end_headers()
                    for _ in range(4):
                        try:
                            self.wfile.write(b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + jpeg + b'\r\n')
                            self.wfile.flush()
                        except (BrokenPipeError, ConnectionResetError):
                            return  # Expected when a stopped worker closes its socket.
                        time.sleep(.15)
                else:
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', str(len(jpeg)))
                    self.end_headers()
                    self.wfile.write(jpeg)

        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.server.daemon_threads = True
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = 'http://127.0.0.1:' + str(cls.server.server_port)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(2)

    def wait_until(self, predicate, timeout=3):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.app.processEvents()
            if predicate():
                return True
            time.sleep(.02)
        return False

    def test_stream_urls(self):
        self.assertEqual(stream_url('http://192.168.0.2:8080', '/main_camera/image_raw'),
                         'http://192.168.0.2:8080/stream?topic=%2Fmain_camera%2Fimage_raw&type=mjpeg')
        direct = self.base + '/snapshot?topic=/custom'
        self.assertEqual(stream_url(direct, '/ignored'), direct)
        self.assertIn('[::1]:8080/stream?', stream_url('http://[::1]:8080', '/image'))
        for bad in ['file:///tmp/image', 'http://', 'http://host:70000', 'http://host/#bad']:
            with self.assertRaises(ValueError):
                stream_url(bad, '/image')

    def test_multipart_split_and_bounded_buffer(self):
        parser = JpegBuffer()
        payload = b'--boundary\r\n' + self.jpeg + b'\r\n' + self.jpeg
        frames = []
        for n in range(0, len(payload), 7):
            frames.extend(parser.feed(payload[n:n+7]))
        self.assertEqual(frames, [self.jpeg, self.jpeg])
        parser.feed(b'garbage' * 10000)
        self.assertLessEqual(len(parser.data), 1)
        with self.assertRaises(ValueError):
            parser.feed(b'\xff\xd8' + b'x' * MAX_FRAME_BYTES)
        self.assertFalse(parser.data)

    def test_real_local_http_snapshots_and_mjpeg(self):
        for path in ['/snapshot', '/mjpeg']:
            worker = CameraWorker(self.base + path)
            worker.start()
            try:
                self.assertTrue(self.wait_until(lambda: worker.snapshot()[2] > 0))
                image, status, count, stamp = worker.snapshot()
                self.assertFalse(image.isNull())
                self.assertGreater(count, 0)
                self.assertGreater(stamp, 0)
                self.assertLessEqual(image.width(), 1280)
            finally:
                worker.stop()
                self.assertTrue(worker.wait(4000))

    def test_html_is_not_displayed_as_video(self):
        worker = CameraWorker(self.base + '/gallery')
        worker.start()
        try:
            self.assertTrue(self.wait_until(lambda: 'HTML page' in worker.snapshot()[1]))
            self.assertEqual(worker.snapshot()[2], 0)
            self.assertIsNone(worker.snapshot()[0])
        finally:
            worker.stop()
            self.assertTrue(worker.wait(4000))

    def test_ipv6_panel_and_nonblocking_stop(self):
        owner = SimpleNamespace(retiring=[])
        panel = CameraPanel('::1', owner)
        self.assertEqual(panel.base, 'http://[::1]:8080')
        panel.base = self.base + '/snapshot'
        panel.show()
        try:
            panel.start()
            worker = panel.worker
            panel.start()  # Do not spawn duplicate camera workers.
            self.assertIs(panel.worker, worker)
            self.assertTrue(self.wait_until(lambda: worker.snapshot()[2] > 0))
            panel.refresh()
            self.assertEqual(panel.canvas.caption, 'LIVE')
            self.assertIsNotNone(panel.canvas.image)
            panel.stop()
            self.assertIsNone(panel.canvas.image)
            self.assertIsNone(panel.worker)
            self.assertIn(worker, owner.retiring)
            self.assertTrue(worker.wait(4000))
        finally:
            panel.shutdown()
            panel.close()


if __name__ == '__main__':
    unittest.main()
