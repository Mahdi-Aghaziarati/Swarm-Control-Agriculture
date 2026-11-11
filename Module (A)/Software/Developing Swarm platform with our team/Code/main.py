"""TECHNIC flight workspace. All command buttons are print-only demo actions."""
import sys
import os
import time
import ipaddress
import json
from datetime import datetime
from PyQt5.QtCore import Qt, QTimer, QDateTime
from PyQt5.QtGui import QColor, QTextCursor, QFont, QIcon
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QLineEdit, QSpinBox, QDoubleSpinBox, QCheckBox, QMessageBox,
    QPlainTextEdit, QScrollArea, QSplitter, QDialog, QListWidget,
    QAbstractItemView, QButtonGroup,
)
import actions
from connection import DroneConnection
from topics import DEFAULT_TOPICS_LIST
from theme import STYLE
from visuals import HeroCard, MetricCard, TrafficChart, LaunchScreen, label
from camera import CameraPanel
from effects import CommandButton, FleetTopology, DeviceTable

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')


def button(text, callback, name=None):
    b = CommandButton(text)
    b.setCursor(Qt.PointingHandCursor)
    if name:
        b.setObjectName(name)
    b.clicked.connect(callback)
    return b


def panel(title, leader=False):
    frame = QFrame()
    frame.setObjectName('Leader' if leader else 'Panel')
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(16, 14, 16, 14)
    layout.setSpacing(10)
    layout.addWidget(label(title, 'Heading'))
    return frame, layout


class TopicInspector(QDialog):
    def __init__(self, window, endpoint):
        super().__init__(window)
        self.window, self.endpoint = window, endpoint
        self.topic = None
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowTitle(f'Topic inspector — {endpoint}')
        self.resize(850, 600)
        layout = QVBoxLayout(self)
        layout.addWidget(label('TOPIC INSPECTOR', 'PageTitle'))
        layout.addWidget(label(endpoint, 'Muted'))
        self.search = QLineEdit()
        self.search.setPlaceholderText('Filter topics…')
        layout.addWidget(self.search)
        self.topics = QListWidget()
        self.topics.addItems(DEFAULT_TOPICS_LIST)
        layout.addWidget(self.topics)
        self.search.textChanged.connect(self.filter_topics)
        self.topics.itemDoubleClicked.connect(self.inspect)
        hint = label('Double-click to subscribe. Messages also appear in the live stream.', 'Muted')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setPlaceholderText('Select a topic to view its latest message.')
        self.output.document().setMaximumBlockCount(500)
        layout.addWidget(self.output)

    def filter_topics(self, text):
        for i in range(self.topics.count()):
            item = self.topics.item(i)
            item.setHidden(text.lower() not in item.text().lower())

    def inspect(self, item):
        info = self.window.drones.get(self.endpoint)
        if not info:
            return
        worker = info['worker']
        if self.topic:
            worker.unsubscribe(self.topic)
        self.topic = item.text()
        self.output.setPlainText(f'Waiting for {self.topic}…')
        worker.subscribe(self.topic)

    def receive(self, lines):
        if not self.topic:
            return
        latest = None
        for line in lines:
            try:
                data = json.loads(line)
                if isinstance(data, dict) and data.get('topic') == self.topic:
                    latest = data.get('msg', data)
            except ValueError:
                pass
        if latest is not None:
            self.output.setPlainText(json.dumps(latest, ensure_ascii=False, indent=2))

    def closeEvent(self, event):
        info = self.window.drones.get(self.endpoint)
        if info and self.topic:
            info['worker'].unsubscribe(self.topic)
        self.window.inspectors.pop(self.endpoint, None)
        super().closeEvent(event)


