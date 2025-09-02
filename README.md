# Virex-OTP

A Python desktop application for managing OTP (One-Time Password) accounts using PySide6.

## Features

- Secure master password protection
- Add OTP accounts via secret key, otpauth URI, CSV import, or QR code (camera/image)
- Export/import accounts to/from CSV
- Auto-lock and clipboard clear timeout settings
- Light/dark/system theme support
- Responsive, modern UI

## Project Structure
app/ 
├── helpers.py # Helper functions (account, clipboard, CSV, QR) 
├── main.py # Main application window and logic 
├── settings.py # Settings dialog and config management 
├── theme.py # Theme and palette management 
├── images/ # UI icons and images 
├── accounts.json # OTP account data (created at runtime) 
├── config.json # User settings (created at runtime) tests/


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

python main.py

## Project Structure

app/
├── helpers.py # Helper functions
├── main.py # Main application entry point

## License

This project is licensed under the MIT License.