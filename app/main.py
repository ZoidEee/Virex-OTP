import sys
import time
import cv2
import pyotp
from PySide6.QtCore import Qt, QTimer, QRect, QSize, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QInputDialog,
    QPushButton,
    QLineEdit,
    QLabel,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
    QScrollArea,
    QMessageBox,
    QGraphicsDropShadowEffect,
    QFileDialog,
    QFrame,
    QDialog,
)
from pyzbar.pyzbar import decode
from app.theme import get_theme, apply_palette, get_stylesheet
from app.settings import (
    SettingsDialog,
    load_settings,
    save_settings,
    DEFAULT_SETTINGS,
)
from app.helpers import (
    prompt_for_password,
    save_accounts,
    load_accounts,
    check_master_password,
    set_master_password,
    parse_account_label,
    clear_clipboard,
    export_accounts_csv,
    import_accounts_csv,
    process_decoded_qr_data,
    export_accounts_encrypted,
    import_accounts_encrypted,
)


class NewPopup(QInputDialog):
    """Custom popup for text input."""

    def __init__(self, prompt, title="Input"):
        super().__init__()
        self.setWindowTitle(title)
        self.setLabelText(prompt)
        self.setOkButtonText("Next")
        self.setCancelButtonText("Cancel")
        self.resize(400, 120)


class CircularCountdown(QWidget):
    """Circular countdown widget for TOTP interval."""

    def __init__(self, interval=30, parent=None):
        super().__init__(parent)
        self.interval = interval
        self.value = interval
        self.setFixedSize(60, 60)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def update_value(self, value):
        self.value = value
        self.update()

    def paintEvent(self, event):
        size = min(self.width(), self.height())
        rect = QRect(4, 4, size - 8, size - 8)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#E0E0E0"), 5))
        painter.drawEllipse(rect)
        angle_span = 360 * (self.value / self.interval)
        painter.setPen(QPen(QColor("#6C4CE0"), 4))
        painter.drawArc(rect, 90 * 16, -int(angle_span * 16))
        painter.setPen(QColor("#6C4CE0"))
        font = QFont("Arial", 15, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, f"{self.value}")


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