class TechnicCommandCenter(QMainWindow):
    def __init__(self):
        super().__init__()
        self.drones, self.inspectors = {}, {}
        self.retiring = []
        self.leader = None
        self.closing = False
        self.received_total = 0
        self.sample_count = 0
        self.sample_time = time.monotonic()
        self.motion_enabled = True
        self.setWindowTitle('TECHNIC — Flight Operations Workspace')
        self.resize(1500, 1000)
        self.setMinimumSize(1080, 720)
        root = QWidget()
        root.setObjectName('Workspace')
        self.setCentralWidget(root)
        shell = QHBoxLayout(root)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)
        self.build_rail(shell)
        workspace = QVBoxLayout()
        workspace.setContentsMargins(22, 18, 22, 16)
        workspace.setSpacing(16)
        shell.addLayout(workspace, 1)
        header = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(3)
        titles.addWidget(label('Operations overview', 'PageTitle'))
        titles.addWidget(label('COMMAND CENTER   /   FLEET WORKSPACE', 'Micro'))
        header.addLayout(titles)
        header.addStretch()
        header.addWidget(label('PRINT-ONLY DEMO', 'Badge'))
        header.addSpacing(14)
        self.clock = label('', 'Muted')
        header.addWidget(self.clock)
        workspace.addLayout(header)

        self.vertical_split = QSplitter(Qt.Vertical)
        workspace.addWidget(self.vertical_split, 1)
        self.upper = QSplitter(Qt.Horizontal)
        self.vertical_split.addWidget(self.upper)
        self.overview_scroll = QScrollArea()
        self.overview_scroll.setWidgetResizable(True)
        self.overview_scroll.setMinimumWidth(540)
        self.upper.addWidget(self.overview_scroll)
        content = QWidget()
        content.setObjectName('Workspace')
        self.overview_scroll.setWidget(content)
        overview = QVBoxLayout(content)
        overview.setContentsMargins(0, 0, 8, 0)
        overview.setSpacing(14)
        self.hero = HeroCard()
        overview.addWidget(self.hero)
        metrics = QHBoxLayout()
        metrics.setSpacing(12)
        self.metrics = [MetricCard('REGISTERED', 'Devices in workspace'),
                        MetricCard('ONLINE', 'Active WebSocket links', '#60e6bb'),
                        MetricCard('SELECTED', 'Current command scope', '#b29aff'),
                        MetricCard('RX / SECOND', 'Incoming messages', '#f1c87d')]
        for metric in self.metrics:
            metrics.addWidget(metric)
        overview.addLayout(metrics)
        self.topology = FleetTopology()
        overview.addWidget(self.topology)
        self.tables, self.inputs = {}, {}
        self.fleet_frames = {}
        for role, title in [('leader', '01   /   LEADER NODE'), ('child', '02   /   CHILD FLEET')]:
            frame, box = panel(title, role == 'leader')
            self.fleet_frames[role] = frame
            note = 'Single coordinator · one device maximum' if role == 'leader' else 'Multiple devices · select the targets for each demo action'
            box.addWidget(label(note, 'Muted'))
            add = QHBoxLayout()
            ip = QLineEdit('10.42.0.1' if role == 'leader' else '10.42.0.2')
            ip.setPlaceholderText('IPv4 / IPv6 address')
            ip.setMinimumWidth(100)
            port = QSpinBox()
            port.setRange(1, 65535)
            port.setValue(9090)
            port.setMinimumWidth(82)
            add_button = button('+ Add leader' if role == 'leader' else '+ Add child',
                                lambda _, r=role: self.add_from_input(r),
                                'LeaderButton' if role == 'leader' else 'Primary')
            add.addWidget(label('HOST', 'Micro'))
            add.addWidget(ip, 1)
            add.addWidget(label('PORT', 'Micro'))
            add.addWidget(port)
            add.addWidget(add_button)
            box.addLayout(add)
            self.inputs[role] = (ip, port, add_button)
            table = DeviceTable(0, 3)
            table.setHorizontalHeaderLabels(['SELECT', 'DEVICE / LIVE TELEMETRY', 'LIVE CAMERA'])
            table.setEditTriggers(QAbstractItemView.NoEditTriggers)
            table.setSelectionBehavior(QAbstractItemView.SelectRows)
            table.setAlternatingRowColors(True)
            table.setShowGrid(False)
            # Cell-widget button sizes are NOT included by ResizeToContents.
            # Explicit minima keep their full labels visible at any DPI.
            header = table.horizontalHeader()
            header.setSectionResizeMode(QHeaderView.ResizeToContents)
            for col, width in [(1, 254), (2, 350)]:
                header.setSectionResizeMode(col, QHeaderView.Interactive)
                table.setColumnWidth(col, width)
            header.setSectionResizeMode(2, QHeaderView.Fixed)
            header.setMinimumSectionSize(64)
            table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
            table.verticalHeader().hide()
            table.verticalHeader().setDefaultSectionSize(242)
            table.setMinimumHeight(96)
            table.setMaximumHeight(110)
            table.setToolTip('Live telemetry and HTTP camera per device. Scroll horizontally for all columns.')
            box.addWidget(table)
            self.tables[role] = table
            if role == 'child':
                select = QHBoxLayout()
                select.addWidget(button('Select all devices', lambda: self.select_all(True)))
                select.addWidget(button('Clear selection', lambda: self.select_all(False)))
                select.addStretch()
                box.addLayout(select)
            overview.addWidget(frame)
        traffic, traffic_layout = panel('NETWORK ACTIVITY   /   LIVE RX')
        self.traffic_note = label('0 received · actual WebSocket messages, not flight telemetry', 'Muted')
        traffic_layout.addWidget(self.traffic_note)
        self.chart = TrafficChart()
        traffic_layout.addWidget(self.chart)
        overview.addWidget(traffic)
        overview.addStretch()

        deck_scroll = QScrollArea()
        deck_scroll.setWidgetResizable(True)
        deck_scroll.setMinimumWidth(330)
        deck_scroll.setMaximumWidth(410)
        self.upper.addWidget(deck_scroll)
        deck = QWidget()
        deck.setObjectName('Deck')
        deck_scroll.setWidget(deck)
        controls = QVBoxLayout(deck)
        controls.setContentsMargins(4, 0, 3, 0)
        controls.setSpacing(14)
        title = QHBoxLayout()
        title.addWidget(label('COMMAND DECK', 'Heading'))
        title.addStretch()
        title.addWidget(label('DEMO', 'Badge'))
        controls.addLayout(title)
        # Leader commands deliberately come first, before all other controls.
        frame, box = panel('01   /   LEADER COMMANDS', True)
        box.addWidget(label('Dedicated coordinator control', 'Muted'))
        self.leader_label = label('No leader registered', 'Muted')
        self.leader_label.setWordWrap(True)
        box.addWidget(self.leader_label)
        self.leader_buttons = []
        for text, fn in [('Scan area', actions.scan_area),
                         ('Return to nest', actions.return_to_nest),
                         ('Immediate land', actions.immediate_land)]:
            b = button(text, lambda _, f=fn: self.leader_action(f), 'LeaderButton')
            b.setToolTip('Demo only: prints the operation to the terminal.')
            self.leader_buttons.append(b)
            box.addWidget(b)
        controls.addWidget(frame)
        frame, box = panel('02   /   SHOW SEQUENCE')
        self.delay = QSpinBox()
        self.delay.setRange(0, 3600)
        self.delay.setValue(0)
        self.delay.setSuffix(' s')
        box.addWidget(label('Start delay · placeholder only', 'Muted'))
        box.addWidget(self.delay)
        box.addWidget(button('Preflight check', lambda: actions.preflight_check(self.selected())))
        box.addWidget(button('Start sequence', lambda: actions.start_animation(self.selected(), self.delay.value())))
        box.addWidget(button('Pause / Resume sequence', lambda: actions.pause_resume(self.selected())))
        controls.addWidget(frame)
        frame, box = panel('03   /   FLIGHT CONTROL')
        box.addWidget(label('Scope: selected devices · demo only', 'Muted'))
        self.altitude = QDoubleSpinBox()
        self.altitude.setRange(0.1, 100)
        self.altitude.setValue(1.5)
        self.altitude.setSuffix(' m')
        box.addWidget(self.altitude)
        box.addWidget(button('Takeoff', lambda: actions.takeoff(self.selected(), self.altitude.value())))
        for text, fn in [('Land selected', actions.land_selected),
                         ('Disarm selected', actions.disarm_selected),
                         ('Test LEDs', actions.test_leds), ('Flip', actions.flip)]:
            box.addWidget(button(text, lambda _, f=fn: f(self.selected())))
        controls.addWidget(frame)
        frame, box = panel('04   /   SAFETY COMMANDS')
        hint = label('ALL targets every registered device.\nEmergency land targets selected devices.\nThese buttons do NOT send flight commands.', 'Muted')
        hint.setWordWrap(True)
        box.addWidget(hint)
        box.addWidget(button('Land ALL', lambda: actions.land_all(list(self.drones)), 'Danger'))
        box.addWidget(button('Disarm ALL', lambda: actions.disarm_all(list(self.drones)), 'Danger'))
        box.addWidget(button('Emergency land', lambda: actions.emergency_land(self.selected()), 'Danger'))
        controls.addWidget(frame)
        controls.addStretch()
        self.upper.setSizes([900, 350])

        self.log_frame, log_layout = panel('LIVE STREAM   /   WEBSOCKET CONSOLE')
        tools = QHBoxLayout()
        self.pause_logs = QCheckBox('Pause display')
        self.pause_logs.setToolTip('Paused messages are discarded from the display; connections remain active.')
        tools.addWidget(self.pause_logs)
        tools.addWidget(button('Clear', lambda: self.log.clear()))
        tools.addStretch()
        self.log_state = label('●  LISTENING', 'Micro')
        tools.addWidget(self.log_state)
        log_layout.addLayout(tools)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setPlaceholderText('Waiting for a connection. Add a leader or child to receive WebSocket messages…')
        self.log.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.log.document().setMaximumBlockCount(3000)
        log_layout.addWidget(self.log)
        self.log_frame.setMinimumHeight(155)
        self.vertical_split.addWidget(self.log_frame)
        self.vertical_split.setSizes([720, 200])
        self.vertical_split.setCollapsible(0, False)
        footer = QHBoxLayout()
        footer.addWidget(label('●  LOCAL WORKSPACE', 'Micro'))
        footer.addStretch()
        footer.addWidget(label('No flight commands are transmitted  /  Artwork is illustrative', 'Micro'))
        workspace.addLayout(footer)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(100)
        self.refresh()

    def build_rail(self, shell):
        rail = QFrame()
        rail.setObjectName('Rail')
        rail.setFixedWidth(176)
        box = QVBoxLayout(rail)
        box.setContentsMargins(15, 22, 15, 20)
        box.setSpacing(8)
        box.addWidget(label('T /', 'BrandMark'))
        box.addWidget(label('TECHNIC', 'Brand'))
        box.addWidget(label('FLIGHT SYSTEMS', 'Micro'))
        box.addSpacing(36)
        box.addWidget(label('WORKSPACE', 'Micro'))
        self.nav = QButtonGroup(self)
        for i, (text, icon) in enumerate([('Overview', 'overview'), ('Fleet nodes', 'fleet'), ('Live stream', 'stream')]):
            b = button(text, lambda _, n=i: self.navigate(n), 'Nav')
            b.setIcon(QIcon(os.path.join(ASSETS, icon + '.svg')))
            b.setCheckable(True)
            self.nav.addButton(b, i)
            box.addWidget(b)
            if i == 0:
                b.setChecked(True)
        box.addStretch()
        box.addWidget(label('PREFERENCES', 'Micro'))
        motion = QCheckBox('Visual motion')
        motion.setChecked(True)
        motion.toggled.connect(self.set_motion)
        box.addWidget(motion)
        box.addSpacing(16)
        note = label('DEMO MODE\nCommands print to\nthe terminal only.', 'Muted')
        note.setWordWrap(True)
        box.addWidget(note)
        box.addSpacing(12)
        box.addWidget(label('WORKSPACE  /  02', 'Micro'))
        shell.addWidget(rail)

    def set_motion(self, enabled):
        self.motion_enabled = enabled
        self.hero.artwork.set_motion(enabled)
        self.topology.set_motion(enabled)
        for info in self.drones.values():
            info['camera'].motion = enabled

    def resize_table(self, table):
        height = min(640, 62 + table.rowCount() * 242) if table.rowCount() else 100
        table.setMinimumHeight(height)
        table.setMaximumHeight(height)

    def navigate(self, index):
        if index == 0:
            self.overview_scroll.verticalScrollBar().setValue(0)
        elif index == 1:
            self.overview_scroll.ensureWidgetVisible(self.fleet_frames['child'], 0, 12)
            self.inputs['child'][0].setFocus()
        else:
            self.log_frame.show()
            self.vertical_split.setSizes([max(300, self.height() - 350), 220])
            self.log.setFocus()

    def add_from_input(self, role):
        ip, port, _ = self.inputs[role]
        self.register_drone(ip.text().strip(), port.value(), role)

    def register_drone(self, ip, port, role):
        if role not in self.tables:
            raise ValueError('Role must be leader or child')
        try:
            address = ipaddress.ip_address(ip)
        except ValueError:
            QMessageBox.warning(self, 'Invalid address', 'Enter a valid IPv4 or IPv6 address.')
            return
        ip = str(address)
        host = f'[{ip}]' if address.version == 6 else ip
        endpoint = f'{host}:{port}'
        if role == 'leader' and self.leader:
            QMessageBox.warning(self, 'Leader limit', 'Only one leader is allowed. Remove the current leader first.')
            return
        if endpoint in self.drones:
            QMessageBox.warning(self, 'Duplicate endpoint', 'This host and port are already registered.')
            return
        worker = DroneConnection(host, port)
        table = self.tables[role]
        row = table.rowCount()
        table.insertRow(row)
        check = QCheckBox()
        check.setChecked(True)
        check.setToolTip('Include this device in selected-device actions')
        table.setCellWidget(row, 0, check)
        items = [QTableWidgetItem(t) for t in [endpoint, 'CONNECTING', '--', '--', str(len(DEFAULT_TOPICS_LIST))]]
        # Keep the endpoint item as the stable row identity beneath the device card.
        table.setItem(row, 1, items[0])
        card = QWidget()
        card.setObjectName('DeviceCard')
        detail = QVBoxLayout(card)
        detail.setContentsMargins(12, 12, 12, 12)
        detail.setSpacing(8)
        detail.addWidget(label('LEADER / COORDINATOR' if role == 'leader' else 'CHILD / FLEET MEMBER', 'Eyebrow'))
        endpoint_label = label(endpoint, 'DeviceTitle')
        endpoint_label.setWordWrap(True)
        detail.addWidget(endpoint_label)
        link = label('CONNECTING', 'Micro')
        detail.addWidget(link)
        battery = label('Battery  --', 'Muted')
        altitude = label('Altitude  --', 'Muted')
        detail.addWidget(battery)
        detail.addWidget(altitude)
        detail.addWidget(label(f'{len(DEFAULT_TOPICS_LIST)} available topics', 'Micro'))
        commands = QHBoxLayout()
        commands.setSpacing(8)
        for text, callback in [('Inspect', lambda: self.inspect(endpoint)),
                               ('Remove', lambda: self.delete_drone(endpoint))]:
            action = button(text, callback)
            commands.addWidget(action)
        detail.addLayout(commands)
        detail.addStretch()
        table.setCellWidget(row, 1, card)
        table.setColumnWidth(1, max(254, card.minimumSizeHint().width() + 8))
        camera = CameraPanel(host, self)
        camera.motion = self.motion_enabled
        table.setCellWidget(row, 2, camera)
        self.resize_table(table)
        self.drones[endpoint] = dict(worker=worker, role=role, check=check, items=items, last_rx=0,
                                     camera=camera, telemetry=(link, battery, altitude))
        if role == 'leader':
            self.leader = endpoint
        worker.start()
        self.refresh()

    def inspect(self, endpoint):
        if endpoint in self.inspectors:
            self.inspectors[endpoint].raise_()
            self.inspectors[endpoint].activateWindow()
            return
        dialog = TopicInspector(self, endpoint)
        self.inspectors[endpoint] = dialog
        dialog.show()

    def delete_drone(self, endpoint):
        if QMessageBox.question(self, 'Remove device', f'Remove {endpoint} from this workspace?') != QMessageBox.Yes:
            return
        if endpoint in self.inspectors:
            self.inspectors[endpoint].close()
        info = self.drones.pop(endpoint)
        table = self.tables[info['role']]
        info['camera'].shutdown()
        table.removeRow(table.row(info['items'][0]))
        self.resize_table(table)
        if self.leader == endpoint:
            self.leader = None
        self.retiring.append(info['worker'])
        info['worker'].stop()
        self.refresh()

    def selected(self):
        return [key for key, value in self.drones.items() if value['check'].isChecked()]

    def select_all(self, state):
        for info in self.drones.values():
            info['check'].setChecked(state)

    def leader_action(self, function):
        if self.leader in self.drones:
            function(self.leader)

    def refresh(self):
        self.clock.setText(QDateTime.currentDateTime().toString('dd MMM yyyy  /  HH:mm:ss'))
        self.retiring[:] = [w for w in self.retiring if w.isRunning()]
        online = 0
        batch = []
        stamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        for endpoint, info in self.drones.items():
            snapshot = info['worker'].snapshot()
            online += int(snapshot['online'])
            received = snapshot.get('received', 0)
            self.received_total += max(0, received - info['last_rx'])
            info['last_rx'] = received
            values = ['ONLINE' if snapshot['online'] else 'OFFLINE', snapshot['battery'], snapshot['altitude']]
            for item, value in zip(info['items'][1:4], values):
                if item.text() != value:
                    item.setText(value)
            info['items'][1].setForeground(QColor('#60e6bb' if snapshot['online'] else '#ed8ca5'))
            link, battery, altitude = info['telemetry']
            link.setText('●  ' + values[0] + '  /  WEBSOCKET')
            link.setStyleSheet('color: ' + ('#60e6bb' if snapshot['online'] else '#ed8ca5') + ';')
            battery.setText('Battery   ' + str(snapshot['battery']))
            altitude.setText('Altitude   ' + str(snapshot['altitude']))
            lines = info['worker'].drain_logs(limit=max(5, 200 // max(1, len(self.drones))))
            if endpoint in self.inspectors:
                self.inspectors[endpoint].receive(lines)
            if not self.pause_logs.isChecked():
                batch.extend(f'[{stamp}] [{endpoint}] {line}' for line in lines)
        if batch:
            bar = self.log.verticalScrollBar()
            at_bottom = bar.value() >= bar.maximum() - 2
            cursor = QTextCursor(self.log.document())
            cursor.movePosition(QTextCursor.End)
            cursor.insertText('\n'.join(batch) + '\n')
            if at_bottom:
                bar.setValue(bar.maximum())
        now = time.monotonic()
        elapsed = now - self.sample_time
        if elapsed >= 1:
            rate = (self.received_total - self.sample_count) / elapsed
            self.chart.push(rate)
            self.metrics[3].value.setText(f'{rate:.0f}')
            self.sample_count, self.sample_time = self.received_total, now
        for metric, value in zip(self.metrics, [len(self.drones), online, len(self.selected())]):
            metric.value.setText(str(value))
        self.traffic_note.setText(f'{self.received_total:,} received · actual WebSocket messages, not flight telemetry')
        self.log_state.setText('Ⅱ  DISPLAY PAUSED' if self.pause_logs.isChecked() else f'●  LISTENING  /  {online} LINKS')
        self.hero.status.setText(f'●  {online} LINKS ONLINE     /     {len(self.drones)} REGISTERED DEVICES' if self.drones
                                 else '●  WORKSPACE READY     /     AWAITING CONNECTIONS')
        self.topology.nodes = [(key, info['role'], info['items'][1].text() == 'ONLINE')
                               for key, info in self.drones.items()]
        self.topology.update()
        self.inputs['leader'][2].setEnabled(self.leader is None)
        self.leader_label.setText(self.leader or 'No leader registered')
        for b in self.leader_buttons:
            b.setEnabled(self.leader is not None)

    def closeEvent(self, event):
        # Poll completion instead of blocking Qt with worker.wait().
        # Stop cameras first so their workers enter the same nonblocking retirement path.
        for info in self.drones.values():
            info['camera'].shutdown()
        workers = [i['worker'] for i in self.drones.values()] + self.retiring
        if any(w.isRunning() for w in workers):
            event.ignore()
            if not self.closing:
                self.closing = True
                self.centralWidget().setEnabled(False)
                for dialog in list(self.inspectors.values()):
                    dialog.close()
                for worker in workers:
                    worker.stop()
            QTimer.singleShot(100, self.close)
            return
        self.timer.stop()
        self.hero.artwork.set_motion(False)
        self.topology.set_motion(False)
        event.accept()


def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setApplicationName('TECHNIC')
    app.setStyle('Fusion')
    app.setFont(QFont('Segoe UI', 10))
    # Absolute paths keep SVG resources working from any launch directory.
    app.setStyleSheet(STYLE.replace('assets/', ASSETS.replace('\\', '/') + '/'))
    app.setWindowIcon(QIcon(os.path.join(ASSETS, 'app.svg')))
    splash = LaunchScreen()
    screen = app.primaryScreen()
    if screen:
        splash.move(screen.availableGeometry().center() - splash.rect().center())
    splash.show()
    window = TechnicCommandCenter()

    def open_workspace():
        window.show()
        splash.timer.stop()
        splash.artwork.set_motion(False)
        splash.close()

    # A visual introduction only, not a simulated connection or safety check.
    QTimer.singleShot(2000, open_workspace)
    return app.exec_()


if __name__ == '__main__':
    sys.exit(main())
