from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette, QColor
from PySide6.QtWidgets import QApplication


def get_theme(current_theme):
    """Return the theme name based on system or user selection."""
    if current_theme == "system":
        from PySide6.QtGui import QGuiApplication

        style_hints = QGuiApplication.styleHints()
        color_scheme = style_hints.colorScheme()
        return "dark" if color_scheme == Qt.ColorScheme.Dark else "light"
    return current_theme


def apply_palette(theme):
    """Apply color palette to the application."""
    app = QApplication.instance()
    palette = QPalette()
    if theme == "dark":
        palette.setColor(QPalette.ColorRole.Window, QColor("#232323"))
        palette.setColor(QPalette.ColorRole.WindowText, QColor("#ffffff"))
        palette.setColor(QPalette.ColorRole.Base, QColor("#232323"))
        palette.setColor(QPalette.ColorRole.Text, QColor("#ffffff"))
    else:
        palette.setColor(QPalette.ColorRole.Window, QColor("#ffffff"))
        palette.setColor(QPalette.ColorRole.WindowText, QColor("#232323"))
        palette.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
        palette.setColor(QPalette.ColorRole.Text, QColor("#232323"))
    app.setPalette(palette)


def get_stylesheet(theme):
    """Return the stylesheet string for the given theme."""
    if theme == "dark":
        return """
            QDialog {
                background: #232323;
                color: #fff;
                border-radius: 16px;
            }
            QLabel { color: #fff; }
            QLineEdit, QComboBox {
                background: #232323;
                color: #fff;
                border: 1px solid #444;
                border-radius: 8px;
                padding: 4px 8px;
            }
            QPushButton {
                background: #232323;
                color: #fff;
                border: 1px solid #444;
                border-radius: 8px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background: #444;
                color: #fff;
            }
        """
    return """
        QDialog {
            background: #fff;
            color: #232323;
            border-radius: 16px;
        }
        QLabel { color: #232323; }
        QLineEdit, QComboBox {
            background: #fff;
            color: #232323;
            border: 1px solid #ccc;
            border-radius: 8px;
            padding: 4px 8px;
        }
        QPushButton {
            background: #f5f5f5;
            color: #232323;
            border: 1px solid #ccc;
            border-radius: 8px;
            padding: 6px 12px;
        }
        QPushButton:hover {
            background: #e0e0e0;
            color: #232323;
        }
    """
