# Virex-OTP

A Python desktop application for managing OTP (One-Time Password) accounts using PySide6.

## Features

- Secure master password protection (accounts are encrypted at rest)
- Add OTP accounts via secret key, otpauth URI, CSV import, or QR code (camera/image)
- Export/import accounts to/from CSV
- Auto-lock and clipboard clear timeout settings
- Light/dark/system theme support
- Responsive, modern UI

## Project Structure
```
app/
├── main.py         # Main application window and logic
├── helpers.py      # Helper functions (encryption, account management, etc.)
├── settings.py     # Settings dialog and config management
├── theme.py        # Theme and palette management
└── images/         # UI icons and images
```

## Installation

1. Clone the repository:

   git clone <your-repo-url>
2. Navigate to the `app` directory:

   cd app

3. (Optional) Create and activate a virtual environment:
    
    python -m venv venv venv\Scripts\activate

4. Install dependencies (if any):

   pip install -r requirements.txt

## Usage

Run the main application:

```bash
python app/main.py
```

## License

This project is licensed under the MIT License.