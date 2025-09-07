import time
import pyotp
from PySide6.QtCore import Qt, QTimer, QSize, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPen
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget, QGridLayout,
)

from app.helpers import parse_account_label
from .circular_countdown import CircularCountdown
from .dialogs import OptionsDialog


class OtpCard(QWidget):
    """Widget for displaying an OTP account."""

    edit_requested = Signal(object)  # Emits self
    delete_requested = Signal(object)  # Emits self

    def __init__(self, account, icon_set="light", start_hidden=False, parent=None):
        super().__init__(parent)
        self.icon_set = icon_set
        self.init_ui()

        self.setFixedSize(300, 100)
        shadow = QGraphicsDropShadowEffect()
        shadow.setColor(QColor(100, 100, 100, 50))
        shadow.setBlurRadius(14)
        shadow.setOffset(0, 4)
        self.frame.setGraphicsEffect(shadow)
        self.timer = QTimer(self)

        self.code_hidden = start_hidden
        self.update_data(account)  # Populate UI with data

        self.timer.timeout.connect(self.update_totp)
        self.timer.start(1000)

    def update_data(self, account):
        """Update the card with new account data."""
        try:
            if "key_uri" in account:
                self.account_name, self.user = parse_account_label(account["key_uri"])
                self.totp = pyotp.parse_uri(account["key_uri"])
            else:
                self.account_name = account.get("name", "Unknown")
                self.user = ""
                self.totp = pyotp.TOTP(account.get("secret", ""))
            self.interval = self.totp.interval
        except Exception:
            self.account_name = account.get("name", "Invalid Account")
            self.user = "Error: Invalid Secret/URI"
            self.totp = None
            self.interval = 30  # Default

        self.label_account.setText(self.account_name)
        self.label_user.setText(self.user)
        self.update_totp()

    def init_ui(self):
        self.frame = QFrame(self)
        self.frame.setObjectName("frame")
        self.frame.setFixedSize(300, 100)
        main_layout = QHBoxLayout(self.frame)
        main_layout.setContentsMargins(10, 0, 10, 0)
        info_layout = QVBoxLayout()
        info_layout.setSpacing(0)
        info_layout.setAlignment(Qt.AlignmentFlag.AlignLeft & Qt.AlignmentFlag.AlignVCenter)
        self.label_account = QLabel("Account")
        self.label_account.setObjectName("label_account")
        self.label_account.setFixedHeight(20)
        #self.label_account.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.label_account.setFont(QFont("Times", 12))

        self.label_user = QLabel("User")
        self.label_user.setObjectName("label_user")
        #self.label_user.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.label_user.setFixedHeight(21)
        self.label_user.setFont(QFont("Times", 9))

        self.label_current = QLabel("-- -- --")
        self.label_current.setObjectName("label_current")
        #self.label_current.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.label_current.setFixedHeight(20)
        self.label_current.setFont(QFont("Times", 15))

        info_layout.addWidget(self.label_account)
        info_layout.addWidget(self.label_user)
        info_layout.addWidget(self.label_current)
        main_layout.addLayout(info_layout)

        main_layout.addStretch()
        self.countdown_circle = CircularCountdown(30, self.icon_set)
        main_layout.addWidget(self.countdown_circle)

        functions_layout = QVBoxLayout()
        functions_layout.setSpacing(0)

        grid_layout = QGridLayout()
        grid_layout.setContentsMargins(0, 0, 0, 30)

        self.options_button = QPushButton()
        self.options_button.setStyleSheet("border: none; background-color: transparent;")
        self.options_button.setObjectName("options_button")
        self.options_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.options_button.setIcon(QIcon(f"images/{self.icon_set}-options-16.png"))
        self.options_button.setIconSize(QSize(10, 10))
        self.options_button.setFixedSize(15, 15)
        self.options_button.clicked.connect(self.show_options_dialog)
        grid_layout.addWidget(self.options_button, 0, 1,
                              alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.toggle_button = QPushButton()
        self.toggle_button.setStyleSheet("border: none; background-color: transparent;")
        self.toggle_button.setObjectName("toggle_button")
        self.toggle_button.setCursor(Qt.CursorShape.PointingHandCursor)
        icon_hide = QIcon(f"images/{self.icon_set}-hide-24.png")
        icon_show = QIcon(f"images/{self.icon_set}-show-24.png")
        self.toggle_button.setIcon(icon_hide)
        self.toggle_button.setIconSize(QSize(20, 20))
        self.toggle_button.setFixedSize(30, 30)
        self.toggle_button.clicked.connect(self.toggle_code_visibility)
        self.icon_hide = icon_hide
        self.icon_show = icon_show
        grid_layout.addWidget(self.toggle_button, 1, 0,
                              alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.copy_button = QPushButton()
        self.copy_button.setStyleSheet("border: none; background-color: transparent;")
        self.copy_button.setObjectName("copy_button")
        self.copy_button.setCursor(Qt.CursorShape.PointingHandCursor)
        icon_copy = QIcon(f"images/{self.icon_set}-copy-24.png")
        self.copy_button.setIcon(icon_copy)
        self.copy_button.setIconSize(QSize(20, 20))
        self.copy_button.setFixedSize(30, 30)
        self.copy_button.clicked.connect(self.copy_to_clipboard)
        grid_layout.addWidget(self.copy_button, 1, 1,
                              alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        functions_layout.addLayout(grid_layout)
        main_layout.addLayout(functions_layout)

    def show_options_dialog(self):
        dlg = OptionsDialog(self.account_name, self)
        result = dlg.exec()
        if result == QDialog.DialogCode.Accepted:
            self.edit_requested.emit(self)
        elif result == QDialog.DialogCode.Rejected:
            self.delete_requested.emit(self)

    def toggle_code_visibility(self):
        self.code_hidden = not self.code_hidden
        if self.code_hidden:
            self.label_current.setText("*** ***")
            self.toggle_button.setIcon(self.icon_show)
        else:
            self.update_totp_code()
            self.toggle_button.setIcon(self.icon_hide)

    def update_totp(self):
        now = int(time.time())
        elapsed = now % self.interval
        remaining = self.interval - elapsed
        self.countdown_circle.update_value(remaining)
        if not self.code_hidden:
            self.update_totp_code()

    def update_totp_code(self):
        """Updates only the OTP code label."""
        if self.totp:
            current = self.totp.now()
            self.label_current.setText(" ".join([current[:3], current[3:]]))
        else:
            self.label_current.setText("-- -- --")

    def update_icons(self, icon_set):
        self.icon_set = icon_set
        self.options_button.setIcon(QIcon(f"images/{self.icon_set}-options-16.png"))
        self.icon_hide = QIcon(f"images/{self.icon_set}-hide-24.png")
        self.icon_show = QIcon(f"images/{self.icon_set}-show-24.png")
        self.toggle_button.setIcon(self.icon_hide if not self.code_hidden else self.icon_show)
        self.countdown_circle.update_theme(self.icon_set)
        self.copy_button.setIcon(QIcon(f"images/{self.icon_set}-copy-24.png"))

    def copy_to_clipboard(self):
        try:
            current = self.totp.now() if self.totp else ""
            clipboard = QApplication.clipboard()
            clipboard.setText(current)
        except Exception:
            pass