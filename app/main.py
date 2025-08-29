import sys
import time
from urllib.parse import unquote, urlparse

import csv
import cv2
import pyotp
from PySide6.QtCore import Qt, QTimer, QRect, QSize
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
)
from pyzbar.pyzbar import decode

from helpers import prompt_for_password, save_accounts, load_accounts


class NewPopup(QInputDialog):
    """Popup dialog to get user input with configurable prompt and title."""

    def __init__(self, prompt, title="Input"):
        super().__init__()
        self.setWindowTitle(title)
        self.setLabelText(prompt)
        self.setOkButtonText("Next")
        self.setCancelButtonText("Cancel")
        self.resize(400, 120)


class CircularCountdown(QWidget):
    """Widget for displaying a circular countdown timer."""

    def __init__(self, interval=30, parent=None):
        super().__init__(parent)
        self.interval = interval
        self.value = interval
        self.setFixedSize(60, 60)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def update_value(self, value):
        """Update the countdown value and refresh the widget."""
        self.value = value
        self.update()

    def paintEvent(self, event):
        """Draw the countdown circle and remaining seconds."""
        size = min(self.width(), self.height())
        rect = QRect(4, 4, size - 8, size - 8)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw background circle in grey
        painter.setPen(QPen(QColor("#E0E0E0"), 5))
        painter.drawEllipse(rect)

        # Draw the purple arc representing the remaining time
        angle_span = 360 * (self.value / self.interval)
        painter.setPen(QPen(QColor("#6C4CE0"), 4))
        painter.drawArc(rect, 90 * 16, -int(angle_span * 16))

        # Draw remaining seconds text in the center
        painter.setPen(QColor("#6C4CE0"))
        font = QFont("Arial", 15, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, f"{self.value}")


class OtpCard(QWidget):
    """Card widget displaying an OTP account with current TOTP code and rounded border."""

    def __init__(
        self, account_name, user, totp, interval=30, logo_path=None, parent=None
    ):
        super().__init__(parent)
        self.account_name = account_name
        self.user = user
        self.totp = totp
        self.interval = interval
        self.code_hidden = False
        self.setFixedSize(300, 75)

        self.init_ui()

        # Drop shadow on the outer frame
        shadow = QGraphicsDropShadowEffect()
        shadow.setColor(QColor(100, 100, 100, 50))
        shadow.setBlurRadius(14)
        shadow.setOffset(0, 4)
        self.frame.setGraphicsEffect(shadow)

        # Timer to update TOTP every second
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_totp)
        self.timer.start(1000)
        self.update_totp()

    def init_ui(self):
        """Initialize the UI components of the OTP card."""
        self.frame = QFrame(self)
        self.frame.setFixedSize(300, 75)
        self.frame.setStyleSheet(
            """
                background-color: #FFFFFF;
                border: 1.5px solid #CCCCCC;
                border-radius: 16px;
            
        """
        )

        main_layout = QHBoxLayout(self.frame)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 0, 10, 5)

        sub_layout = QVBoxLayout()
        sub_layout.setSpacing(0)
        sub_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.label_account = QLabel(self.account_name)
        self.label_account.setFixedHeight(25)
        self.label_account.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.label_account.setFont(QFont("Times", 12))
        self.label_account.setStyleSheet(
            "color: #000000; background-color: transparent;border: none;"
        )

        self.label_user = QLabel(self.user)
        self.label_user.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.label_user.setFixedHeight(25)
        self.label_user.setFont(QFont("Times", 9))
        self.label_user.setStyleSheet(
            "color: #000000; background-color: transparent; border: none;"
        )

        self.label_current = QLabel("-- -- --")
        self.label_current.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.label_current.setFixedHeight(25)
        self.label_current.setFont(QFont("Times", 15))
        self.label_current.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.label_current.setStyleSheet(
            "color: #000000; background-color: transparent; letter-spacing: 2px;border: none;"
        )

        sub_layout.addWidget(self.label_account)
        sub_layout.addWidget(self.label_user)
        sub_layout.addWidget(self.label_current)

        main_layout.addLayout(sub_layout)

        self.countdown_circle = CircularCountdown(self.interval)
        main_layout.addWidget(self.countdown_circle)

        self.toggle_button = QPushButton()
        self.toggle_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_button.setStyleSheet("background-color: transparent; border: none;")
        icon_hide = QIcon("images/hide-24.png")
        icon_show = QIcon("images/show-24.png")
        self.toggle_button.setIcon(icon_hide)
        self.toggle_button.setIconSize(QSize(20, 20))
        self.toggle_button.setFixedSize(25, 25)
        self.toggle_button.clicked.connect(self.toggle_code_visibility)

        self.icon_hide = icon_hide
        self.icon_show = icon_show

        main_layout.addWidget(self.toggle_button)

        self.copy_button = QPushButton()
        self.copy_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.copy_button.setStyleSheet("background-color: transparent; border: none;")
        icon_copy = QIcon("images/copy-24.png")
        self.copy_button.setIcon(icon_copy)
        self.copy_button.setIconSize(QSize(20, 20))
        self.copy_button.setFixedSize(25, 25)
        self.copy_button.clicked.connect(self.copy_to_clipboard)

        main_layout.addWidget(self.copy_button)

    def toggle_code_visibility(self):
        """Toggle showing/hiding the OTP code."""
        if self.code_hidden:
            # Show the code
            try:
                current = self.totp.now()
            except Exception:
                current = "-- -- --"
            self.label_current.setText(" ".join([current[:3], current[3:]]))
            self.toggle_button.setIcon(self.icon_hide)
            self.code_hidden = False
        else:
            # Hide the code
            self.label_current.setText("*** ***")
            self.toggle_button.setIcon(self.icon_show)
            self.code_hidden = True

    def update_totp(self):
        """Update TOTP code and countdown only if code is visible."""
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

    def copy_to_clipboard(self):
        """Copy the current OTP code to the clipboard."""
        try:
            current = self.totp.now()
        except Exception:
            current = ""
        clipboard = QApplication.clipboard()
        clipboard.setText(current)


