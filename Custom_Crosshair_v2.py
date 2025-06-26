from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QFileDialog,
    QVBoxLayout, QHBoxLayout, QCheckBox, QMessageBox,
    QMenu, QAction, QSystemTrayIcon, QShortcut, QFrame,
    QDialog, QLineEdit, QDialogButtonBox
)
from PyQt5.QtGui import QPixmap, QIcon, QKeySequence
from PyQt5.QtCore import Qt, QPoint
import sys
import os
import ctypes

# Constants
DEFAULT_IMAGE = "crosshair.png"
TRAY_ICON = "crosshair.ico"
CROSSHAIR_SIZE = 100
WINDOW_SIZE = (400, 280)  # Slightly taller to fit new button comfortably
HOTKEY = "Alt+S"


def resource_path(relative_path: str) -> str:
    base = getattr(sys, '_MEIPASS', os.path.abspath("."))
    path = os.path.join(base, relative_path)
    if not os.path.exists(path):
        print(f"Resource not found: {path}")
    return path


def set_click_through(win: QWidget):
    hwnd = int(win.winId())
    style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
    ctypes.windll.user32.SetWindowLongW(hwnd, -20, style | 0x80000 | 0x20)


class HotkeyDialog(QDialog):
    def __init__(self, current_hotkey, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Change Hotkey")
        self.setFixedSize(300, 100)
        self.key_sequence = None

        layout = QVBoxLayout(self)

        self.label = QLabel(f"Current Hotkey: {current_hotkey}\nPress new hotkey combination:", self)
        layout.addWidget(self.label)

        self.edit = QLineEdit(self)
        self.edit.setPlaceholderText("Press keys here")
        self.edit.setReadOnly(True)
        layout.addWidget(self.edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.grabKeyboard()

    def keyPressEvent(self, event):
        key_seq = QKeySequence(event.modifiers() | event.key())
        # Filter out modifier-only keys (like Shift alone)
        if key_seq.toString():
            self.key_sequence = key_seq
            self.edit.setText(key_seq.toString())
        event.accept()

    def keyReleaseEvent(self, event):
        event.accept()


class TrayMenuPopup(QWidget):
    """Custom popup tray menu with bigger buttons and fonts."""

    def __init__(self, parent=None):
        super().__init__(parent, Qt.Tool | Qt.FramelessWindowHint)
        self.setWindowFlag(Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("""
            QWidget {
                background-color: #2c2c2c;
                border-radius: 10px;
            }
            QPushButton {
                background-color: #505050;
                color: white;
                font-size: 13pt;
                padding: 10px 20px;
                border-radius: 8px;
                margin: 6px 10px;
            }
            QPushButton:hover {
                background-color: #707070;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        self.show_btn = QPushButton("Show")
        self.hide_btn = QPushButton("Hide")
        self.exit_btn = QPushButton("Exit")

        layout.addWidget(self.show_btn)
        layout.addWidget(self.hide_btn)
        layout.addWidget(self.exit_btn)

        self.show_btn.clicked.connect(self._on_show)
        self.hide_btn.clicked.connect(self._on_hide)
        self.exit_btn.clicked.connect(self._on_exit)

    def _on_show(self):
        self.parent().show()
        self.parent().raise_()
        self.parent().activateWindow()
        self.hide()

    def _on_hide(self):
        self.parent().hide()
        self.hide()

    def _on_exit(self):
        QApplication.quit()

    def show_at(self, pos: QPoint):
        screen = QApplication.primaryScreen()
        screen_geom = screen.availableGeometry()
        popup_size = self.sizeHint()

        x = pos.x()
        y = pos.y()

        # If showing below the cursor would clip the popup at screen bottom, show above
        if y + popup_size.height() > screen_geom.bottom():
            y = y - popup_size.height()

        # Prevent clipping off right edge
        if x + popup_size.width() > screen_geom.right():
            x = screen_geom.right() - popup_size.width()

        # Prevent clipping off left edge
        if x < screen_geom.left():
            x = screen_geom.left()

        self.move(QPoint(x, y))
        self.show()


class CrosshairApp(QWidget):
    def __init__(self):
        super().__init__()
        self.current_hotkey = HOTKEY  # Store current hotkey
        self._load_resources()
        self._init_window()
        self._init_ui()
        self._init_tray()
        self._init_hotkey()
        self.load_image(DEFAULT_IMAGE)

    def _load_resources(self):
        self.default_image = resource_path(DEFAULT_IMAGE)
        self.tray_icon_path = resource_path(TRAY_ICON)

    def _init_window(self):
        self.setWindowTitle("Custom Crosshair")
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setFixedSize(*WINDOW_SIZE)
        self.setStyleSheet("background-color: #121212; color: white;")

    def _init_ui(self):
        self.image_label = QLabel(alignment=Qt.AlignCenter)
        self.image_label.setFixedSize(CROSSHAIR_SIZE, CROSSHAIR_SIZE)
        self.image_label.setAttribute(Qt.WA_TranslucentBackground, True)
        self.image_label.setStyleSheet("background: transparent;")

        self.reset_btn = QPushButton("Reset")
        self.select_btn = QPushButton("Select")
        self.center_btn = QPushButton("Center")
        self.pin_chk = QCheckBox("Pin on Top")
        self.pin_chk.setChecked(True)

        for w in (self.reset_btn, self.select_btn, self.center_btn):
            w.setStyleSheet("background: #2c2c2c; padding: 8px; border-radius: 6px;")
        self.pin_chk.setStyleSheet("padding: 6px;")

        self.reset_btn.clicked.connect(self._on_reset)
        self.select_btn.clicked.connect(self._on_select)
        self.center_btn.clicked.connect(self._on_center)
        self.pin_chk.stateChanged.connect(self._on_pin_toggle)

        # Add the new "Change Hotkey" button
        self.change_hotkey_btn = QPushButton("Change Hotkey")
        self.change_hotkey_btn.setStyleSheet("background: #2c2c2c; padding: 8px; border-radius: 6px;")
        self.change_hotkey_btn.clicked.connect(self._on_change_hotkey_clicked)

        btn_layout = QVBoxLayout()
        btn_layout.addWidget(self.reset_btn)
        btn_layout.addWidget(self.select_btn)
        btn_layout.addWidget(self.center_btn)
        btn_layout.addWidget(self.pin_chk)
        btn_layout.addWidget(self.change_hotkey_btn)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(10)
        main_layout.addWidget(self.image_label)
        main_layout.addLayout(btn_layout)

    def _init_tray(self):
        icon = QIcon(self.tray_icon_path)
        self.tray = QSystemTrayIcon(icon, self)

        # Remove native context menu
        self.tray.setContextMenu(None)
        self.tray.show()

        # Prepare custom popup menu
        self.popup_menu = TrayMenuPopup(self)

        # Connect tray icon clicks
        self.tray.activated.connect(self._on_tray_activated)

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:  # Left click
            if self.isVisible():
                self.hide()
            else:
                self.show()
                self.raise_()
                self.activateWindow()
        elif reason == QSystemTrayIcon.Context:  # Right click
            # Use cursor position to show popup menu
            pos = QApplication.instance().desktop().cursor().pos()
            self.popup_menu.show_at(pos)

    def _init_hotkey(self):
        # Remove old shortcut if any
        if hasattr(self, "_hotkey_shortcut") and self._hotkey_shortcut:
            try:
                self._hotkey_shortcut.activated.disconnect()
            except Exception:
                pass
            self._hotkey_shortcut.setParent(None)

        self._hotkey_shortcut = QShortcut(QKeySequence(self.current_hotkey), self)
        self._hotkey_shortcut.activated.connect(self._toggle_visibility)

    def _toggle_visibility(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()
            self.activateWindow()

    def _on_change_hotkey_clicked(self):
        dlg = HotkeyDialog(self.current_hotkey, self)
        if dlg.exec_() == QDialog.Accepted and dlg.key_sequence:
            new_hotkey = dlg.key_sequence.toString()
            if new_hotkey:
                self.current_hotkey = new_hotkey
                self._init_hotkey()  # Re-init shortcut with new hotkey
                QMessageBox.information(self, "Hotkey Changed", f"New hotkey set to: {new_hotkey}")

    def load_image(self, path: str):
        path = path if os.path.exists(path) else self.default_image
        pix = QPixmap(path)
        if pix.isNull():
            QMessageBox.warning(self, "Error", f"Cannot load: {path}")
            return
        scaled_pix = pix.scaled(CROSSHAIR_SIZE, CROSSHAIR_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_label.setPixmap(scaled_pix)
        self.image_label.setFixedSize(scaled_pix.size())
        self.current = path

    def _on_reset(self):
        self.load_image(self.default_image)
        self._exit_overlay()

    def _on_select(self):
        f, _ = QFileDialog.getOpenFileName(self, "Select Image", filter="PNG (*.png)")
        if f:
            self.load_image(f)

    def _on_center(self):
        self._center()
        ok = QMessageBox.question(self, "Confirm", "Center OK?", QMessageBox.Yes | QMessageBox.No)
        if ok == QMessageBox.Yes:
            self._enter_overlay()
        else:
            self._on_reset()

    def _on_pin_toggle(self):
        self.setWindowFlag(Qt.WindowStaysOnTopHint, self.pin_chk.isChecked())
        self.show()

    def _center(self):
        geom = QApplication.primaryScreen().availableGeometry()
        x = (geom.width() - self.width()) // 2
        y = (geom.height() - self.height()) // 2
        self.move(x, y)

    def _enter_overlay(self):
        for w in (self.reset_btn, self.select_btn, self.center_btn, self.pin_chk, self.change_hotkey_btn):
            w.hide()
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)

        pixmap = self.image_label.pixmap()
        if pixmap:
            size = pixmap.size()
            self.setFixedSize(size)
            self.image_label.setFixedSize(size)
        else:
            self.setFixedSize(CROSSHAIR_SIZE, CROSSHAIR_SIZE)
            self.image_label.setFixedSize(CROSSHAIR_SIZE, CROSSHAIR_SIZE)

        self.image_label.setAttribute(Qt.WA_TranslucentBackground, True)
        self.image_label.setStyleSheet("background: transparent;")
        self.setStyleSheet("background: transparent;")

        self._center()
        self.show()
        set_click_through(self)

    def _exit_overlay(self):
        for w in (self.reset_btn, self.select_btn, self.center_btn, self.pin_chk, self.change_hotkey_btn):
            w.show()
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self._init_window()
        self.show()

    def _toggle_ui(self, show: bool):
        self.setVisible(show)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = CrosshairApp()
    win.show()
    sys.exit(app.exec_())
