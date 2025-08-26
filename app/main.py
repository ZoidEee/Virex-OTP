import sys
import time
from urllib.parse import unquote, urlparse

import cv2
import pyotp
from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import (
    QColor,
    QFont,
    QPainter,
    QPen,
    QPixmap,
    QIcon,
)
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
    QGraphicsDropShadowEffect,
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


class CircularCountdown(QWidget):
    def __init__(self, interval=30, parent=None):
        super().__init__(parent)
        self.interval = interval
        self.value = interval
        self.setFixedSize(42, 42)
        self.setAttribute(Qt.WA_TranslucentBackground)

    def update_value(self, value):
        self.value = value
        self.update()

    def paintEvent(self, event):
        size = min(self.width(), self.height())
        rect = QRectF(4, 4, size - 8, size - 8)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        # Draw background grey circle
        painter.setPen(QPen(QColor("#E0E0E0"), 5))
        painter.drawEllipse(rect)
        # Draw purple arc representing countdown
        angle_span = 360 * (self.value / self.interval)
        painter.setPen(QPen(QColor("#6C4CE0"), 5))
        painter.drawArc(rect, 90 * 16, -angle_span * 16)
        # Draw seconds text in center
        painter.setPen(QColor("#6C4CE0"))
        font = QFont("Arial", 12, QFont.Bold)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignCenter, f"{self.value}")


class OtpCard(QWidget):
    def __init__(
        self, account_name, user, totp, interval=30, logo_path=None, parent=None
    ):
        super().__init__(parent)
        self.account_name = account_name
        self.user = user
        self.totp = totp
        self.interval = interval
        self.logo_path = logo_path
        self.setFixedWidth(300)
        self.setFixedHeight(75)

        self.setStyleSheet(
            """
            QWidget {
                background-color: #FFFFFF;
                border-radius: 16px;
            }
        """
        )
        self.init_ui()

        shadow = QGraphicsDropShadowEffect()
        shadow.setColor(QColor(100, 100, 100, 50))
        shadow.setBlurRadius(14)
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_totp)
        self.timer.start(1000)
        self.update_totp()

    def init_ui(self):

        main_layout = QVBoxLayout(self)

        top_sub_layout = QHBoxLayout()
        self.countdown_circle = CircularCountdown(self.interval)
        top_sub_layout.addWidget(self.countdown_circle)

        bottom_sub_layout = QHBoxLayout()
        bottom_sub_left_layout = QHBoxLayout()
        bottom_sub_right_layout = QVBoxLayout()
        bottom_sub_right_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bottom_sub_right_layout.setSpacing(5)
        bottom_sub_left_layout.setContentsMargins(0, 17, 0, 0)

        self.label_current = QLabel("-- -- --")
        self.label_current.setFixedSize(75, 20)
        self.label_current.setFont(QFont("Times", 10, QFont.Weight.ExtraBold))
        self.label_current.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.label_current.setStyleSheet(
            "color: #fff; " "background-color: transparent; " "letter-spacing: 2px; "
        )
        bottom_sub_left_layout.addWidget(self.label_current)

        label_next_text = QLabel("Next")
        label_next_text.setStyleSheet("  color: #fff; background-color: transparent;")
        label_next_text.setFont(QFont("Times", 9))
        label_next_text.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.label_next_code = QLabel("-- -- --")
        self.label_next_code.setFixedSize(75, 20)
        self.label_next_code.setFont(QFont("Times", 8, QFont.Weight.DemiBold))
        self.label_next_code.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_next_code.setStyleSheet(
            "color: #fff; " "background-color: transparent; " "letter-spacing: 2px; "
        )
        bottom_sub_right_layout.addWidget(label_next_text)
        bottom_sub_right_layout.addWidget(self.label_next_code)

        bottom_sub_layout.addLayout(bottom_sub_left_layout)
        bottom_sub_layout.addLayout(bottom_sub_right_layout)

        main_layout.addLayout(top_sub_layout)
        main_layout.addLayout(bottom_sub_layout)

        """main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(6)

        # Top Row: logo (optional), account + user, countdown circle
        top_row = QHBoxLayout()
        top_row.setSpacing(12)

        if self.logo_path:
            logo_label = QLabel()
            pixmap = QPixmap(self.logo_path).scaled(
                28, 28, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            logo_label.setPixmap(pixmap)
            top_row.addWidget(logo_label)
        else:
            # For demo, add placeholder label for spacing
            spacer = QLabel("")
            spacer.setFixedWidth(28)
            top_row.addWidget(spacer)

        names_layout = QVBoxLayout()
        self.label_account = QLabel(self.account_name)
        self.label_account.setStyleSheet("font-weight: 600; font-size: 14px;")
        self.label_user = QLabel(self.user)
        self.label_user.setStyleSheet("color: #666; font-size: 11px;")

        names_layout.addWidget(self.label_account)
        names_layout.addWidget(self.label_user)
        top_row.addLayout(names_layout)
        top_row.addStretch()

        self.countdown_circle = CircularCountdown(self.interval)
        top_row.addWidget(self.countdown_circle)
        main_layout.addLayout(top_row)

        # OTP codes row
        otp_row = QHBoxLayout()
        otp_left_row = QVBoxLayout()
        otp_left_row.setContentsMargins(0, 11, 0, 0)

        self.label_current = QLabel("-- -- --")
        self.label_current.setFixedSize(75, 20)
        self.label_current.setFont(QFont("times", 8, QFont.Weight.ExtraBold))
        self.label_current.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.label_current.setStyleSheet(
            "color: #222; "
            "letter-spacing: 2px; "
            "padding-left: 5px; "
            "padding-right: 5px; "
            "border-radius: 10px; "
        )
        otp_left_row.addWidget(
            self.label_current, alignment=Qt.AlignmentFlag.AlignVCenter
        )

        otp_right = QVBoxLayout()

        label_next_text = QLabel("Next")
        label_next_text.setFixedSize(25, 15)
        label_next_text.setStyleSheet("  color: #666; background-color: transparent;")
        label_next_text.setFont(QFont("Times", 9))

        otp_right.addWidget(label_next_text)

        self.label_next_code = QLabel("-- -- --")
        self.label_next_code.setFont(QFont("times", 8, QFont.Weight.Bold))
        self.label_next_code.setFixedSize(75, 20)

        self.label_next_code.setStyleSheet(
            "color: #222; "
            "letter-spacing: 2px; "
            "padding-left: 5px; "
            "padding-right: 5px; "
            "border-radius: 10px; "
        )

        otp_right.addWidget(self.label_next_code)

        otp_row.addLayout(otp_left_row)
        otp_row.addLayout(otp_right)

        main_layout.addLayout(otp_row)"""

    def update_totp(self):
        now = int(time.time())
        elapsed = now % self.interval
        remaining = self.interval - elapsed
        self.countdown_circle.update_value(remaining)
        try:
            current = self.totp.now()
            next_code = self.totp.at(now + remaining)
        except Exception:
            current = "-- -- --"
            next_code = "-- -- --"
        self.label_current.setText(" ".join([current[:3], current[3:]]))
        self.label_next_code.setText(" ".join([next_code[:3], next_code[3:]]))


