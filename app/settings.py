import json
import os
import re
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QHBoxLayout,
    QPushButton,
    QComboBox,
    QMessageBox,
)
from PySide6.QtGui import QIntValidator
from app.theme import get_theme, apply_palette, get_stylesheet

CONFIG_PATH = "config.json"
DEFAULT_SETTINGS = {
    "auto_lock_timeout": 0,
    "clipboard_clear_timeout": 0,
    "otp_display_mode": "show",
    "theme": "system",
}


def load_settings():
    """Load settings from config file."""
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_SETTINGS.copy()


def save_settings(settings):
    """Save settings to config file."""
    try:
        with open(CONFIG_PATH, "w") as f:
            json.dump(settings, f)
    except Exception:
        pass


def is_strong_password(pw):
    """Check password strength: min 8 chars, upper, lower, digit."""
    if len(pw) < 8:
        return False
    if not re.search(r"[A-Z]", pw):
        return False
    if not re.search(r"[a-z]", pw):
        return False
    if not re.search(r"\d", pw):
        return False
    return True


class SettingsDialog(QDialog):
    """Settings dialog for user preferences."""

    def __init__(self, current_settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumSize(400, 500)
        self.current_settings = current_settings
        self.init_ui()
        self.load_settings()
        self.apply_theme()

    def init_ui(self):
        """Initialize the settings dialog UI."""
        layout = QVBoxLayout()
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        layout.addWidget(QLabel("Change Master Password"))
        self.old_pw = QLineEdit()
        self.old_pw.setEchoMode(QLineEdit.EchoMode.Password)
        self.old_pw.setPlaceholderText("Enter current master password")
        layout.addWidget(self.old_pw)
        self.new_pw = QLineEdit()
        self.new_pw.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_pw.setPlaceholderText("Enter new master password")
        layout.addWidget(self.new_pw)
        self.conf_pw = QLineEdit()
        self.conf_pw.setEchoMode(QLineEdit.EchoMode.Password)
        self.conf_pw.setPlaceholderText("Confirm new master password")
        layout.addWidget(self.conf_pw)

        layout.addSpacing(12)
        layout.addWidget(QLabel("Auto-lock timeout (minutes, 0 to disable)"))
        self.autolock_edit = QLineEdit()
        self.autolock_edit.setValidator(QIntValidator(0, 120))
        self.autolock_edit.setPlaceholderText("0")
        layout.addWidget(self.autolock_edit)

        layout.addSpacing(8)
        layout.addWidget(QLabel("Clipboard clear timeout (seconds, 0 to disable)"))
        self.clipboard_edit = QLineEdit()
        self.clipboard_edit.setValidator(QIntValidator(0, 120))
        self.clipboard_edit.setPlaceholderText("0")
        layout.addWidget(self.clipboard_edit)

        layout.addSpacing(8)
        layout.addWidget(QLabel("Default OTP Display Mode"))
        self.otp_display_combo = QComboBox()
        self.otp_display_combo.addItems(["Show Codes", "Hide Codes"])
        layout.addWidget(self.otp_display_combo)

        layout.addSpacing(8)
        layout.addWidget(QLabel("Theme"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["System Default", "Light", "Dark"])
        layout.addWidget(self.theme_combo)

        layout.addSpacing(16)
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        self.save_btn = QPushButton("Save")
        self.cancel_btn = QPushButton("Cancel")
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)
        self.save_btn.clicked.connect(self.on_save)
        self.cancel_btn.clicked.connect(self.reject)

    def load_settings(self):
        """Load current settings into the dialog fields."""
        s = self.current_settings
        self.autolock_edit.setText(str(s.get("auto_lock_timeout", 0)))
        self.clipboard_edit.setText(str(s.get("clipboard_clear_timeout", 0)))
        dmode = s.get("otp_display_mode", "show")
        self.otp_display_combo.setCurrentIndex(0 if dmode == "show" else 1)
        theme = s.get("theme", "system")
        idx = {"system": 0, "light": 1, "dark": 2}.get(theme, 0)
        self.theme_combo.setCurrentIndex(idx)

    def apply_theme(self):
        """Apply the selected theme to the dialog."""
        theme = get_theme(self.current_settings.get("theme", "system"))
        apply_palette(theme)
        self.setStyleSheet(get_stylesheet(theme))

    def on_save(self):
        """Handle saving settings and password change."""
        old_pw = self.old_pw.text().strip()
        new_pw = self.new_pw.text().strip()
        conf_pw = self.conf_pw.text().strip()
        if old_pw or new_pw or conf_pw:
            if not old_pw or not new_pw or not conf_pw:
                QMessageBox.warning(
                    self, "Error", "Fill all password fields to change password."
                )
                return
            if new_pw != conf_pw:
                QMessageBox.warning(self, "Error", "New passwords do not match.")
                return
            if not is_strong_password(new_pw):
                QMessageBox.warning(
                    self,
                    "Weak Password",
                    "Password must be at least 8 characters and include upper, lower, and digit.",
                )
                return
            self.current_settings["pending_old_master_pw"] = old_pw
            self.current_settings["pending_new_master_pw"] = new_pw

        try:
            auto_lock = int(self.autolock_edit.text())
            if auto_lock < 0 or auto_lock > 120:
                raise ValueError
            self.current_settings["auto_lock_timeout"] = auto_lock
        except ValueError:
            QMessageBox.warning(self, "Error", "Auto-lock timeout must be 0-120.")
            return

        try:
            clipboard_timeout = int(self.clipboard_edit.text())
            if clipboard_timeout < 0 or clipboard_timeout > 120:
                raise ValueError
            self.current_settings["clipboard_clear_timeout"] = clipboard_timeout
        except ValueError:
            QMessageBox.warning(self, "Error", "Clipboard timeout must be 0-120.")
            return

        self.current_settings["otp_display_mode"] = (
            "show" if self.otp_display_combo.currentIndex() == 0 else "hide"
        )
        theme_idx = self.theme_combo.currentIndex()
        theme_val = ["system", "light", "dark"][theme_idx]
        self.current_settings["theme"] = theme_val
        self.accept()
