import cv2
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QInputDialog,
    QLabel,
    QPushButton,
    QVBoxLayout,
)
from pyzbar.pyzbar import decode


class NewPopup(QInputDialog):
    """Custom popup for text input."""

    def __init__(self, prompt, title="Input"):
        super().__init__()
        self.setWindowTitle(title)
        self.setLabelText(prompt)
        self.setOkButtonText("Next")
        self.setCancelButtonText("Cancel")
        self.resize(400, 120)


class OptionsDialog(QDialog):
    """Dialog for account options: Edit and Delete."""

    def __init__(self, account_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Options for {account_name}")
        self.setMinimumSize(220, 120)
        layout = QVBoxLayout()
        self.edit_btn = QPushButton("Edit")
        self.delete_btn = QPushButton("Delete")
        self.cancel_btn = QPushButton("Cancel")
        layout.addWidget(self.edit_btn)
        layout.addWidget(self.delete_btn)
        layout.addWidget(self.cancel_btn)
        self.setLayout(layout)
        self.edit_btn.clicked.connect(self.accept)
        self.delete_btn.clicked.connect(self.reject)
        self.cancel_btn.clicked.connect(self.close)


class CameraScannerDialog(QDialog):
    """Dialog for scanning QR codes using the camera."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Scan QR Code")
        self.setMinimumSize(400, 300)
        self.decoded_data = None

        layout = QVBoxLayout()
        self.camera_label = QLabel("Initializing camera...")
        self.camera_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.camera_label)
        self.setLayout(layout)

        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            self.camera_label.setText("Could not open camera.")
            return

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.next_frame)
        self.timer.start(1000 // 30)  # ~30 FPS

    def next_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            self.timer.stop()
            return

        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_image)
        # Scale the pixmap to fit the label while preserving aspect ratio
        self.camera_label.setPixmap(
            pixmap.scaled(self.camera_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        )

        decoded_objs = decode(frame)
        if decoded_objs:
            self.decoded_data = decoded_objs[0].data.decode()
            self.accept()

    def closeEvent(self, event):
        try:
            self.timer.stop()
            if self.cap and self.cap.isOpened():
                self.cap.release()
        finally:
            super().closeEvent(event)