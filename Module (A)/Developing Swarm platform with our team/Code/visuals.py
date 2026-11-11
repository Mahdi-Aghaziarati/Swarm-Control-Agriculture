"""Original vector artwork and lightweight Qt animations. No network assets."""
import math
from collections import deque
from PyQt5.QtCore import Qt, QRectF, QPointF, QTimer
from PyQt5.QtGui import (QColor, QPainter, QPen, QLinearGradient, QRadialGradient,
                         QPainterPath, QFont, QPolygonF)
from PyQt5.QtWidgets import QWidget, QFrame, QLabel, QVBoxLayout, QHBoxLayout

CYAN = '#62e5f5'
MINT = '#60e6bb'
VIOLET = '#b29aff'


def label(text, name=None):
    w = QLabel(text)
    if name:
        w.setObjectName(name)
    if name in ('Muted', 'HeroStatus', 'Eyebrow'):
        w.setWordWrap(True)
    return w


def polygon(points):
    return QPolygonF([QPointF(x, y) for x, y in points])


class DroneArtwork(QWidget):
    """Animated, resolution-independent quadcopter illustration, not a live map."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(220, 160)
        self.phase = 0
        self.motion = True
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.advance)
        self.timer.start(40)  # 25 fps, only this small canvas is repainted.
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

    def advance(self):
        if self.isVisible() and self.motion:
            self.phase = (self.phase + 2.5) % 360
            self.update()

    def set_motion(self, enabled):
        self.motion = enabled
        self.timer.start(40) if enabled else self.timer.stop()
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.translate(self.width() / 2, self.height() / 2)
        scale = min(self.width() / 480, self.height() / 300)
        p.scale(scale, scale)
        glow = QRadialGradient(QPointF(0, 0), 220)
        glow.setColorAt(0, QColor(51, 173, 204, 40))
        glow.setColorAt(1, QColor(0, 0, 0, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(glow)
        p.drawEllipse(QRectF(-235, -145, 470, 290))
        # Horizon reticle and latitude ellipses.
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(76, 143, 172, 35), 1))
        for size in (140, 205, 265, 335, 410):
            p.drawEllipse(QRectF(-size / 2, -size / 4, size, size / 2))
        p.drawLine(QPointF(-225, 0), QPointF(225, 0))
        p.drawLine(QPointF(0, -135), QPointF(0, 135))
        # Orbiting signal particles are decorative and do not represent telemetry.
        p.setPen(Qt.NoPen)
        for i in range(12):
            angle = math.radians(self.phase + i * 30)
            alpha = 35 + int(100 * (1 + math.sin(angle)) / 2)
            p.setBrush(QColor(110, 224, 240, alpha))
            p.drawEllipse(QPointF(math.cos(angle)*207, math.sin(angle)*102), 2, 2)
        p.setPen(QPen(QColor('#33556b'), 1))
        for x, y, sign in [(-215, -115, 1), (215, -115, -1), (-215, 115, 1), (215, 115, -1)]:
            p.drawLine(QPointF(x, y), QPointF(x + 18 * sign, y))
            p.drawLine(QPointF(x, y), QPointF(x, y + (16 if y < 0 else -16)))
        p.save()
        p.translate(0, math.sin(math.radians(self.phase)) * 3)
        # Carbon airframe arms with luminous inlays.
        for x, y in [(-133, -65), (133, -65), (-133, 65), (133, 65)]:
            p.setPen(QPen(QColor('#071019'), 24, Qt.SolidLine, Qt.RoundCap))
            p.drawLine(QPointF(x, y), QPointF(0, 0))
            p.setPen(QPen(QColor('#345168'), 17, Qt.SolidLine, Qt.RoundCap))
            p.drawLine(QPointF(x, y), QPointF(0, 0))
            p.setPen(QPen(QColor('#101f2f'), 13, Qt.SolidLine, Qt.RoundCap))
            p.drawLine(QPointF(x, y), QPointF(0, 0))
            p.setPen(QPen(QColor(CYAN if y < 0 else VIOLET), 1.4))
            p.drawLine(QPointF(x, y - 3), QPointF(0, -3))
        # Rotor guards and animated rotor blades.
        for index, (x, y) in enumerate([(-133, -65), (133, -65), (-133, 65), (133, 65)]):
            color = QColor(CYAN if index < 2 else VIOLET)
            p.save()
            p.translate(x, y)
            p.scale(1, .64)
            p.setBrush(QColor(9, 23, 36, 160))
            p.setPen(QPen(QColor('#203d51'), 5))
            p.drawEllipse(QRectF(-55, -55, 110, 110))
            for width, alpha in [(9, 12), (5, 22), (1.2, 180)]:
                color.setAlpha(alpha)
                p.setPen(QPen(color, width))
                p.setBrush(Qt.NoBrush)
                p.drawEllipse(QRectF(-55, -55, 110, 110))
            p.setPen(QPen(QColor('#81eaf3'), 2))
            p.drawArc(QRectF(-49, -49, 98, 98), int((self.phase * 2 + index * 70) * 16), 65 * 16)
            p.rotate(self.phase * (4 if index % 2 else -4))
            blades = QLinearGradient(-44, 0, 44, 0)
            blades.setColorAt(0, QColor('#1e384b'))
            blades.setColorAt(.5, QColor('#83b4c7'))
            blades.setColorAt(1, QColor('#1e384b'))
            p.setBrush(blades)
            p.setPen(QPen(QColor('#548493'), 1))
            p.drawPolygon(polygon([(-46, -6), (-12, -10), (12, -2), (46, 5), (12, 10), (-12, 2)]))
            p.setBrush(QColor('#0d1b29'))
            p.setPen(QPen(QColor('#b0e8ed'), 1))
            p.drawEllipse(QRectF(-8, -8, 16, 16))
            p.restore()
        # Faceted fuselage, vents, camera and navigation LEDs.
        body = QLinearGradient(-42, -55, 52, 50)
        body.setColorAt(0, QColor('#517080'))
        body.setColorAt(.35, QColor('#243d50'))
        body.setColorAt(1, QColor('#080f1b'))
        p.setBrush(body)
        p.setPen(QPen(QColor('#6b9aaa'), 1.2))
        p.drawPolygon(polygon([(-34, -44), (0, -58), (34, -44), (43, 22), (21, 48), (-21, 48), (-43, 22)]))
        p.setBrush(QColor('#101d2b'))
        p.setPen(QPen(QColor('#385266'), 1))
        p.drawPolygon(polygon([(-22, -34), (0, -43), (22, -34), (27, 20), (0, 35), (-27, 20)]))
        for y in range(-19, 16, 6):
            p.setPen(QPen(QColor('#55788b'), 1))
            p.drawLine(QPointF(-13, y), QPointF(13, y))
        p.setPen(QPen(QColor(CYAN), 2))
        p.drawLine(QPointF(-25, -35), QPointF(-30, 14))
        p.drawLine(QPointF(25, -35), QPointF(30, 14))
        p.setBrush(QColor('#07101a'))
        p.setPen(QPen(QColor('#8099b1'), 2))
        p.drawRoundedRect(QRectF(-16, 39, 32, 19), 5, 5)
        p.setBrush(QColor('#276b91'))
        p.setPen(QPen(QColor(CYAN), 1))
        p.drawEllipse(QRectF(-6, 43, 12, 12))
        p.restore()
        # Scan line stays inside the illustration.
        y = -115 + (self.phase / 360) * 230
        scan = QLinearGradient(-200, 0, 200, 0)
        scan.setColorAt(0, QColor(98, 229, 245, 0))
        scan.setColorAt(.5, QColor(98, 229, 245, 85))
        scan.setColorAt(1, QColor(98, 229, 245, 0))
        p.setPen(QPen(scan, 1))
        p.drawLine(QPointF(-205, y), QPointF(205, y))
        p.end()


class HeroCard(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName('Hero')
        self.setMinimumHeight(225)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(28, 20, 18, 16)
        copy = QVBoxLayout()
        copy.addWidget(label('T E C H N I C   /   F L I G H T   O P E R A T I O N S', 'Eyebrow'))
        copy.addWidget(label('Precision.\nIn formation.', 'HeroTitle'))
        copy.addWidget(label('One leader. A connected fleet. A single workspace.', 'Muted'))
        copy.addSpacing(8)
        self.status = label('●  WORKSPACE READY     /     AWAITING CONNECTIONS', 'HeroStatus')
        copy.addWidget(self.status)
        layout.addLayout(copy, 5)
        scene = QVBoxLayout()
        self.artwork = DroneArtwork()
        scene.addWidget(self.artwork)
        caption = label('Q U A D   /   X 4     ·     CONCEPT VISUAL', 'Micro')
        caption.setAlignment(Qt.AlignCenter)
        scene.addWidget(caption)
        layout.addLayout(scene, 4)


class MetricCard(QFrame):
    def __init__(self, title, note, accent=CYAN):
        super().__init__()
        self.setObjectName('Metric')
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        top = QHBoxLayout()
        top.addWidget(label(title, 'Micro'))
        top.addStretch()
        dot = label('●')
        dot.setStyleSheet(f'color: {accent}; font-size: 11px;')
        top.addWidget(dot)
        layout.addLayout(top)
        self.value = label('0', 'MetricValue')
        layout.addWidget(self.value)
        layout.addWidget(label(note, 'Muted'))


class TrafficChart(QWidget):
    """Actual received messages per sampling interval. No synthetic telemetry."""
    def __init__(self):
        super().__init__()
        self.points = deque([0] * 60, maxlen=60)
        self.setMinimumHeight(90)

    def push(self, value):
        self.points.append(max(0, value))
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(10, 12, max(1, self.width() - 20), max(1, self.height() - 30))
        p.setPen(QPen(QColor('#1b2d3e'), 1, Qt.DotLine))
        for i in range(4):
            y = r.top() + r.height() * i / 3
            p.drawLine(QPointF(r.left(), y), QPointF(r.right(), y))
        peak = max(5, max(self.points))
        line = QPainterPath()
        coords = []
        for i, v in enumerate(self.points):
            coords.append(QPointF(r.left() + i / 59 * r.width(), r.bottom() - v / peak * r.height()))
        line.moveTo(coords[0])
        for pt in coords[1:]:
            line.lineTo(pt)
        area = QPainterPath(line)
        area.lineTo(r.right(), r.bottom())
        area.lineTo(r.left(), r.bottom())
        area.closeSubpath()
        gradient = QLinearGradient(0, r.top(), 0, r.bottom())
        gradient.setColorAt(0, QColor(98, 229, 245, 65))
        gradient.setColorAt(1, QColor(98, 229, 245, 2))
        p.fillPath(area, gradient)
        p.setPen(QPen(QColor(98, 229, 245, 20), 6))
        p.drawPath(line)
        p.setPen(QPen(QColor(CYAN), 1.7))
        p.drawPath(line)
        p.setPen(QColor('#668499'))
        p.setFont(QFont('Consolas', 8))
        p.drawText(QRectF(r.left(), r.bottom() + 4, 110, 14), Qt.AlignLeft, '60 S HISTORY')
        p.drawText(QRectF(r.right() - 160, r.bottom() + 4, 160, 14), Qt.AlignRight, f'PEAK {max(self.points):.0f} MSG/S')
        p.end()


class LaunchScreen(QWidget):
    """Short cinematic intro; progress indicates presentation, not hardware checks."""
    def __init__(self):
        super().__init__(None, Qt.SplashScreen | Qt.FramelessWindowHint)
        self.setFixedSize(760, 480)
        self.setObjectName('Launch')
        box = QVBoxLayout(self)
        box.setContentsMargins(38, 28, 38, 28)
        top = QHBoxLayout()
        top.addWidget(label('T /', 'BrandMark'))
        top.addWidget(label('TECHNIC', 'Brand'))
        top.addStretch()
        top.addWidget(label('FLIGHT WORKSPACE  /  02', 'Micro'))
        box.addLayout(top)
        self.artwork = DroneArtwork()
        box.addWidget(self.artwork, 1)
        title = label('A new perspective on command.', 'SplashTitle')
        title.setAlignment(Qt.AlignCenter)
        box.addWidget(title)
        sub = label('LEADER CONTROL   /   FLEET TELEMETRY   /   LIVE STREAM', 'Micro')
        sub.setAlignment(Qt.AlignCenter)
        box.addWidget(sub)
        box.addSpacing(20)
        self.status = label('Preparing your workspace…', 'Muted')
        self.status.setAlignment(Qt.AlignCenter)
        box.addWidget(self.status)
        self.progress = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(30)

    def tick(self):
        self.progress = min(1, self.progress + .018)
        self.update()

    def paintEvent(self, event):
        # QSS background is drawn explicitly for the custom top-level widget.
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor('#070e18'))
        g = QRadialGradient(QPointF(380, 200), 380)
        g.setColorAt(0, QColor(22, 62, 80, 100))
        g.setColorAt(1, QColor(7, 14, 24, 0))
        p.fillRect(self.rect(), g)
        p.setPen(QPen(QColor('#2a4b60'), 1))
        p.drawRect(self.rect().adjusted(0, 0, -1, -1))
        p.setPen(Qt.NoPen)
        p.setBrush(QColor('#142b3b'))
        p.drawRoundedRect(QRectF(205, 458, 350, 2), 1, 1)
        p.setBrush(QColor(CYAN))
        p.drawRoundedRect(QRectF(205, 458, 350 * self.progress, 2), 1, 1)
        p.end()
