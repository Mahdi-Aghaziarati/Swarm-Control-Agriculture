"""Headless UI smoke tests. Skipped when PyQt5 is not installed.
Run: QT_QPA_PLATFORM=offscreen python -m unittest -v test_ui.py
No drone or network access is needed; workers are mocked.
"""
import contextlib
import io
import os
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
try:
    from PyQt5.QtWidgets import QApplication, QMessageBox
    from PyQt5.QtCore import QTimer
    from PyQt5.QtGui import QImage
    from main import TechnicCommandCenter, ASSETS
    from theme import STYLE
    from visuals import LaunchScreen
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False


@unittest.skipUnless(QT_AVAILABLE, 'PyQt5 is not installed')
class DashboardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setStyleSheet(STYLE.replace('assets/', ASSETS.replace('\\', '/') + '/'))

    def setUp(self):
        self.window = TechnicCommandCenter()
        self.window.timer.stop()
        self.window.hero.artwork.set_motion(False)
        self.worker_patch = patch('main.DroneConnection')
        self.worker = self.worker_patch.start().return_value
        self.worker.snapshot.return_value = {'online': True, 'battery': '12.0 V',
                                             'altitude': '1.50 m', 'received': 3}
        self.worker.drain_logs.return_value = ['{"topic":"/mavros/state","msg":{"armed":false}}']
        self.worker.isRunning.return_value = False
        self.window.show()
        self.app.processEvents()

    def tearDown(self):
        self.window.close()
        self.app.processEvents()
        self.worker_patch.stop()

    def test_one_leader_and_multiple_children(self):
        self.window.register_drone('127.0.0.1', 9090, 'leader')
        with patch.object(QMessageBox, 'warning') as warning:
            self.window.register_drone('127.0.0.2', 9090, 'leader')
            warning.assert_called_once()
        self.window.register_drone('127.0.0.2', 9090, 'child')
        self.window.register_drone('127.0.0.3', 9090, 'child')
        self.assertEqual(len(self.window.drones), 3)
        self.assertEqual(self.window.tables['leader'].rowCount(), 1)
        self.assertEqual(self.window.tables['child'].rowCount(), 2)
        self.assertFalse(self.window.inputs['leader'][2].isEnabled())
        self.assertTrue(all(b.isEnabled() for b in self.window.leader_buttons))
        self.window.select_all(False)
        self.assertEqual(self.window.selected(), [])
        self.window.select_all(True)
        self.assertEqual(len(self.window.selected()), 3)

    def test_invalid_and_duplicate_addresses(self):
        with patch.object(QMessageBox, 'warning') as warning:
            self.window.register_drone('invalid', 9090, 'child')
            self.assertEqual(warning.call_count, 1)
        self.assertFalse(self.window.drones)
        self.window.register_drone('::1', 9090, 'child')
        self.assertIn('[::1]:9090', self.window.drones)
        with patch.object(QMessageBox, 'warning') as warning:
            self.window.register_drone('::1', 9090, 'child')
            warning.assert_called_once()
        self.assertEqual(len(self.window.drones), 1)

    def test_stream_metrics_pause_and_inspector(self):
        self.window.register_drone('127.0.0.1', 9090, 'leader')
        self.assertIn('/mavros/state', self.window.log.toPlainText())
        self.assertEqual(self.window.received_total, 3)
        self.window.refresh()
        self.assertEqual(self.window.received_total, 3)  # no double count
        self.assertEqual(self.window.metrics[1].value.text(), '1')
        self.window.pause_logs.setChecked(True)
        self.window.log.clear()
        self.window.refresh()
        self.assertEqual(self.window.log.toPlainText(), '')
        self.window.inspect('127.0.0.1:9090')
        inspector = self.window.inspectors['127.0.0.1:9090']
        inspector.inspect(inspector.topics.item(0))
        self.worker.subscribe.assert_called_once()
        inspector.close()
        self.assertFalse(self.window.inspectors)

    def test_leader_commands_and_removal(self):
        self.window.register_drone('127.0.0.1', 9090, 'leader')
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            for b in self.window.leader_buttons:
                b.click()
        for text in ['Scan area', 'Return to nest', 'Immediate land']:
            self.assertIn(text, output.getvalue())
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.Yes):
            self.window.delete_drone('127.0.0.1:9090')
        self.assertIsNone(self.window.leader)
        self.assertEqual(self.window.tables['leader'].rowCount(), 0)
        self.assertTrue(self.window.inputs['leader'][2].isEnabled())
        self.assertFalse(any(b.isEnabled() for b in self.window.leader_buttons))
        self.worker.stop.assert_called_once()

    def test_camera_rows_and_full_button_labels_at_minimum_size(self):
        self.window.register_drone('127.0.0.1', 9090, 'leader')
        self.window.register_drone('127.0.0.2', 9090, 'child')
        self.window.resize(1080, 720)
        self.app.processEvents()
        for endpoint, info in self.window.drones.items():
            table = self.window.tables[info['role']]
            self.assertIs(table.cellWidget(table.row(info['items'][0]), 2), info['camera'])
            self.assertGreaterEqual(table.columnWidth(2), 350)
            self.assertEqual(info['camera'].base, 'http://' + endpoint.split(':')[0] + ':8080')
            self.assertIsNone(info['camera'].worker)  # No surprise network connection.
        for control in self.window.leader_buttons:
            self.assertGreaterEqual(control.width(), control.sizeHint().width())
        self.window.set_motion(False)
        self.assertFalse(self.window.topology.timer.isActive())
        self.assertTrue(all(not info['camera'].motion for info in self.window.drones.values()))
        self.window.set_motion(True)
        self.assertTrue(self.window.topology.timer.isActive())

    def test_artwork_splash_and_navigation_render(self):
        self.window.navigate(0)
        self.window.navigate(1)
        self.window.navigate(2)
        self.window.hero.artwork.advance()
        self.window.chart.push(10)
        self.app.processEvents()
        self.assertFalse(self.window.grab().isNull())
        splash = LaunchScreen()
        splash.show()
        self.app.processEvents()
        splash.tick()
        self.assertFalse(splash.grab().isNull())
        splash.timer.stop()
        splash.artwork.set_motion(False)
        splash.close()


if __name__ == '__main__':
    unittest.main()