class OtpCard(QWidget):
    """Widget for displaying an OTP account."""

    edit_requested = Signal(object)  # Emits self
    delete_requested = Signal(object)  # Emits self

    def __init__(
        self, account_name, user, totp, interval=30, parent=None, icon_set="light"
    ):
        super().__init__(parent)
        self.account_name = account_name
        self.user = user
        self.totp = totp
        self.interval = interval
        self.code_hidden = False
        self.setFixedSize(300, 100)
        self.icon_set = icon_set
        self.init_ui()
        self.setStyleSheet(
            """
            #frame {
                border-top: 1px solid #E0E0E0;
            }
            #label_account, #label_user, #label_current {
                background-color: transparent;
                border: none;
            }
            #label_current {
                letter-spacing: 2px;
            }
            #toggle_button, #copy_button {
                background-color: transparent;
                border: none;
            }
            """
        )
        shadow = QGraphicsDropShadowEffect()
        shadow.setColor(QColor(100, 100, 100, 50))
        shadow.setBlurRadius(14)
        shadow.setOffset(0, 4)
        self.frame.setGraphicsEffect(shadow)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_totp)
        self.timer.start(1000)
        self.update_totp()

    def init_ui(self):
        self.frame = QFrame(self)
        self.frame.setObjectName("frame")
        self.frame.setFixedSize(300, 100)
        main_layout = QHBoxLayout(self.frame)
        main_layout.setContentsMargins(10, 0, 10, 0)
        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 5)
        info_layout.setSpacing(0)
        info_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.label_account = QLabel(self.account_name)
        self.label_account.setObjectName("label_account")
        self.label_account.setFixedHeight(25)
        self.label_account.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.label_account.setFont(QFont("Times", 12))
        self.label_user = QLabel(self.user)
        self.label_user.setObjectName("label_user")
        self.label_user.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.label_user.setFixedHeight(25)
        self.label_user.setFont(QFont("Times", 9))
        self.label_current = QLabel("-- -- --")
        self.label_current.setObjectName("label_current")
        self.label_current.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.label_current.setFixedHeight(25)
        self.label_current.setFont(QFont("Times", 15))
        info_layout.addWidget(self.label_account)
        info_layout.addWidget(self.label_user)
        info_layout.addWidget(self.label_current)
        main_layout.addLayout(info_layout)
        self.countdown_circle = CircularCountdown(self.interval)
        main_layout.addWidget(self.countdown_circle)
        functions_layout = QVBoxLayout()
        functions_layout.setContentsMargins(0, 0, 0, 0)
        functions_layout.setSpacing(0)
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.options_button = QPushButton()
        self.options_button.setStyleSheet(
            "border: none; background-color: transparent;"
        )
        self.options_button.setObjectName("options_button")
        self.options_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.options_button.setIcon(QIcon(f"images/{self.icon_set}-options-16.png"))
        self.options_button.setIconSize(QSize(20, 20))
        self.options_button.setFixedSize(30, 30)
        self.options_button.clicked.connect(self.show_options_dialog)
        top_layout.addWidget(self.options_button)
        functions_layout.addLayout(top_layout)
        bottom_layout = QHBoxLayout()
        bottom_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bottom_layout.setContentsMargins(0, 0, 0, 15)
        self.toggle_button = QPushButton()
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
        bottom_layout.addWidget(self.toggle_button)
        self.copy_button = QPushButton()
        self.copy_button.setObjectName("copy_button")
        self.copy_button.setCursor(Qt.CursorShape.PointingHandCursor)
        icon_copy = QIcon(f"images/{self.icon_set}-copy-24.png")
        self.copy_button.setIcon(icon_copy)
        self.copy_button.setIconSize(QSize(20, 20))
        self.copy_button.setFixedSize(30, 30)
        self.copy_button.clicked.connect(self.copy_to_clipboard)
        bottom_layout.addWidget(self.copy_button)
        functions_layout.addLayout(bottom_layout)
        main_layout.addLayout(functions_layout)

    def show_options_dialog(self):
        dlg = OptionsDialog(self.account_name, self)
        result = dlg.exec()
        if result == QDialog.DialogCode.Accepted:
            self.edit_requested.emit(self)
        elif result == QDialog.DialogCode.Rejected:
            self.delete_requested.emit(self)

    def toggle_code_visibility(self):
        if self.code_hidden:
            try:
                current = self.totp.now()
            except Exception:
                current = "-- -- --"
            self.label_current.setText(" ".join([current[:3], current[3:]]))
            self.toggle_button.setIcon(self.icon_hide)
            self.code_hidden = False
        else:
            self.label_current.setText("*** ***")
            self.toggle_button.setIcon(self.icon_show)
            self.code_hidden = True

    def update_totp(self):
        now = int(time.time())
        elapsed = now % self.interval
        remaining = self.interval - elapsed
        self.countdown_circle.update_value(remaining)
        if not self.code_hidden:
            try:
                current = self.totp.now()
            except Exception:
                current = "-- -- --"
            self.label_current.setText(" ".join([current[:3], current[3:]]))

    def update_icons(self, icon_set):
        self.icon_set = icon_set
        self.options_button.setIcon(QIcon(f"images/{self.icon_set}-options-16.png"))
        self.icon_hide = QIcon(f"images/{self.icon_set}-hide-24.png")
        self.icon_show = QIcon(f"images/{self.icon_set}-show-24.png")
        self.toggle_button.setIcon(
            self.icon_hide if not self.code_hidden else self.icon_show
        )
        self.copy_button.setIcon(QIcon(f"images/{self.icon_set}-copy-24.png"))

    def copy_to_clipboard(self):
        try:
            current = self.totp.now()
        except Exception:
            current = ""
        clipboard = QApplication.clipboard()
        clipboard.setText(current)


