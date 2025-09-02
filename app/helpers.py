import hashlib
import json
import os
import sys
import csv
from urllib.parse import unquote, urlparse
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QInputDialog, QLineEdit, QMessageBox, QApplication

ORG_NAME = "YourOrg"
APP_NAME = "OTPApp"
ACCOUNTS_FILE = "accounts.json"


def set_master_password(pw):
    """Hash and store the master password."""
    settings = QSettings(ORG_NAME, APP_NAME)
    hash_pw = hashlib.sha256(pw.encode()).hexdigest()
    settings.setValue("master_hash", hash_pw)


def check_master_password(pw):
    """Check if the provided password matches the stored hash."""
    settings = QSettings(ORG_NAME, APP_NAME)
    hash_pw = hashlib.sha256(pw.encode()).hexdigest()
    stored_hash = settings.value("master_hash")
    return stored_hash == hash_pw


def prompt_for_password():
    """Prompt user for master password or to set a new one."""
    settings = QSettings(ORG_NAME, APP_NAME)
    master_hash = settings.value("master_hash")
    if master_hash is None:
        pw, ok = QInputDialog.getText(
            None,
            "Set Master Password",
            "Create master password:",
            echo=QLineEdit.EchoMode.Password,
        )
        if ok and pw:
            set_master_password(pw)
            return pw
        sys.exit()
    while True:
        pw, ok = QInputDialog.getText(
            None,
            "Master Password",
            "Enter master password:",
            echo=QLineEdit.EchoMode.Password,
        )
        if not ok:
            sys.exit()
        if check_master_password(pw):
            return pw
        QMessageBox.warning(None, "Error", "Incorrect password!")


def save_accounts(accounts):
    """Save accounts to file."""
    with open(ACCOUNTS_FILE, "w") as f:
        json.dump(accounts, f)


def load_accounts():
    """Load accounts from file."""
    if os.path.exists(ACCOUNTS_FILE):
        try:
            with open(ACCOUNTS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def parse_account_label(key_uri):
    """Parse account name and user from otpauth URI."""
    try:
        path = urlparse(key_uri).path
        label = path.lstrip("/")
        if ":" in label:
            acc, user = label.split(":", 1)
        else:
            acc, user = label, ""
        return unquote(acc), unquote(user)
    except Exception:
        return "Unknown", ""


def clear_clipboard():
    """Clear the system clipboard."""
    QApplication.clipboard().clear()


def export_accounts_csv(accounts, filename):
    """Export accounts to a CSV file."""
    try:
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for account in accounts:
                name = account.get("name", "Unknown")
                secret_or_uri = account.get("key_uri") or account.get("secret", "")
                if secret_or_uri:
                    writer.writerow([name, secret_or_uri])
        return True, None
    except Exception as e:
        return False, str(e)


def import_accounts_csv(filename):
    """Import accounts from a CSV file."""
    imported_accounts = []
    try:
        with open(filename, "r", newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 2:
                    account_name, secret_or_uri = row[0].strip(), row[1].strip()
                    if not account_name or not secret_or_uri:
                        continue
                    if secret_or_uri.startswith("otpauth://"):
                        imported_accounts.append(
                            {"name": account_name, "key_uri": secret_or_uri}
                        )
                    else:
                        imported_accounts.append(
                            {"name": account_name, "secret": secret_or_uri}
                        )
        return imported_accounts, None
    except Exception as e:
        return [], str(e)


def process_decoded_qr_data(data):
    """Return account entry dict from QR data."""
    if data.startswith("otpauth://"):
        return {"key_uri": data}
    return {"secret": data}


def generate_backup_key(password):
    """Generate a Fernet key from a password."""
    return base64.urlsafe_b64encode(hashlib.sha256(password.encode()).digest())


def export_accounts_encrypted(accounts, filename, password):
    """Export accounts to an encrypted file."""
    try:
        key = generate_backup_key(password)
        f = Fernet(key)
        data = json.dumps(accounts).encode()
        encrypted = f.encrypt(data)
        with open(filename, "wb") as file:
            file.write(encrypted)
        return True, None
    except Exception as e:
        return False, str(e)


def import_accounts_encrypted(filename, password):
    """Import accounts from an encrypted file."""
    try:
        key = generate_backup_key(password)
        f = Fernet(key)
        with open(filename, "rb") as file:
            encrypted = file.read()
        data = f.decrypt(encrypted)
        return json.loads(data), None
    except Exception as e:
        return [], str(e)
