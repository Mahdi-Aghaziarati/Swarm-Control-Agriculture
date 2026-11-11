"""Animated controls and fleet topology. Motion is decorative, not flight telemetry."""
import math
from PyQt5.QtCore import Qt, QTimer, QRectF, QPointF, QVariantAnimation
from PyQt5.QtGui import QColor, QPainter, QPen, QFont, QRadialGradient
from PyQt5.QtWidgets import QPushButton, QWidget, QSizePolicy, QTableWidget


class DeviceTable(QTableWidget):
    """Give spare width to video without ever squeezing its controls."""
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.columnCount() == 3:
            self.setColumnWidth(2, max(350, self.viewport().width()
                                      - self.columnWidth(0) - self.columnWidth(1)))


class CommandButton(QPushButton):
    """Never sacrifice the label width; animate a subtle hover highlight."""
    def __init__(self, text):
        super().__init__(text)
        self.hover = 0.
        self.animation = QVariantAnimation(self)
        self.animation.setDuration(180)
        self.animation.valueChanged.connect(self.set_hover)
        self.setMinimumWidth(self.sizeHint().width() + 16)
        self.setMinimumHeight(38)
        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)
        self.setToolTip(text)

    def set_hover(self, value):
        self.hover = float(value)
        self.update()

    def animate(self, target):
        self.animation.stop()
        self.animation.setStartValue(self.hover)
        self.animation.setEndValue(target)
        self.animation.start()

    def enterEvent(self, event):
        self.animate(1.)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.animate(0.)
        super().leaveEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.hover and self.isEnabled():
            p = QPainter(self)
            p.setRenderHint(QPainter.Antialiasing)
            color = QColor('#bbadff' if self.objectName() == 'LeaderButton' else '#69e5ee')
            color.setAlpha(int(self.hover * 150))
            p.setPen(QPen(color, 1.2))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), 7, 7)
            p.end()


class FleetTopology(QWidget):
    def __init__(self):
        super().__init__()
        self.nodes = []
        self.phase = 0.
        self.motion = True
        self.setMinimumHeight(172)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(40)

    def set_motion(self, enabled):
        self.motion = enabled
        self.timer.start(40) if enabled else self.timer.stop()
        self.update()

    def tick(self):
        if self.isVisible():
            self.phase = (self.phase + .012) % 1
            self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        p.setPen(QPen(QColor('#173044'), 1, Qt.DotLine))
        for x in range(12, w, 28):
            p.drawLine(x, 32, x, h-12)
        center = QPointF(w*.19, h*.56)
        p.setFont(QFont('Consolas', 8))
        p.setPen(QColor('#7a98ae'))
        p.drawText(12, 17, 'FLEET TOPOLOGY  /  CONNECTION STATUS')
        p.drawText(QRectF(w-235, 4, 223, 20), Qt.AlignRight, 'SCHEMATIC · NOT A FLIGHT MAP')
        leaders = [n for n in self.nodes if n[1] == 'leader']
        children = [n for n in self.nodes if n[1] == 'child']
        if not self.nodes:
            p.setPen(QColor('#6c879c'))
            p.drawText(QRectF(w*.36, 50, w*.62, 80), Qt.AlignCenter,
                       'YOUR FLEET STARTS HERE\nRegister a leader and connect child devices')
        visible = children[:8]
        for i, (name, role, online) in enumerate(visible):
            point = QPointF(w*.49 + (i % 4)*w*.135, h*(.40 if i < 4 else .79))
            color = QColor('#60e6bb' if online else '#3a526a')
            p.setPen(QPen(color, 1, Qt.SolidLine if online else Qt.DashLine))
            p.drawLine(center, point)
            if online and self.motion:
                t = (self.phase + i*.17) % 1
                packet = center*(1-t)+point*t
                p.setBrush(QColor('#b2f8ee'))
                p.setPen(Qt.NoPen)
                p.drawEllipse(packet, 3, 3)
            p.setBrush(QColor('#102334'))
            p.setPen(QPen(color, 2))
            p.drawRoundedRect(QRectF(point.x()-12, point.y()-12, 24, 24), 6, 6)
            p.setPen(QColor('#bbccda'))
            p.drawText(QRectF(point.x()-47, point.y()+16, 94, 18), Qt.AlignCenter,
                       p.fontMetrics().elidedText(name, Qt.ElideMiddle, 90))
        color = QColor('#b29aff' if leaders else '#476078')
        halo = QRadialGradient(center, 46)
        halo.setColorAt(0, QColor(178,154,255,65))
        halo.setColorAt(1, QColor(178,154,255,0))
        p.setBrush(halo)
        p.setPen(Qt.NoPen)
        p.drawEllipse(center, 46, 46)
        p.setBrush(QColor('#242139'))
        p.setPen(QPen(color, 2))
        p.drawEllipse(center, 22, 22)
        if self.motion:
            p.drawArc(QRectF(center.x()-30, center.y()-30, 60, 60), int(self.phase*360*16), 100*16)
        p.setPen(color)
        p.drawText(QRectF(center.x()-22, center.y()-12, 44, 24), Qt.AlignCenter, 'LDR')
        p.setPen(QColor('#b2a3d2'))
        p.drawText(QRectF(center.x()-80, center.y()+35, 160, 18), Qt.AlignCenter,
                   leaders[0][0] if leaders else 'NO LEADER')
        if len(children) > 8:
            p.drawText(w-140, h-5, f'+ {len(children)-8} more devices')
        p.end()
