import sys
import time
from urllib.parse import unquote, urlparse

import cv2
import pyotp
from PySide6.QtCore import QTimer
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
    QGridLayout,
    QFileDialog,
    QMessageBox,
)
from pyzbar.pyzbar import decode

from helpers import prompt_for_password, save_accounts, load_accounts


class NewPopup(QInputDialog):
    def __init__(self, prompt, title="Input"):
        super().__init__()
        self.setWindowTitle(title)
        self.setLabelText(prompt)
        self.setOkButtonText("Next")
        self.setCancelButtonText("Cancel")
        self.resize(400, 120)


class Virex(QMainWindow):
    def __init__(self, master_pw):
        super().__init__()
        self.master_pw = master_pw
        self.accounts = load_accounts()  # Load saved accounts on startup
        self.otp_labels = []  # Store references to labels for updates
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Virex")
        self.setMinimumSize(600, 600)
        self.setup_mainwindow()
        self.refresh_tiles()  # Show accounts on startup
        self.setup_timer()

    def setup_mainwindow(self):
        btn_new = QPushButton("New")
        btn_new.clicked.connect(self.show_new_options)
        search_bar = QLineEdit()
        search_bar.setPlaceholderText("Search...")
        btn_settings = QPushButton("Settings")

        top_layout = QHBoxLayout()
        top_layout.addWidget(btn_new)
        top_layout.addWidget(search_bar)
        top_layout.addWidget(btn_settings)

        self.grid_layout = QGridLayout()
        self.grid_layout.setHorizontalSpacing(20)
        self.grid_layout.setVerticalSpacing(15)

        scroll_area = QScrollArea()
        scroll_content = QWidget()
        scroll_content.setLayout(self.grid_layout)
        scroll_area.setWidget(scroll_content)
        scroll_area.setWidgetResizable(True)

        main_layout = QVBoxLayout()
        main_layout.addLayout(top_layout)
        main_layout.addWidget(scroll_area)

        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

    def parse_account_label(self, key_uri):
        try:
            path = urlparse(key_uri).path  # "/ExampleOrg:user@example.com"
            label = path.lstrip("/")  # "ExampleOrg:user@example.com"
            if ":" in label:
                acc, user = label.split(":", 1)
            else:
                acc, user = label, ""
            return unquote(acc), unquote(user)
        except Exception:
            return "Unknown", ""

    def refresh_tiles(self):
        # Clear tiles and reset label storage
        for i in reversed(range(self.grid_layout.count())):
            widget = self.grid_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        self.otp_labels = []

        for i, account in enumerate(self.accounts):
            widget = QWidget()
            v_layout = QVBoxLayout(widget)
            v_layout.setContentsMargins(10, 10, 10, 10)

            # Extract account and user info
            if "key_uri" in account:
                acc_name, user = self.parse_account_label(account["key_uri"])
            else:
                acc_name = account.get("name", "Unknown")
                user = ""

            # Create labels
            label_account = QLabel(acc_name)
            label_user = QLabel(user)
            label_countdown = QLabel("")
            label_otp_current = QLabel("...")
            label_otp_next = QLabel("...")

            # Styling
            label_account.setStyleSheet("font-weight: bold; font-size: 16px;")
            label_user.setStyleSheet("color: gray; font-size: 12px;")
            label_otp_current.setStyleSheet(
                "font-family: monospace; font-size: 18px; color: blue;"
            )
            label_otp_next.setStyleSheet(
                "font-family: monospace; font-size: 14px; color: darkgray;"
            )
            label_countdown.setStyleSheet("font-size: 12px; color: green;")

            v_layout.addWidget(label_account)
            v_layout.addWidget(label_user)

            h_layout_otp = QHBoxLayout()
            h_layout_otp.addWidget(QLabel("Current:"))
            h_layout_otp.addWidget(label_otp_current)
            h_layout_otp.addStretch()
            h_layout_otp.addWidget(QLabel("Next:"))
            h_layout_otp.addWidget(label_otp_next)
            v_layout.addLayout(h_layout_otp)

            v_layout.addWidget(label_countdown)

            widget.setStyleSheet("border: 1px solid gray;")
            self.grid_layout.addWidget(widget, i // 2, i % 2)

            self.otp_labels.append(
                {
                    "current": label_otp_current,
                    "next": label_otp_next,
                    "countdown": label_countdown,
                    "account": account,
                }
            )

    def setup_timer(self):
        self.otp_update_interval = 30  # TOTP default interval
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_otps)
        self.timer.start(1000)  # update every second
        self.update_otps()

    def update_otps(self):
        now = int(time.time())
        elapsed = now % self.otp_update_interval
        remaining = self.otp_update_interval - elapsed

        for otp_entry in self.otp_labels:
            account = otp_entry["account"]
            try:
                if "key_uri" in account:
                    totp = pyotp.parse_uri(account["key_uri"])
                else:
                    totp = pyotp.TOTP(account.get("secret", ""))
                current_code = totp.now()
                next_code = totp.at(now + remaining)
            except Exception:
                current_code = "Invalid"
                next_code = "Invalid"

            otp_entry["current"].setText(current_code)
            otp_entry["next"].setText(next_code)
            otp_entry["countdown"].setText(f"Reset in {remaining}s")

    def show_new_options(self):
        options = [
            "Enter Secret Key",
            "Enter Key URI",
            "Import from CSV",
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
        elif option == "Import from CSV":
            self.import_csv()
        elif option == "Scan QR Code with Camera":
            self.scan_qr_code_camera()
        elif option == "Import QR Code Image":
            self.import_qr_image()

    def prompt_secret_key(self):
        popup = NewPopup("Enter secret key (Base32):", "Secret Key Entry")
        if popup.exec() == QInputDialog.Accepted:
            secret = popup.textValue().strip()
            if secret:
                popup_name = NewPopup(
                    "Enter account name for this secret:", "Account Name Entry"
                )
                if popup_name.exec() == QInputDialog.Accepted:
                    account_name = popup_name.textValue().strip()
                    if account_name:
                        self.accounts.append({"name": account_name, "secret": secret})
                        save_accounts(self.accounts)
                        self.refresh_tiles()

    def prompt_key_uri(self):
        popup = NewPopup("Enter the Key URI (otpauth URI):", "Key URI Entry")
        if popup.exec() == QInputDialog.Accepted:
            key_uri = popup.textValue().strip()
            if key_uri:
                popup_name = NewPopup(
                    "Enter account name for this Key URI:", "Account Name Entry"
                )
                if popup_name.exec() == QInputDialog.Accepted:
                    account_name = popup_name.textValue().strip()
                    if account_name:
                        self.accounts.append({"name": account_name, "key_uri": key_uri})
                        save_accounts(self.accounts)
                        self.refresh_tiles()

    def import_csv(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Import OTP Entries from CSV", "", "CSV Files (*.csv)"
        )
        if filename:
            try:
                with open(filename, "r") as f:
                    lines = f.readlines()
                for line in lines:
                    parts = line.strip().split(",")
                    if len(parts) >= 2:
                        account_name = parts[0].strip()
                        secret_or_uri = parts[1].strip()
                        if secret_or_uri.startswith("otpauth://"):
                            self.accounts.append(
                                {"name": account_name, "key_uri": secret_or_uri}
                            )
                        else:
                            self.accounts.append(
                                {"name": account_name, "secret": secret_or_uri}
                            )
                save_accounts(self.accounts)
                self.refresh_tiles()
                QMessageBox.information(
                    self, "Import Successful", "OTP accounts imported successfully!"
                )
            except Exception as e:
                QMessageBox.warning(
                    self, "Import Failed", f"Failed to import CSV file:\n{e}"
                )

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
            self.process_decoded_qr_data(decoded_data)
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
                self.process_decoded_qr_data(decoded_data)
            else:
                QMessageBox.warning(
                    self, "Decode Failed", "No QR code found in the image."
                )
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to decode QR code:\n{e}")

    def process_decoded_qr_data(self, data):
        if data.startswith("otpauth://"):
            popup_name = NewPopup(
                "Enter account name for scanned Key URI:", "Account Name Entry"
            )
            if popup_name.exec() == QInputDialog.Accepted:
                account_name = popup_name.textValue().strip()
                if account_name:
                    self.accounts.append({"name": account_name, "key_uri": data})
                    save_accounts(self.accounts)
                    self.refresh_tiles()
        else:
            popup_name = NewPopup(
                "Enter account name for scanned secret key:", "Account Name Entry"
            )
            if popup_name.exec() == QInputDialog.Accepted:
                account_name = popup_name.textValue().strip()
                if account_name:
                    self.accounts.append({"name": account_name, "secret": data})
                    save_accounts(self.accounts)
                    self.refresh_tiles()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    master_pw = prompt_for_password()
    window = Virex(master_pw)
    window.show()
    sys.exit(app.exec())