class Virex(QMainWindow):
    """Main application window and controller for Virex OTP manager."""

    def __init__(self, master_pw):
        super().__init__()
        self.master_pw = master_pw
        self.accounts = load_accounts()
        self.cards = []
        self.init_ui()

    def init_ui(self):
        """Initialize the main UI window and refresh OTP cards."""
        self.setWindowTitle("Virex")
        self.setFixedSize(350, 500)
        self.setup_mainwindow()
        self.refresh_tiles()

    def setup_mainwindow(self):
        """Set up the main window layout with buttons and search bar."""
        btn_new = QPushButton()
        btn_new.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_new.setStyleSheet("background-color: transparent; border: none;")
        icon_new = QIcon("images/plus-50.png")
        btn_new.setIcon(icon_new)
        btn_new.setIconSize(QSize(20, 20))
        btn_new.setFixedSize(25, 25)
        btn_new.clicked.connect(self.show_new_options)

        search_bar = QLineEdit()
        self.search_bar = search_bar
        search_bar.setPlaceholderText("Search...")
        search_bar.textChanged.connect(self.filter_cards)
        btn_settings = QPushButton()
        btn_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_settings.setStyleSheet("background-color: transparent; border: none;")
        icon_settings = QIcon("images/settings-50.png")
        btn_settings.setIcon(icon_settings)
        btn_settings.clicked.connect(self.show_settings_options)
        btn_settings.setIconSize(QSize(20, 20))
        btn_settings.setFixedSize(25, 25)

        top_layout = QHBoxLayout()
        top_layout.addWidget(btn_new)
        top_layout.addWidget(search_bar)
        top_layout.addWidget(btn_settings)

        self.grid_layout = QVBoxLayout()
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.grid_layout.setSpacing(5)

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

    def parse_account_label(self, key_uri):
        """Parse account and user from a given otpauth URI."""
        try:
            path = urlparse(key_uri).path  # e.g., "/ExampleOrg:user@example.com"
            label = path.lstrip("/")
            if ":" in label:
                acc, user = label.split(":", 1)
            else:
                acc, user = label, ""
            return unquote(acc), unquote(user)
        except Exception:
            return "Unknown", ""

    def refresh_tiles(self):
        """Clear existing OTP cards and reload current accounts."""
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.cards.clear()

        for account in self.accounts:
            if "key_uri" in account:
                acc_name, user = self.parse_account_label(account["key_uri"])
                totp = pyotp.parse_uri(account["key_uri"])
            else:
                acc_name = account.get("name", "Unknown")
                user = ""
                totp = pyotp.TOTP(account.get("secret", ""))

            card = OtpCard(acc_name, user, totp, logo_path=None)
            self.grid_layout.addWidget(card)
            self.cards.append(card)

        if hasattr(self, "search_bar"):
            self.filter_cards(self.search_bar.text())

    def show_new_options(self):
        """Present user with different OTP adding options."""
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

    def prompt_secret_key(self):
        """Prompt user to manually enter a Base32 secret key and account name."""
        popup = NewPopup("Enter secret key (Base32):", "Secret Key Entry")
        if popup.exec() == QInputDialog.DialogCode.Accepted:
            secret = popup.textValue().strip()
            if secret:
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
        """Prompt user to enter a full otpauth URI and account name."""
        popup = NewPopup("Enter the Key URI (otpauth URI):", "Key URI Entry")
        if popup.exec() == QInputDialog.DialogCode.Accepted:
            key_uri = popup.textValue().strip()
            if key_uri:
                popup_name = NewPopup(
                    "Enter account name for this Key URI:", "Account Name Entry"
                )
                if popup_name.exec() == QInputDialog.DialogCode.Accepted:
                    account_name = popup_name.textValue().strip()
                    if account_name:
                        self.accounts.append({"name": account_name, "key_uri": key_uri})
                        save_accounts(self.accounts)
                        self.refresh_tiles()

    def import_csv(self):
        """Import OTP accounts from a CSV file with account and secret or URI."""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Import OTP Entries from CSV", "", "CSV Files (*.csv)"
        )
        if filename:
            try:
                imported_count = 0
                with open(filename, "r", newline="", encoding="utf-8") as f:
                    reader = csv.reader(f)
                    for row in reader:
                        if len(row) >= 2:
                            account_name, secret_or_uri = row[0].strip(), row[1].strip()
                            if not account_name or not secret_or_uri:
                                continue
                            if secret_or_uri.startswith("otpauth://"):
                                self.accounts.append({"name": account_name, "key_uri": secret_or_uri})
                            else:
                                self.accounts.append({"name": account_name, "secret": secret_or_uri})
                            imported_count += 1
                if imported_count > 0:
                    save_accounts(self.accounts)
                    self.refresh_tiles()
                    QMessageBox.information(
                        self, "Import Successful", f"{imported_count} accounts imported successfully!"
                    )
                else:
                    QMessageBox.information(self, "Import", "No new accounts found in file.")
            except Exception as e:
                QMessageBox.warning(
                    self, "Import Failed", f"Failed to import CSV file:\n{e}"
                )

    def scan_qr_code_camera(self):
        """Open the camera to scan a QR code and decode the OTP data."""
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
            self.process_decoded_qr_data(decoded_data)
        else:
            QMessageBox.warning(self, "Scan Failed", "No QR code detected.")

    def import_qr_image(self):
        """Import a QR code image file and decode the OTP data from it."""
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
                self.process_decoded_qr_data(decoded_data)
            else:
                QMessageBox.warning(
                    self, "Decode Failed", "No QR code found in the image."
                )
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to decode QR code:\n{e}")

    def process_decoded_qr_data(self, data):
        """Add a decoded secret or URI OTP data after prompting for account name."""
        if data.startswith("otpauth://"):
            popup_name = NewPopup(
                "Enter account name for scanned Key URI:", "Account Name Entry"
            )
            if popup_name.exec() == QInputDialog.DialogCode.Accepted:
                account_name = popup_name.textValue().strip()
                if account_name:
                    self.accounts.append({"name": account_name, "key_uri": data})
                    save_accounts(self.accounts)
                    self.refresh_tiles()
        else:
            popup_name = NewPopup(
                "Enter account name for scanned secret key:", "Account Name Entry"
            )
            if popup_name.exec() == QInputDialog.DialogCode.Accepted:
                account_name = popup_name.textValue().strip()
                if account_name:
                    self.accounts.append({"name": account_name, "secret": data})
                    save_accounts(self.accounts)
                    self.refresh_tiles()

    def show_settings_options(self):
        """Present user with different settings options."""
        options = [
            "Export Accounts to CSV",
        ]
        option, ok = QInputDialog.getItem(
            self, "Settings", "Choose an option:", options, 0, False
        )
        if not ok:
            return

        if option == "Export Accounts to CSV":
            self.export_accounts_csv()

    def export_accounts_csv(self):
        """Export current OTP accounts to a CSV file."""
        if not self.accounts:
            QMessageBox.information(self, "Export", "No accounts to export.")
            return

        filename, _ = QFileDialog.getSaveFileName(
            self, "Export OTP Entries to CSV", "", "CSV Files (*.csv)"
        )
        if filename:
            try:
                with open(filename, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    for account in self.accounts:
                        name = account.get("name", "Unknown")
                        secret_or_uri = account.get("key_uri") or account.get("secret", "")
                        if secret_or_uri:
                            writer.writerow([name, secret_or_uri])
                QMessageBox.information(
                    self, "Export Successful", "OTP accounts exported successfully!"
                )
            except Exception as e:
                QMessageBox.warning(self, "Export Failed", f"Failed to export to CSV file:\n{e}")

    def filter_cards(self, text):
        """Filter displayed OTP cards based on search text."""
        search_text = text.lower()
        for card in self.cards:
            if search_text in card.account_name.lower() or search_text in card.user.lower():
                card.show()
            else:
                card.hide()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    master_pw = prompt_for_password()
    window = Virex(master_pw)
    window.show()
    sys.exit(app.exec())