class Virex(QMainWindow):
    """Main application window for Virex OTP."""

    def __init__(self, master_pw):
        super().__init__()
        self.master_pw = master_pw
        self.accounts = load_accounts()
        self.cards = []
        self.settings = load_settings()
        self.clipboard_clear_timer = None
        self.auto_lock_timer = None
        self.setup_auto_lock()
        self.apply_theme()
        self.init_ui()
        clip_timeout = self.settings.get("clipboard_clear_timeout", 0)
        if clip_timeout > 0:
            self.clipboard_clear_timer = QTimer(self)
            self.clipboard_clear_timer.timeout.connect(self.clear_clipboard)
            self.clipboard_clear_timer.start(clip_timeout * 1000)
        self.last_theme = get_theme(self.settings.get("theme", "system"))
        self.theme_check_timer = QTimer(self)
        self.theme_check_timer.timeout.connect(self.check_system_theme)
        self.theme_check_timer.start(2000)

    def save_settings(self):
        save_settings(self.settings)

    def init_ui(self):
        self.setWindowTitle("Virex")
        self.setFixedSize(350, 550)
        self.setup_mainwindow()
        self.refresh_tiles()

    def setup_mainwindow(self):
        self.btn_new = QPushButton()
        self.btn_new.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_new.setStyleSheet("background-color: transparent; border: none;")
        self.btn_new.setIcon(QIcon(f"images/{self.icon_set}-plus-24.png"))
        self.btn_new.setIconSize(QSize(20, 20))
        self.btn_new.setFixedSize(25, 25)
        self.btn_new.clicked.connect(self.show_new_options)
        search_bar = QLineEdit()
        self.search_bar = search_bar
        search_bar.setPlaceholderText("Search...")
        search_bar.textChanged.connect(self.filter_cards)
        self.btn_settings = QPushButton()
        self.btn_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_settings.setStyleSheet("background-color: transparent; border: none;")
        self.btn_settings.setIcon(QIcon(f"images/{self.icon_set}-settings-24.png"))
        self.btn_settings.setIconSize(QSize(20, 20))
        self.btn_settings.setFixedSize(25, 25)
        self.btn_settings.clicked.connect(self.show_settings_options)
        top_layout = QHBoxLayout()
        top_layout.addWidget(self.btn_new)
        top_layout.addWidget(search_bar)
        top_layout.addWidget(self.btn_settings)
        self.grid_layout = QVBoxLayout()
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.grid_layout.setSpacing(2)
        scroll_area = QScrollArea()
        container = QWidget()
        container.setLayout(self.grid_layout)
        scroll_area.setWidget(container)
        scroll_area.setWidgetResizable(True)
        main_layout = QVBoxLayout()
        main_layout.addLayout(top_layout)
        main_layout.addWidget(scroll_area)
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

    def refresh_tiles(self):
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.cards.clear()
        for account in self.accounts:
            if "key_uri" in account:
                acc_name, user = parse_account_label(account["key_uri"])
                totp = pyotp.parse_uri(account["key_uri"])
            else:
                acc_name = account.get("name", "Unknown")
                user = ""
                totp = pyotp.TOTP(account.get("secret", ""))
            card = OtpCard(acc_name, user, totp, icon_set=self.icon_set)
            card.edit_requested.connect(self.edit_account)
            card.delete_requested.connect(self.delete_account)
            self.grid_layout.addWidget(card)
            self.cards.append(card)
        if hasattr(self, "search_bar"):
            self.filter_cards(self.search_bar.text())

    def edit_account(self, card):
        idx = self.cards.index(card)
        account = self.accounts[idx]
        name, ok = QInputDialog.getText(
            self, "Edit Account Name", "Account Name:", text=account.get("name", "")
        )
        if ok and name:
            account["name"] = name
            save_accounts(self.accounts)
            self.refresh_tiles()

    def delete_account(self, card):
        idx = self.cards.index(card)
        res = QMessageBox.question(
            self, "Delete Account", "Are you sure?", QMessageBox.Yes | QMessageBox.No
        )
        if res == QMessageBox.Yes:
            self.accounts.pop(idx)
            save_accounts(self.accounts)
            self.refresh_tiles()

    def setup_auto_lock(self):
        """Setup auto-lock timer based on settings."""
        timeout = self.settings.get("auto_lock_timeout", 0)
        if timeout > 0:
            if self.auto_lock_timer:
                self.auto_lock_timer.stop()
            self.auto_lock_timer = QTimer(self)
            self.auto_lock_timer.timeout.connect(self.lock_app)
            self.auto_lock_timer.start(timeout * 60 * 1000)
            self.installEventFilter(self)
        else:
            if self.auto_lock_timer:
                self.auto_lock_timer.stop()
                self.auto_lock_timer = None

    def eventFilter(self, obj, event):
        """Reset auto-lock timer on user activity."""
        if self.auto_lock_timer and event.type() in [2, 3, 4, 5, 6, 7, 8, 9, 10, 11]:
            self.auto_lock_timer.start(
                self.settings.get("auto_lock_timeout", 0) * 60 * 1000
            )
        return super().eventFilter(obj, event)

    def lock_app(self):
        """Lock the app and prompt for master password."""
        pw = prompt_for_password()
        if not check_master_password(pw):
            QMessageBox.warning(self, "Locked", "Incorrect password. Exiting.")
            QApplication.quit()
        else:
            self.master_pw = pw

    def show_settings_options(self):
        dlg = SettingsDialog(self.settings, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            if "pending_new_master_pw" in self.settings:
                if not check_master_password(
                    self.settings.get("pending_old_master_pw")
                ):
                    QMessageBox.warning(
                        self, "Password Error", "Current master password incorrect."
                    )
                    return
                set_master_password(self.settings["pending_new_master_pw"])
                self.master_pw = self.settings["pending_new_master_pw"]
                self.settings.pop("pending_new_master_pw", None)
                self.settings.pop("pending_old_master_pw", None)
                QMessageBox.information(
                    self, "Password Changed", "Master password changed successfully!"
                )
            clip_timeout = self.settings.get("clipboard_clear_timeout", 0)
            self.setup_auto_lock()
            if self.clipboard_clear_timer:
                self.clipboard_clear_timer.stop()
            if clip_timeout > 0:
                self.clipboard_clear_timer = QTimer(self)
                self.clipboard_clear_timer.timeout.connect(self.clear_clipboard)
                self.clipboard_clear_timer.start(clip_timeout * 1000)
            if getattr(dlg, "backup_requested", False):
                self.export_accounts_csv()
            if getattr(dlg, "restore_requested", False):
                self.import_csv()
            if getattr(dlg, "encrypted_backup_requested", False):
                self.export_accounts_encrypted()
            if getattr(dlg, "encrypted_restore_requested", False):
                self.import_accounts_encrypted()
            if getattr(dlg, "reset_requested", False):
                self.reset_all_data()
            self.save_settings()
            self.apply_theme()
            self.refresh_tiles()

    def apply_theme(self):
        theme = get_theme(self.settings.get("theme", "system"))
        self.icon_set = "light" if theme == "dark" else "dark"
        apply_palette(theme)
        self.setStyleSheet(get_stylesheet(theme))
        if hasattr(self, "btn_new"):
            self.btn_new.setIcon(QIcon(f"images/{self.icon_set}-plus-24.png"))
        if hasattr(self, "btn_settings"):
            self.btn_settings.setIcon(QIcon(f"images/{self.icon_set}-settings-24.png"))
        for card in getattr(self, "cards", []):
            card.update_icons(self.icon_set)
        self.last_theme = theme

    def check_system_theme(self):
        if self.settings.get("theme", "system") == "system":
            current_theme = get_theme("system")
            if current_theme != self.last_theme:
                self.apply_theme()
                self.refresh_tiles()

    def clear_clipboard(self):
        clear_clipboard()

    def reset_all_data(self):
        self.accounts.clear()
        save_accounts(self.accounts)
        self.settings = DEFAULT_SETTINGS.copy()
        self.save_settings()
        self.refresh_tiles()
        QMessageBox.information(
            self, "Data Reset", "All accounts and settings have been reset."
        )

    def export_accounts_csv(self):
        if not self.accounts:
            QMessageBox.information(self, "Export", "No accounts to export.")
            return
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export OTP Entries to CSV", "", "CSV Files (*.csv)"
        )
        if filename:
            success, error = export_accounts_csv(self.accounts, filename)
            if success:
                QMessageBox.information(
                    self, "Export Successful", "OTP accounts exported successfully!"
                )
            else:
                QMessageBox.warning(
                    self, "Export Failed", f"Failed to export to CSV file:\n{error}"
                )

    def import_csv(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Import OTP Entries from CSV", "", "CSV Files (*.csv)"
        )
        if filename:
            imported_accounts, error = import_accounts_csv(filename)
            if error:
                QMessageBox.warning(
                    self, "Import Failed", f"Failed to import CSV file:\n{error}"
                )
                return
            imported_count = 0
            for account in imported_accounts:
                self.accounts.append(account)
                imported_count += 1
            if imported_count > 0:
                save_accounts(self.accounts)
                self.refresh_tiles()
                QMessageBox.information(
                    self,
                    "Import Successful",
                    f"{imported_count} accounts imported successfully!",
                )
            else:
                QMessageBox.information(
                    self, "Import", "No new accounts found in file."
                )

    def filter_cards(self, text):
        search_text = text.lower()
        for card in self.cards:
            if (
                search_text in card.account_name.lower()
                or search_text in card.user.lower()
            ):
                card.show()
            else:
                card.hide()

    def show_new_options(self):
        options = [
            "Enter Secret Key",
            "Enter Key URI",
            "Import from CSV file",
            "Scan QR Code with Camera",
            "Import QR Code Image",
        ]
        option, ok = QInputDialog.getItem(
            self, "Add New OTP", "Choose method to add OTP:", options, 0, False
        )
        if not ok:
            return
        if option == "Enter Secret Key":
            self.prompt_secret_key()
        elif option == "Enter Key URI":
            self.prompt_key_uri()
        elif option == "Import from CSV file":
            self.import_csv()
        elif option == "Scan QR Code with Camera":
            self.scan_qr_code_camera()
        elif option == "Import QR Code Image":
            self.import_qr_image()

    def scan_qr_code_camera(self):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            QMessageBox.warning(self, "Camera Error", "Could not open camera.")
            return
        QMessageBox.information(
            self, "Camera Scan", "Press 'q' to capture and decode a QR code."
        )
        decoded_data = None
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            cv2.imshow('QR Code Scanner - Press "q" to scan', frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                decoded_objs = decode(frame)
                if decoded_objs:
                    decoded_data = decoded_objs[0].data.decode()
                break
        cap.release()
        cv2.destroyAllWindows()
        if decoded_data:
            self.handle_decoded_qr_data(decoded_data)
        else:
            QMessageBox.warning(self, "Scan Failed", "No QR code detected.")

    def import_qr_image(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Import QR Code Image", "", "Image Files (*.png *.jpg *.bmp)"
        )
        if not filename:
            return
        try:
            img = cv2.imread(filename)
            decoded_objs = decode(img)
            if decoded_objs:
                decoded_data = decoded_objs[0].data.decode()
                self.handle_decoded_qr_data(decoded_data)
            else:
                QMessageBox.warning(
                    self, "Decode Failed", "No QR code found in the image."
                )
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to decode QR code:\n{e}")

    def handle_decoded_qr_data(self, data):
        account_entry = process_decoded_qr_data(data)
        if "key_uri" in account_entry:
            popup_name = NewPopup(
                "Enter account name for scanned Key URI:", "Account Name Entry"
            )
        else:
            popup_name = NewPopup(
                "Enter account name for scanned secret key:", "Account Name Entry"
            )
        if popup_name.exec() == QInputDialog.DialogCode.Accepted:
            account_name = popup_name.textValue().strip()
            if account_name:
                account_entry["name"] = account_name
                self.accounts.append(account_entry)
                save_accounts(self.accounts)
                self.refresh_tiles()

    def edit_account(self, card):
        idx = self.cards.index(card)
        account = self.accounts[idx]
        name, ok = QInputDialog.getText(
            self, "Edit Account Name", "Account Name:", text=account.get("name", "")
        )
        if ok and name:
            account["name"] = name
            save_accounts(self.accounts)
            self.refresh_tiles()

    def delete_account(self, card):
        idx = self.cards.index(card)
        res = QMessageBox.question(
            self, "Delete Account", "Are you sure?", QMessageBox.Yes | QMessageBox.No
        )
        if res == QMessageBox.Yes:
            self.accounts.pop(idx)
            save_accounts(self.accounts)
            self.refresh_tiles()

    def prompt_secret_key(self):
        popup = NewPopup("Enter secret key (Base32):", "Secret Key Entry")
        if popup.exec() == QInputDialog.DialogCode.Accepted:
            secret = popup.textValue().strip()
            # Account validation
            if not secret or not pyotp.utils.is_base32(secret):
                QMessageBox.warning(
                    self, "Invalid Secret", "Secret must be valid Base32."
                )
                return
            popup_name = NewPopup(
                "Enter account name for this secret:", "Account Name Entry"
            )
            if popup_name.exec() == QInputDialog.DialogCode.Accepted:
                account_name = popup_name.textValue().strip()
                if account_name:
                    self.accounts.append({"name": account_name, "secret": secret})
                    save_accounts(self.accounts)
                    self.refresh_tiles()

    def prompt_key_uri(self):
        popup = NewPopup("Enter the Key URI (otpauth URI):", "Key URI Entry")
        if popup.exec() == QInputDialog.DialogCode.Accepted:
            key_uri = popup.textValue().strip()
            # Account validation
            if not key_uri.startswith("otpauth://"):
                QMessageBox.warning(
                    self, "Invalid URI", "Key URI must start with otpauth://"
                )
                return
            try:
                pyotp.parse_uri(key_uri)
            except Exception:
                QMessageBox.warning(self, "Invalid URI", "Key URI is not valid.")
                return
            popup_name = NewPopup(
                "Enter account name for this Key URI:", "Account Name Entry"
            )
            if popup_name.exec() == QInputDialog.DialogCode.Accepted:
                account_name = popup_name.textValue().strip()
                if account_name:
                    self.accounts.append({"name": account_name, "key_uri": key_uri})
                    save_accounts(self.accounts)
                    self.refresh_tiles()

    def export_accounts_encrypted(self):
        if not self.accounts:
            QMessageBox.information(self, "Export", "No accounts to export.")
            return
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Encrypted OTP Entries", "", "Encrypted Files (*.bin)"
        )
        if filename:
            pw, ok = QInputDialog.getText(
                self,
                "Backup Password",
                "Enter password for encryption:",
                QLineEdit.EchoMode.Password,
            )
            if not ok or not pw:
                QMessageBox.warning(self, "Export Cancelled", "No password entered.")
                return
            success, error = export_accounts_encrypted(self.accounts, filename, pw)
            if success:
                QMessageBox.information(
                    self, "Export Successful", "Accounts exported (encrypted)!"
                )
            else:
                QMessageBox.warning(self, "Export Failed", f"Error:\n{error}")

    def import_accounts_encrypted(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Import Encrypted OTP Entries", "", "Encrypted Files (*.bin)"
        )
        if filename:
            pw, ok = QInputDialog.getText(
                self,
                "Restore Password",
                "Enter password for decryption:",
                QLineEdit.EchoMode.Password,
            )
            if not ok or not pw:
                QMessageBox.warning(self, "Import Cancelled", "No password entered.")
                return
            imported_accounts, error = import_accounts_encrypted(filename, pw)
            if error:
                QMessageBox.warning(self, "Import Failed", f"Error:\n{error}")
                return
            imported_count = 0
            for account in imported_accounts:
                self.accounts.append(account)
                imported_count += 1
            if imported_count > 0:
                save_accounts(self.accounts)
                self.refresh_tiles()
                QMessageBox.information(
                    self, "Import Successful", f"{imported_count} accounts imported!"
                )
            else:
                QMessageBox.information(self, "Import", "No new accounts found.")

    def closeEvent(self, event):
        self.save_settings()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Virex(prompt_for_password())
    window.show()
    sys.exit(app.exec())