class Virex(QMainWindow):
    def __init__(self, master_pw):
        super().__init__()
        self.master_pw = master_pw
        self.accounts = load_accounts()
        self.cards = []
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Virex")
        self.setMinimumSize(650, 500)
        self.setup_mainwindow()
        self.refresh_tiles()

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
        self.grid_layout.setHorizontalSpacing(24)
        self.grid_layout.setVerticalSpacing(20)

        self.grid_layout.setColumnStretch(0, 1)
        self.grid_layout.setColumnStretch(1, 1)

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
        try:
            path = urlparse(key_uri).path  # "/ExampleOrg:user@example.com"
            label = path.lstrip("/")
            if ":" in label:
                acc, user = label.split(":", 1)
            else:
                acc, user = label, ""
            return unquote(acc), unquote(user)
        except Exception:
            return "Unknown", ""

    def refresh_tiles(self):
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.cards.clear()

        for idx, account in enumerate(self.accounts):
            if "key_uri" in account:
                acc_name, user = self.parse_account_label(account["key_uri"])
                totp = pyotp.parse_uri(account["key_uri"])
            else:
                acc_name = account.get("name", "Unknown")
                user = ""
                totp = pyotp.TOTP(account.get("secret", ""))

            # Optionally supply logo path or None
            card = OtpCard(acc_name, user, totp, logo_path=None)
            self.grid_layout.addWidget(card, idx // 2, idx % 2)
            self.cards.append(card)

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
