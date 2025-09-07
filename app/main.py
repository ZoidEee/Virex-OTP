import sys
import os
import cv2
import pyotp
from PySide6.QtCore import Qt, QTimer, QSize, QPoint, QEvent
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QInputDialog,
    QPushButton,
    QLineEdit,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
    QScrollArea,
    QMessageBox,
    QMenu,
    QFileDialog,
    QDialog, QSystemTrayIcon,
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
    export_accounts_csv,
    import_accounts_csv,
    process_decoded_qr_data,
    export_accounts_encrypted,
    import_accounts_encrypted,
)
from app.about import AboutDialog
from app.widgets import (
    OtpCard,
    NewPopup,
    CameraScannerDialog,
)


class Virex(QMainWindow):
    """Main application window for Virex OTP."""

    def __init__(self, master_pw):
        super().__init__()
        self.master_pw = master_pw
        self.accounts = load_accounts(self.master_pw)
        self.cards = []
        self.last_copied_code = None
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
        self.setup_tray_icon()
        self.refresh_tiles()

    def setup_mainwindow(self):
        self.btn_new = QPushButton()
        self.btn_new.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_new.setObjectName("transparentButton")
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
        self.btn_settings.setObjectName("transparentButton")
        self.btn_settings.setIcon(QIcon(f"images/{self.icon_set}-settings-24.png"))
        self.btn_settings.setIconSize(QSize(20, 20))
        self.btn_settings.setFixedSize(25, 25)
        self.btn_settings.clicked.connect(self.show_settings_menu)
        top_layout = QHBoxLayout()
        top_layout.addWidget(self.btn_new)
        top_layout.addWidget(search_bar)
        top_layout.addWidget(self.btn_settings)


        self.grid_layout = QVBoxLayout()
        scroll_area = QScrollArea()
        container = QWidget()
        container.setLayout(self.grid_layout)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scroll_area.setWidget(container)
        scroll_area.setWidgetResizable(True)


        main_layout = QVBoxLayout()
        main_layout.addLayout(top_layout)
        main_layout.addWidget(scroll_area)
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

    def refresh_tiles(self):
        for card in self.cards:
            self.grid_layout.removeWidget(card)
            card.deleteLater()
        self.cards.clear()

        start_hidden = self.settings.get("otp_display_mode") == "hide"

        for account in self.accounts:
            card = OtpCard(account, icon_set=self.icon_set, start_hidden=start_hidden)
            card.edit_requested.connect(self.edit_account)
            card.delete_requested.connect(self.delete_account)
            self.grid_layout.addWidget(card)
            self.cards.append(card)

        if hasattr(self, "search_bar"):
            self.filter_cards(self.search_bar.text())

    def edit_account(self, card):
        idx = self.cards.index(card)
        account = self.accounts[idx]
        popup = NewPopup("Edit Account Name:", "Edit Account")
        popup.setTextValue(account.get("name", ""))
        if popup.exec() == QDialog.DialogCode.Accepted and popup.textValue():
            account["name"] = popup.textValue()
            save_accounts(self.accounts, self.master_pw)
            self.refresh_tiles()

    def delete_account(self, card):
        idx = self.cards.index(card)
        res = QMessageBox.question(
            self, "Delete Account", "Are you sure?", QMessageBox.Yes | QMessageBox.No
        )
        if res == QMessageBox.Yes:
            self.accounts.pop(idx)
            save_accounts(self.accounts, self.master_pw)
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
        for card in self.cards:
            if not card.code_hidden:
                card.toggle_code_visibility()

        while True:
            pw, ok = QInputDialog.getText(
                self,
                "Application Locked",
                "Enter master password to unlock:",
                echo=QLineEdit.EchoMode.Password,
            )
            if not ok:
                QApplication.quit()
                return
            if check_master_password(pw):
                self.master_pw = pw
                if self.auto_lock_timer:
                    self.auto_lock_timer.start()
                start_hidden = self.settings.get("otp_display_mode") == "hide"
                for card in self.cards:
                    if card.code_hidden and not start_hidden:
                        card.toggle_code_visibility()
                return
            QMessageBox.warning(self, "Unlock Failed", "Incorrect password.")

    def show_settings_menu(self):
        """Create and show a dropdown menu for the settings button."""
        menu = QMenu(self)

        preferences_action = menu.addAction("Preferences...")
        preferences_action.triggered.connect(self.show_settings_dialog)

        menu.addSeparator()

        export_csv_action = menu.addAction("Export to CSV...")
        export_csv_action.triggered.connect(self.export_accounts_csv)

        export_enc_action = menu.addAction("Export Encrypted Backup...")
        export_enc_action.triggered.connect(self.export_accounts_encrypted)

        import_enc_action = menu.addAction("Import Encrypted Backup...")
        import_enc_action.triggered.connect(self.import_accounts_encrypted)

        about_action = menu.addAction("About Virex OTP")
        about_action.triggered.connect(self.show_about_dialog)

        menu.addSeparator()

        reset_action = menu.addAction("Reset All Data...")
        reset_action.triggered.connect(self.handle_reset_request)

        button_pos = self.btn_settings.mapToGlobal(QPoint(0, 0))
        menu_pos = QPoint(button_pos.x(), button_pos.y() + self.btn_settings.height())
        menu.exec(menu_pos)

    def show_about_dialog(self):
        dlg = AboutDialog(self)
        dlg.exec()

    def show_settings_dialog(self):
        dlg = SettingsDialog(self.settings, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            old_pw = dlg.old_pw.text()
            new_pw = dlg.new_pw.text()
            if old_pw and new_pw:
                if not check_master_password(old_pw):
                    QMessageBox.warning(
                        self, "Password Error", "Current master password incorrect."
                    )
                else:
                    set_master_password(new_pw)
                    self.master_pw = new_pw
                    save_accounts(self.accounts, self.master_pw)
                    QMessageBox.information(
                        self,
                        "Password Changed",
                        "Master password changed successfully!",
                    )

            self.settings = dlg.current_settings
            clip_timeout = self.settings.get("clipboard_clear_timeout", 0)
            self.setup_auto_lock()
            if self.clipboard_clear_timer:
                self.clipboard_clear_timer.stop()
            if clip_timeout > 0:
                self.clipboard_clear_timer = QTimer(self)
                self.clipboard_clear_timer.timeout.connect(self.clear_clipboard)
                self.clipboard_clear_timer.start(clip_timeout * 1000)
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
        clipboard = QApplication.clipboard()
        if self.last_copied_code and clipboard.text() == self.last_copied_code:
            clipboard.clear()
            self.last_copied_code = None

    def handle_reset_request(self):
        """Confirm and trigger reset of all data."""
        res = QMessageBox.question(
            self,
            "Confirm Reset",
            "This will delete all accounts and reset all settings. Are you sure?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if res == QMessageBox.StandardButton.Yes:
            self._reset_all_data()

    def _reset_all_data(self):
        self.accounts.clear()
        save_accounts(self.accounts, self.master_pw)
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
            try:
                export_accounts_csv(self.accounts, filename)
                QMessageBox.information(
                    self, "Export Successful", "OTP accounts exported successfully!"
                )
            except Exception as e:
                QMessageBox.warning(
                    self, "Export Failed", f"Failed to export to CSV file:\n{e}"
                )

    def import_csv(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Import OTP Entries from CSV", "", "CSV Files (*.csv)"
        )
        if filename:
            try:
                imported_accounts = import_accounts_csv(filename)
            except Exception as e:
                QMessageBox.warning(
                    self, "Import Failed", f"Failed to import CSV file:\n{e}"
                )
                return
            imported_count = 0
            for account in imported_accounts:
                self.accounts.append(account)
                imported_count += 1
            if imported_count > 0:
                save_accounts(self.accounts, self.master_pw)
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
        dlg = CameraScannerDialog(self)
        if not dlg.cap.isOpened():
            QMessageBox.warning(self, "Camera Error", "Could not open camera.")
            return

        if dlg.exec() == QDialog.DialogCode.Accepted:
            if dlg.decoded_data:
                self.handle_decoded_qr_data(dlg.decoded_data)
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
                save_accounts(self.accounts, self.master_pw)
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
                    save_accounts(self.accounts, self.master_pw)
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
                    save_accounts(self.accounts, self.master_pw)
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
            try:
                export_accounts_encrypted(self.accounts, filename, pw)
                QMessageBox.information(
                    self, "Export Successful", "Accounts exported (encrypted)!"
                )
            except Exception as e:
                QMessageBox.warning(self, "Export Failed", f"Error:\n{e}")

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
            try:
                imported_accounts = import_accounts_encrypted(filename, pw)
            except Exception as e:
                QMessageBox.warning(self, "Import Failed", f"Error:\n{e}")
                return
            imported_count = 0
            for account in imported_accounts:
                self.accounts.append(account)
                imported_count += 1
            if imported_count > 0:
                save_accounts(self.accounts, self.master_pw)
                self.refresh_tiles()
                QMessageBox.information(
                    self, "Import Successful", f"{imported_count} accounts imported!"
                )
            else:
                QMessageBox.information(self, "Import", "No new accounts found.")

    def setup_tray_icon(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(script_dir, "..", "images", "icon.png")
        self.tray_icon = QSystemTrayIcon(QIcon(icon_path), self)
        self.tray_icon.setToolTip("Virex OTP")
        tray_menu = QMenu()
        show_action = tray_menu.addAction("Show/Hide")
        show_action.triggered.connect(self.toggle_visibility)
        quit_action = tray_menu.addAction("Quit")
        quit_action.triggered.connect(QApplication.quit)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        self.tray_icon.activated.connect(self.on_tray_icon_activated)

    def on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.toggle_visibility()

    def toggle_visibility(self):
        self.setVisible(not self.isVisible())

    def closeEvent(self, event):
        event.ignore()
        self.hide()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Virex(prompt_for_password())
    window.show()
    sys.exit(app.exec())
