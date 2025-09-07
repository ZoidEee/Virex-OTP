from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout


class AboutDialog(QDialog):
    """About dialog for the application."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About Virex OTP")
        self.setFixedSize(300, 180)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("Virex OTP")
        title.setObjectName("aboutTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        version = QLabel("Version 1.0.0")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)

        license_info = QLabel("Licensed under the MIT License.")
        license_info.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(title)
        layout.addWidget(version)
        layout.addWidget(license_info)
        layout.addStretch()

        self.setLayout(layout)