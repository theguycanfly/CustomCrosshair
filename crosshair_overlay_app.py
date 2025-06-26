from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QFileDialog,
    QVBoxLayout, QHBoxLayout, QFrame, QCheckBox, QMessageBox,
    QMenu, QAction, QSystemTrayIcon
)
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import Qt
import sys
import os
import ctypes
import keyboard  # requires: pip install keyboard

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller."""
    try:
        base_path = getattr(sys, '_MEIPASS', os.path.abspath("."))
        full_path = os.path.join(base_path, relative_path)
        
        if not os.path.exists(full_path):
            print(f"Error: Resource path not found: {full_path}")
        return full_path
    except Exception as e:
        print(f"Error getting resource path: {str(e)}")
        return relative_path

DEFAULT_IMAGE = resource_path("crosshair.png")
TRAY_ICON = resource_path("crosshair.ico")

def make_window_click_through(window):
    """Set the window to be click-through on Windows (overlay mode)."""
    hwnd = int(window.winId())
    extended_style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
    ctypes.windll.user32.SetWindowLongW(
        hwnd, -20, extended_style | 0x80000 | 0x20  # WS_EX_LAYERED | WS_EX_TRANSPARENT
    )

class CrosshairApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Custom Crosshair")
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setStyleSheet("background-color: #121212; color: white;")
        self.setFixedSize(400, 250)  # Adjust this size if necessary

        self.init_ui()
        self.load_image(DEFAULT_IMAGE)
        self.create_tray_icon()

        # Register global hotkey Alt+S
        keyboard.add_hotkey('alt+s', lambda: QApplication.quit())

    def init_ui(self):
        """Initialize the UI elements."""
        self.image_label = QLabel(self)
        self.image_label.setFixedSize(100, 100)  # Fixed size for crosshair image
        self.image_label.setFrameStyle(QFrame.NoFrame)
        self.image_label.setAlignment(Qt.AlignCenter)

        self.reset_button = QPushButton("Reset Image")
        self.select_button = QPushButton("Select Image")
        self.center_button = QPushButton("Center Screen")
        self.pin_checkbox = QCheckBox("Pin to Top")
        self.pin_checkbox.setChecked(True)

        for btn in [self.reset_button, self.select_button, self.center_button]:
            btn.setStyleSheet("background-color: #2c2c2c; padding: 8px; border-radius: 6px;")
        self.pin_checkbox.setStyleSheet("padding: 6px; color: white;")

        self.reset_button.clicked.connect(self.reset_image)
        self.select_button.clicked.connect(self.select_image)
        self.center_button.clicked.connect(self.center_on_screen)
        self.pin_checkbox.stateChanged.connect(self.toggle_pin)

        button_layout = QVBoxLayout()
        button_layout.addWidget(self.reset_button)
        button_layout.addWidget(self.select_button)
        button_layout.addWidget(self.center_button)
        button_layout.addWidget(self.pin_checkbox)

        main_layout = QHBoxLayout()
        main_layout.addWidget(self.image_label)
        main_layout.addLayout(button_layout)

        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.setLayout(main_layout)

    def load_image(self, image_path):
        """Load image and set it to the label."""
        print(f"Loading image from: {image_path}")  # Debugging line
        if os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                pixmap = pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.image_label.setPixmap(pixmap)
                self.current_image_path = image_path
                return
        QMessageBox.warning(self, "Image Load Error", f"Failed to load image: {image_path}")

    def reset_image(self):
        """Reset the image to default and restore UI.""" 
        self.load_image(DEFAULT_IMAGE)
        self.set_ui_visibility(True)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setStyleSheet("background-color: #121212; color: white;")
        self.setFixedSize(400, 250)
        self.image_label.setFixedSize(150, 150)
        self.image_label.setStyleSheet("")  # Reset style

        self.image_label.setFrameStyle(QFrame.NoFrame)
        self.show()

    def select_image(self):
        """Allow the user to select a custom image."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Crosshair Image", "", "PNG Images (*.png)"
        )
        if file_path:
            self.load_image(file_path)

    def center_on_screen(self):
        """Center the window on the screen and confirm the placement."""
        self.move_to_center()

        result = QMessageBox.question(
            self,
            "Confirm Alignment",
            "Does this look correct for your screen?",
            QMessageBox.Yes | QMessageBox.No
        )

        if result == QMessageBox.Yes:
            self.enter_overlay_mode()
        else:
            self.reset_image()

    def toggle_pin(self):
        """Toggle pinning the window on top."""
        is_pinned = self.pin_checkbox.isChecked()
        self.setWindowFlag(Qt.WindowStaysOnTopHint, is_pinned)
        self.show()

    def enter_overlay_mode(self):
        """Enter overlay mode with transparent background."""
        self.set_ui_visibility(False)
        self.image_label.setFrameStyle(QFrame.NoFrame)
        self.image_label.setStyleSheet("background: transparent; border: none;")
        self.image_label.setFixedSize(100, 100)

        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setStyleSheet("background: transparent;")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)

        self.setFixedSize(100, 100)
        self.move_to_center()

        self.update()
        self.show()

        make_window_click_through(self)

    def move_to_center(self):
        """Move window to the center of the screen (2560x1440)."""
        screen_width = 2560
        screen_height = 1440
        
        # Get the center of the screen
        center_x = screen_width // 2
        center_y = screen_height // 2

        # Adjust for the size of the window (100x100 crosshair)
        window_width = self.width()
        window_height = self.height()

        # Calculate the top-left corner position to center the window
        x_pos = center_x - window_width // 2
        y_pos = center_y - window_height // 2

        # Move the window
        self.move(x_pos, y_pos)

    def screen_center(self):
        """Get the center of the screen."""
        screen = QApplication.primaryScreen()
        return screen.availableGeometry().center()

    def set_ui_visibility(self, visible):
        """Show or hide UI components.""" 
        self.reset_button.setVisible(visible)
        self.select_button.setVisible(visible)
        self.center_button.setVisible(visible)
        self.pin_checkbox.setVisible(visible)

    def create_tray_icon(self):
        """Create the system tray icon and context menu.""" 
        tray_icon_path = TRAY_ICON
        if not os.path.exists(tray_icon_path):
            print(f"Error: Tray icon not found at {tray_icon_path}")  # Debugging line
        self.tray_icon = QSystemTrayIcon(QIcon(tray_icon_path), self)
        self.tray_icon.setVisible(True)

        tray_menu = QMenu(self)

        toggle_ui_action = QAction("Show/Hide UI", self)
        toggle_ui_action.setCheckable(True)
        toggle_ui_action.setChecked(True)
        toggle_ui_action.triggered.connect(self.toggle_ui)

        close_action = QAction("Close", self)
        close_action.triggered.connect(QApplication.quit)

        tray_menu.addAction(toggle_ui_action)
        tray_menu.addAction(close_action)

        self.tray_icon.setContextMenu(tray_menu)

    def toggle_ui(self):
        """Toggle UI visibility.""" 
        self.reset_image()
        self.set_ui_visibility(True)
        self.show()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CrosshairApp()
    window.show()
    sys.exit(app.exec_())
