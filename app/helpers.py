import hashlib
import json
import os
import sys

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QInputDialog, QLineEdit, QMessageBox

ORG_NAME = "YourOrg"
APP_NAME = "OTPApp"
ACCOUNTS_FILE = "accounts.json"


def set_master_password(pw):
    settings = QSettings(ORG_NAME, APP_NAME)
    hash_pw = hashlib.sha256(pw.encode()).hexdigest()
    settings.setValue("master_hash", hash_pw)


def check_master_password(pw):
    settings = QSettings(ORG_NAME, APP_NAME)
    hash_pw = hashlib.sha256(pw.encode()).hexdigest()
    stored_hash = settings.value("master_hash")
    return stored_hash == hash_pw


def prompt_for_password():
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
        else:
            sys.exit()
    else:
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
            else:
                QMessageBox.warning(None, "Error", "Incorrect password!")


def save_accounts(accounts):
    with open(ACCOUNTS_FILE, "w") as f:
        json.dump(accounts, f)


def load_accounts():
    if os.path.exists(ACCOUNTS_FILE):
        try:
            with open(ACCOUNTS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []
