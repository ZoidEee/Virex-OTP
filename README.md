# Virex-OTP

A secure, modern, and cross-platform desktop application for managing your Two-Factor Authentication (2FA) accounts, built with Python and PySide6.


## Features

- **Secure Storage**: All your OTP secrets are encrypted at rest using a master password you control.
- **Strong Encryption**: Uses PBKDF2 for key derivation to protect against brute-force attacks.
- **Multiple Import Options**: Add accounts via secret key, `otpauth://` URI, QR code scanning (from camera or image file), and bulk import from a CSV file.
- **Flexible Data Management**: Easily export your accounts to an unencrypted CSV file for portability or to a secure, encrypted backup file for safekeeping.
- **Customizable Security**: Enhance your security by setting an automatic application lock timer and a clipboard-clearing timeout.
- **System Tray Integration**: Runs conveniently in the system tray for quick access.
- **Modern UI**: A clean and intuitive user interface that automatically adapts to your system's light or dark theme.

## Project Structure
```
app/ 
+├── main.py                 # Main application window and logic 
+├── helpers.py              # Helper functions (encryption, account management, etc.) 
+├── about.py                # The "About" dialog window
+├── settings.py             # Settings dialog and config management 
+├── theme.py                # Theme and stylesheet management 
+├── widgets/ 
+│   ├── init.py           # Makes widgets a package 
+│   ├── circular_countdown.py # TOTP countdown timer widget 
+│   ├── dialogs.py            # Custom dialogs (popups, QR scanner) 
+│   └── otp_card.py           # The main card widget for displaying an account 
+└── images/                 # UI icons and images
```


## Installation

1. Clone the repository:

    git clone https://github.com/ZoidEee/Virex-OTP.git

2. Navigate to the `app` directory:

   cd app

3. (Optional) Create and activate a virtual environment:
    
    python -m venv venv venv\Scripts\activate

4. Install dependencies (if any):

   pip install -r requirements.txt  

A `requirements.txt` file is included with the necessary packages:

```
PySide6
pyotp
pyzbar
opencv-python
cryptography
```

## Usage

Run the main application:

```bash
python app/main.py
```

## License

This project is licensed under the MIT License.