"""Transport logic tests; a QThread stub is used only when Qt is unavailable.
These tests do not validate the GUI or real ROS devices.
"""
import importlib.util
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

try:
    from PyQt5.QtCore import QThread
    from connection import DroneConnection
except ImportError:
    qt = types.ModuleType('PyQt5')
    core = types.ModuleType('PyQt5.QtCore')
    core.QThread = type('QThread', (), {})
    qt.QtCore = core
    spec = importlib.util.spec_from_file_location('transport_under_test', Path(__file__).with_name('connection.py'))
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {'PyQt5': qt, 'PyQt5.QtCore': core}):
        spec.loader.exec_module(module)
    DroneConnection = module.DroneConnection


class TransportTests(unittest.TestCase):
    def test_bounded_log_and_truncation(self):
        worker = DroneConnection('127.0.0.1', 9090)
        for _ in range(2010):
            worker._log('x' * 5000)
        lines = worker.drain_logs(2000)
        self.assertIn('10 old messages discarded', lines[0])
        self.assertEqual(len(lines), 2001)
        self.assertTrue(lines[1].endswith('[truncated]'))
        self.assertEqual(worker.drain_logs(), [])

    def test_connection_subscriptions_receive_and_cleanup(self):
        worker = DroneConnection('127.0.0.1', 9090)
        worker.subscribe('/mavros/state')
        class Socket:
            def __init__(self):
                self.sent = []
                self.messages = iter(['not json', json.dumps({'topic': '/mavros/battery', 'msg': {'voltage': 12.3, 'percentage': .5}})])
                self.closed = False
            def settimeout(self, value):
                pass
            def send(self, text):
                self.sent.append(json.loads(text))
            def recv(self):
                try:
                    return next(self.messages)
                except StopIteration:
                    self.snapshot = worker.snapshot()
                    worker.stop()
                    return ''
            def shutdown(self):
                self.closed = True
        ws = Socket()
        namespace = sys.modules.get(DroneConnection.__module__)
        if namespace is None:
            namespace = module
        with patch.object(namespace.websocket, 'create_connection', return_value=ws):
            worker.run()
        self.assertEqual(ws.snapshot['battery'], '12.3 V (50%)')
        self.assertEqual(ws.snapshot['received'], 2)
        self.assertEqual(worker.snapshot()['received'], 2)  # retained on disconnect
        self.assertTrue(ws.closed)
        self.assertFalse(worker.snapshot()['online'])
        self.assertEqual({m['topic'] for m in ws.sent}, {'/mavros/battery', '/mavros/altitude', '/mavros/state'})
        self.assertTrue(any('not json' in line for line in worker.drain_logs()))

    def test_subscriptions_deduplicated_and_defaults_protected(self):
        worker = DroneConnection('127.0.0.1', 9090)
        worker.subscribe('/mavros/state')
        worker.subscribe('/mavros/state')
        worker.unsubscribe('/mavros/battery')
        worker.unsubscribe('/mavros/altitude')
        worker.unsubscribe('/mavros/state')
        worker.unsubscribe('/not-subscribed')
        sent = []
        ws = types.SimpleNamespace(send=lambda text: sent.append(json.loads(text)))
        worker._apply_requests(ws)
        self.assertEqual([(x['op'], x['topic']) for x in sent],
                         [('subscribe', '/mavros/state'), ('unsubscribe', '/mavros/state')])
        self.assertEqual(worker._topics, {'/mavros/battery', '/mavros/altitude'})


if __name__ == '__main__':
    unittest.main()
