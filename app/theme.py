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
            /* General Window and Dialog Styles */
            QMainWindow, QDialog {
                background-color: #232323;
                color: #ffffff;
            }

            /* Labels */
            QLabel {
                color: #ffffff;
            }

            /* Input Fields */
            QLineEdit, QComboBox {
                background-color: #232323;
                color: #ffffff;
                border: 1px solid #444;
                border-radius: 8px;
                padding: 4px 8px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
            }

            /* Buttons */
            QPushButton {
                background-color: #232323;
                color: #ffffff;
                border: 1px solid #444;
                border-radius: 8px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #444;
            }
            #transparentButton {
                background-color: transparent;
                border: none;
            }

            /* Scroll Area */
            QScrollArea {
                border: none;
            }
            QScrollBar:vertical {
                width: 0px;
            }

            /* OtpCard Styles */
            #frame {
                background-color: #3a3a3a;
                border-radius: 12px;
            }
            #label_account {
                color: #ffffff;
            }
            #label_user {
                color: #b0b0b0;
            }
            #label_current {
                color: #ffffff;
            }
            #aboutTitle {
                font-size: 18px;
                font-weight: bold;
            }
        """
    return """
        /* General Window and Dialog Styles */
        QMainWindow, QDialog {
            background-color: #ffffff;
            color: #232323;
        }

        /* Labels */
        QLabel {
            color: #232323;
        }

        /* Input Fields */
        QLineEdit, QComboBox {
            background-color: #ffffff;
            border: 1px solid #ccc;
            border-radius: 8px;
            padding: 4px 8px;
        }
        QComboBox::drop-down {
            border: none;
        }
        QComboBox::down-arrow {
            image: none;
        }

        /* Buttons */
        QPushButton {
            background-color: #f5f5f5;
            border: 1px solid #ccc;
            border-radius: 8px;
            padding: 6px 12px;
        }
        QPushButton:hover {
            background-color: #e0e0e0;
        }
        #transparentButton {
            background-color: transparent;
            border: none;
        }

        /* Scroll Area */
        QScrollArea {
            border: none;
        }
        QScrollBar:vertical {
            width: 0px;
        }

        /* OtpCard Styles */
        #frame {
            background-color: #f0f0f0;
            border-radius: 12px;
        }
        #label_account {
            color: #000000;
        }
        #label_user {
            color: #555555;
        }
        #label_current {
            color: #000000;
        }
        #aboutTitle {
            font-size: 18px;
            font-weight: bold;
        }
    """
