from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget


class CircularCountdown(QWidget):
    """Circular countdown widget for TOTP interval."""

    def __init__(self, interval=30, icon_set="light", parent=None):
        super().__init__(parent)
        self.interval = interval
        self.value = interval
        self.icon_set = icon_set
        self.setFixedSize(65, 65)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def update_value(self, value):
        self.value = value
        self.update()

    def update_theme(self, icon_set):
        self.icon_set = icon_set
        self.update()  # Trigger a repaint

    def paintEvent(self, event):
        size = min(self.width(), self.height())
        rect = QRect(4, 4, size - 8, size - 8)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self.icon_set == "dark":  # Light Mode
            painter.setPen(QPen(QColor("#f0f0f0"), 5))
            painter.drawEllipse(rect)
            angle_span = 360 * (self.value / self.interval)
            painter.setPen(QPen(QColor("#000"), 6))
            painter.drawArc(rect, 90 * 16, -int(angle_span * 16))
            painter.setPen(QColor("#000"))
            font = QFont("Arial", 15, QFont.Weight.Bold)
            painter.setFont(font)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, f"{self.value}")
        else:  # Dark Mode
            painter.setPen(QPen(QColor("#3a3a3a"), 5))
            painter.drawEllipse(rect)
            angle_span = 360 * (self.value / self.interval)
            painter.setPen(QPen(QColor("#fff"), 6))
            painter.drawArc(rect, 90 * 16, -int(angle_span * 16))
            painter.setPen(QColor("#fff"))
            font = QFont("Arial", 15, QFont.Weight.Bold)
            painter.setFont(font)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, f"{self.value}")