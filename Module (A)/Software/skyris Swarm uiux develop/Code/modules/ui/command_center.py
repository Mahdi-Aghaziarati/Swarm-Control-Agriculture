"""Native presentation layer. No transport, command handlers or model mutations.

The original widgets/QActions are moved, never replaced. horizontalLayout remains
an insertion target for server.py's CopterTableWidget. All assets are local.
"""
import math
from pathlib import Path
from PyQt5 import QtCore, QtGui, QtWidgets

ASSETS = Path(__file__).resolve().parent / 'assets'


def label(text, name='muted'):
    item = QtWidgets.QLabel(text)
    item.setObjectName(name)
    return item


def card(title, subtitle=None):
    frame = QtWidgets.QFrame()
    frame.setObjectName('card')
    layout = QtWidgets.QVBoxLayout(frame)
    layout.setContentsMargins(18, 15, 18, 15)
    layout.setSpacing(10)
    layout.addWidget(label(title, 'sectionTitle'))
    if subtitle:
        description = label(subtitle)
        description.setWordWrap(True)
        layout.addWidget(description)
    return frame, layout


class AirspaceArtwork(QtWidgets.QWidget):
    """Decorative, deterministic artwork, explicitly not a position display."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(160)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.setFixedHeight(174)
        self.elapsed = QtCore.QElapsedTimer()
        self.elapsed.start()
        self.motion = True
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(50)
        self.timer.timeout.connect(self.update)
        self.timer.start()

    def set_motion(self, enabled):
        self.motion = enabled
        if enabled:
            self.timer.start()
        else:
            self.timer.stop()
        self.update()

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        rect = QtCore.QRectF(self.rect()).adjusted(1, 1, -1, -1)
        gradient = QtGui.QLinearGradient(rect.topLeft(), rect.bottomRight())
        gradient.setColorAt(0, QtGui.QColor('#102d43'))
        gradient.setColorAt(0.5, QtGui.QColor('#0c1c30'))
        gradient.setColorAt(1, QtGui.QColor('#171e3d'))
        p.setBrush(gradient)
        p.setPen(QtGui.QColor('#24465d'))
        p.drawRoundedRect(rect, 15, 15)
        p.setClipRect(rect.adjusted(1, 1, -1, -1))
        p.setPen(QtGui.QPen(QtGui.QColor(64, 132, 166, 25), 1))
        for x in range(0, self.width(), 26):
            p.drawLine(x, 0, x, self.height())
        for y in range(0, self.height(), 26):
            p.drawLine(0, y, self.width(), y)
        # Text is intentionally painted on an opaque left-side panel: legible at
        # narrow sizes, while the artwork is clipped to the right-hand area.
        right = max(330, self.width() * 0.55)
        p.save()
        p.setClipRect(QtCore.QRectF(right, 0, self.width() - right, self.height()))
        cx, cy = self.width() - 140, 87
        t = self.elapsed.elapsed() / 1000.0 if self.motion else 0
        p.setPen(QtGui.QPen(QtGui.QColor(56, 185, 207, 45), 1))
        p.setBrush(QtCore.Qt.NoBrush)
        for radius in (35, 62, 90, 118):
            p.drawEllipse(QtCore.QPointF(cx, cy), radius, radius)
        p.drawLine(QtCore.QPointF(cx - 140, cy), QtCore.QPointF(cx + 140, cy))
        p.drawLine(QtCore.QPointF(cx, cy - 100), QtCore.QPointF(cx, cy + 100))
        # Stylised drone wireframe. It is not a fleet map or a simulated aircraft.
        p.translate(cx, cy)
        p.rotate(-16 + math.sin(t * 0.45) * 3)
        p.setPen(QtGui.QPen(QtGui.QColor('#44d9e8'), 2))
        for x, y in ((-48, -32), (48, -32), (-48, 32), (48, 32)):
            p.drawLine(QtCore.QPointF(0, 0), QtCore.QPointF(x, y))
            p.setBrush(QtGui.QColor(20, 71, 91, 150))
            p.drawEllipse(QtCore.QPointF(x, y), 23, 15)
            p.setPen(QtGui.QPen(QtGui.QColor('#79eff4'), 1))
            a = t * 3
            dx, dy = 19 * math.cos(a), 10 * math.sin(a)
            p.drawLine(QtCore.QPointF(x - dx, y - dy), QtCore.QPointF(x + dx, y + dy))
            p.setPen(QtGui.QPen(QtGui.QColor('#44d9e8'), 2))
        p.setBrush(QtGui.QColor('#163e57'))
        p.drawRoundedRect(QtCore.QRectF(-19, -25, 38, 50), 9, 9)
        p.setBrush(QtGui.QColor('#7df7ec'))
        p.drawEllipse(QtCore.QPointF(0, -8), 4, 4)
        p.restore()
        p.setPen(QtGui.QColor('#5cdae0'))
        p.setFont(QtGui.QFont('Segoe UI', 8, QtGui.QFont.Bold))
        p.drawText(23, 31, 'T E C H N I C   /   F L I G H T   O P E R A T I O N S')
        p.setPen(QtGui.QColor('#f0f6ff'))
        p.setFont(QtGui.QFont('Segoe UI', 24, QtGui.QFont.Bold))
        p.drawText(22, 79, 'Precision in every flight.')
        p.setPen(QtGui.QColor('#a7bcd2'))
        p.setFont(QtGui.QFont('Segoe UI', 10))
        p.drawText(24, 108, 'Plan with clarity. Command with confidence.')
        p.setPen(QtGui.QColor('#7893af'))
        p.setFont(QtGui.QFont('Segoe UI', 8))
        p.drawText(24, 145, 'DECORATIVE ARTWORK  /  NOT LIVE TELEMETRY')


class Presentation(QtCore.QObject):
    def __init__(self, ui, window):
        super().__init__(window)
        self.ui = ui
        self.window = window
        self.table = None
        self.metrics = {}
        self.build()
        # Poll only presentation data; do not call model.emit_signals, selection
        # methods, server handlers, networking APIs or command buttons.
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.refresh)
        self.timer.start()
        QtCore.QTimer.singleShot(0, self.refresh)

    def build(self):
        ui, window = self.ui, self.window
        window.setWindowTitle('TECHNIC | Drone Show Command Center')
        window.resize(1480, 940)
        window.setMinimumSize(1000, 720)
        window.setWindowIcon(QtGui.QIcon(str(ASSETS / 'technic.svg')))
        window.setStyleSheet((ASSETS / 'command_center.qss').read_text(encoding='utf-8'))
        # Keep horizontalLayout alive as the server's original table insertion
        # point, but remove its old command column and move it into the fleet card.
        ui.gridLayout.removeItem(ui.horizontalLayout)
        ui.horizontalLayout.removeItem(ui.verticalLayout)
        ui.horizontalLayout.setSizeConstraint(QtWidgets.QLayout.SetDefaultConstraint)
        ui.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        ui.gridLayout.setContentsMargins(18, 12, 18, 12)
        ui.gridLayout.setSpacing(14)
        for name in ('line', 'line_2', 'line_3', 'line_4', 'line_5', 'line_6'):
            getattr(ui, name).hide()

        header = QtWidgets.QHBoxLayout()
        brand_icon = QtWidgets.QLabel()
        brand_icon.setPixmap(QtGui.QIcon(str(ASSETS / 'technic.svg')).pixmap(44, 44))
        header.addWidget(brand_icon)
        brand = QtWidgets.QVBoxLayout()
        brand.setSpacing(1)
        brand.addWidget(label('TECHNIC', 'brand'))
        brand.addWidget(label('DRONE SHOW / COMMAND CENTER', 'eyebrow'))
        header.addLayout(brand)
        header.addStretch()
        self.motion = QtWidgets.QCheckBox('Visual motion')
        self.motion.setChecked(True)
        self.motion.setToolTip('Only decorative motion; never affects flight or commands.')
        header.addWidget(self.motion)
        header.addSpacing(18)
        self.clock = label('', 'clock')
        self.clock.setMinimumWidth(225)
        header.addWidget(self.clock)
        ui.gridLayout.addLayout(header, 0, 0, 1, 2)

        # Main area is independently resizable; command cards scroll instead of
        # shrinking out of reach on smaller Windows displays.
        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        ui.gridLayout.addWidget(self.splitter, 1, 0, 1, 2)
        ui.gridLayout.setRowStretch(1, 1)
        workspace = QtWidgets.QWidget()
        workspace_layout = QtWidgets.QVBoxLayout(workspace)
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        workspace_layout.setSpacing(14)
        self.artwork = AirspaceArtwork()
        workspace_layout.addWidget(self.artwork)
        self.motion.toggled.connect(self.artwork.set_motion)

        metrics_row = QtWidgets.QHBoxLayout()
        metrics_row.setSpacing(12)
        for key, title, hint in (
                ('rows', 'FLEET RECORDS', 'Rows in the real fleet model'),
                ('selected', 'SELECTED DRONES', 'Command checkbox selection'),
                ('ready', 'SELECTED / READY', 'Existing preflight checks')):
            box, layout = card(title)
            layout.setContentsMargins(15, 12, 15, 12)
            value = label('--', 'metric')
            layout.addWidget(value)
            layout.addWidget(label(hint, 'metricHint'))
            self.metrics[key] = value
            metrics_row.addWidget(box)
        workspace_layout.addLayout(metrics_row)

        fleet, fleet_layout = card('FLEET / LIVE TABLE')
        fleet_layout.setContentsMargins(16, 14, 16, 12)
        toolbar = QtWidgets.QHBoxLayout()
        toolbar.addWidget(label('Original telemetry model • original status colours'))
        toolbar.addStretch()
        for title, action in (('Select all', ui.action_select_all),
                              ('Clear', ui.action_deselect_all),
                              ('Columns', ui.action_configure_columns)):
            button = QtWidgets.QToolButton()
            button.setDefaultAction(action)
            button.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)
            button.setText(title)
            toolbar.addWidget(button)
        fleet_layout.addLayout(toolbar)
        self.table_host = QtWidgets.QWidget()
        self.table_host.setObjectName('tableHost')
        self.table_host.setLayout(ui.horizontalLayout)
        fleet_layout.addWidget(self.table_host, 1)
        self.empty = label('NO FLEET RECORDS\nWaiting for drone data — no demo rows are added.', 'emptyState')
        self.empty.setAlignment(QtCore.Qt.AlignCenter)
        self.empty.setWordWrap(True)
        fleet_layout.addWidget(self.empty, 1)
        scope = label('Selection uses the original checkboxes, not highlighted table cells.', 'scopeNote')
        scope.setWordWrap(True)
        fleet_layout.addWidget(scope)
        workspace_layout.addWidget(fleet, 1)
        self.splitter.addWidget(workspace)

        right_panel = QtWidgets.QWidget()
        right_panel.setMinimumWidth(300)
        right_panel.setMaximumWidth(430)
        right_layout = QtWidgets.QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)
        scroll = QtWidgets.QScrollArea()
        scroll.setObjectName('commandScroll')
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        scroll.setMinimumWidth(290)
        scroll.setMaximumWidth(430)
        right_layout.addWidget(scroll, 1)
        commands = QtWidgets.QWidget()
        command_layout = QtWidgets.QVBoxLayout(commands)
        command_layout.setContentsMargins(0, 0, 5, 0)
        command_layout.setSpacing(12)
        command_layout.addWidget(label('COMMAND DECK', 'eyebrow'))

        icon_names = {
            'check_button': 'check', 'start_button': 'play', 'pause_button': 'pause',
            'takeoff_button': 'up', 'land_selected_button': 'down',
            'land_all_button': 'down', 'disarm_selected_button': 'power',
            'disarm_all_button': 'power', 'emergency_land_button': 'warning',
            'leds_button': 'light', 'flip_button': 'rotate', 'reboot_fcu': 'rotate',
            'calibrate_gyro': 'settings', 'calibrate_level': 'settings'}

        def section(title, subtitle, names, destination=None):
            box, layout = card(title, subtitle)
            for name in names:
                if isinstance(name, tuple):
                    row = QtWidgets.QHBoxLayout()
                    for subname in name:
                        row.addWidget(getattr(ui, subname))
                    layout.addLayout(row)
                else:
                    widget = getattr(ui, name)
                    if isinstance(widget, QtWidgets.QPushButton):
                        widget.setMinimumHeight(36)
                        widget.setCursor(QtCore.Qt.PointingHandCursor)
                        widget.setIcon(QtGui.QIcon(str(ASSETS / (icon_names[name] + '.svg'))))
                        widget.setIconSize(QtCore.QSize(17, 17))
                        # No animation or shadow effect changes command states.
                    layout.addWidget(widget)
            (destination if destination is not None else command_layout).addWidget(box)

        section('01  /  SHOW SEQUENCE', 'Uses the original preflight and start checks.',
                [('start_text', 'start_delay_spin'), 'check_button', 'start_button', 'pause_button'])
        section('02  /  FLIGHT CONTROL', 'Scope: selected drones',
                ['takeoff_button', ('z_checkbox', 'z_spin'), 'land_selected_button',
                 'disarm_selected_button', 'leds_button', 'flip_button'])
        section('03  /  SAFETY COMMANDS',
                'Land ALL / Disarm ALL: broadcast.\nEmergency land: selected drones only.',
                ['land_all_button', 'disarm_all_button', 'emergency_land_button'], right_layout)
        section('04  /  MAINTENANCE', 'Scope: selected drones',
                ['reboot_fcu', 'calibrate_gyro', 'calibrate_level'])
        command_layout.addStretch()
        scroll.setWidget(commands)
        self.splitter.addWidget(right_panel)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 0)
        self.splitter.setSizes([1070, 330])
        footer = QtWidgets.QHBoxLayout()
        footer.addWidget(label('TECHNIC  /  NATIVE PyQt5 INTERFACE', 'eyebrow'))
        footer.addStretch()
        footer.addWidget(label('Command scope & safety checks retained', 'muted'))
        ui.gridLayout.addLayout(footer, 2, 0, 1, 2)
        # Show an entrance transition only on the artwork, never on controls.
        self.effect = QtWidgets.QGraphicsOpacityEffect(self.artwork)
        self.artwork.setGraphicsEffect(self.effect)
        self.fade = QtCore.QPropertyAnimation(self.effect, b'opacity', self)
        self.fade.setDuration(700)
        self.fade.setStartValue(0.25)
        self.fade.setEndValue(1.0)
        self.fade.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        self.fade.start()

    def refresh(self):
        self.clock.setText(QtCore.QDateTime.currentDateTime().toString('ddd, dd MMM  |  HH:mm:ss'))
        table = getattr(self.ui, 'copter_table', None)
        if table is None:
            self.empty.setVisible(True)
            self.table_host.setVisible(False)
            return
        if table is not self.table:
            self.table = table
            # Presentation only. Preserve delegates, model colours, sorting and
            # selection semantics. A light data surface keeps black model text
            # readable over existing red/yellow/green diagnostic backgrounds.
            table.verticalHeader().setDefaultSectionSize(33)
            table.setAlternatingRowColors(False)
        model = table.model  # CopterTableWidget stores the source model here.
        count = model.rowCount()
        selected = list(model.user_selected())
        ready = sum(1 for drone in selected if drone.states.all_checks)
        self.metrics['rows'].setText(str(count))
        self.metrics['selected'].setText(str(len(selected)))
        self.metrics['ready'].setText('{} / {}'.format(ready, len(selected)))
        self.empty.setVisible(count == 0)
        self.table_host.setVisible(count != 0)


def install(ui, window):
    ui.command_center = Presentation(ui, window)
