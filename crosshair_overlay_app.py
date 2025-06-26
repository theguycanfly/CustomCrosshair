from pathlib import Path
from typing import Optional, Tuple

from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QFileDialog,
    QVBoxLayout, QHBoxLayout, QCheckBox, QMessageBox,
    QSystemTrayIcon, QShortcut, QDialog, QLineEdit, QDialogButtonBox
)
from PyQt5.QtGui import QPixmap, QIcon, QKeySequence
from PyQt5.QtCore import Qt, QPoint, QSize
import sys
import ctypes


# DPI awareness (optional, can improve fullscreen behavior)
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass


# Constants
DEFAULT_IMAGE: Path = Path("crosshair.png")
TRAY_ICON: Path = Path("crosshair.ico")
CROSSHAIR_SIZE: int = 100
WINDOW_SIZE: Tuple[int, int] = (400, 280)
HOTKEY: str = "Alt+S"

# Extended window styles for click-through
WS_EX_TRANSPARENT: int = 0x00000020
WS_EX_LAYERED: int = 0x00080000
WS_EX_NOACTIVATE: int = 0x08000000
HWND_TOPMOST: int = -1
SWP_NOSIZE: int = 0x0001
SWP_NOMOVE: int = 0x0002
SWP_NOACTIVATE: int = 0x0010
SWP_SHOWWINDOW: int = 0x0040


def set_click_through(win: QWidget) -> None:
    hwnd: int = int(win.winId())
    style: int = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
    ctypes.windll.user32.SetWindowLongW(
        hwnd, -20,
        style | WS_EX_TRANSPARENT | WS_EX_LAYERED | WS_EX_NOACTIVATE
    )
    ctypes.windll.user32.SetWindowPos(
        hwnd, HWND_TOPMOST, 0, 0, 0, 0,
        SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW
    )


def unset_click_through(win: QWidget) -> None:
    hwnd: int = int(win.winId())
    style: int = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
    ctypes.windll.user32.SetWindowLongW(
        hwnd, -20,
        style & ~WS_EX_TRANSPARENT & ~WS_EX_NOACTIVATE
    )


def resource_path(relative_path: Path) -> Path:
    base = Path(getattr(sys, '_MEIPASS', Path.cwd()))
    return base / relative_path


class HotkeyDialog(QDialog):
    def __init__(self, current_hotkey: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Change Hotkey")
        self.setFixedSize(300, 100)
        self.key_sequence: Optional[QKeySequence] = None
        layout = QVBoxLayout(self)
        self.label = QLabel(f"Current Hotkey: {current_hotkey}\nPress new hotkey:", self)
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

    def keyPressEvent(self, event) -> None:
        seq = QKeySequence(event.modifiers() | event.key())
        if seq.toString():
            self.key_sequence = seq
            self.edit.setText(seq.toString())
        event.accept()

    def keyReleaseEvent(self, event) -> None:
        event.accept()


class TrayMenuPopup(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent, Qt.Tool | Qt.FramelessWindowHint)
        self.setWindowFlag(Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet(
            "QWidget{background:#2c2c2c; border-radius:10px;}"
            "QPushButton{background:#505050;color:white;font-size:13pt;"
            "padding:10px 20px;border-radius:8px;margin:6px 10px;}"
            "QPushButton:hover{background:#707070;}"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        for text, fn in [
            ("Show", parent.show_overlay if parent else lambda: None),
            ("Hide", parent.hide if parent else lambda: None),
            ("Settings", parent.show_settings if parent else lambda: None),
            ("Exit", QApplication.quit)
        ]:
            btn = QPushButton(text)
            btn.clicked.connect(lambda _, f=fn: (f(), self.hide()))
            layout.addWidget(btn)

    def show_at(self, pos: QPoint) -> None:
        geom = QApplication.primaryScreen().availableGeometry()
        size = self.sizeHint()
        x = min(max(pos.x(), geom.left()), geom.right() - size.width())
        y = pos.y() + size.height() > geom.bottom() and (pos.y() - size.height()) or pos.y()
        self.move(x, y)
        self.show()


class CrosshairApp(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.current_hotkey: str = HOTKEY
        self.click_through: bool = True
        self._load_resources()
        self._init_window()
        self._init_ui()
        self._init_tray()
        self._init_hotkey()
        self.load_image(DEFAULT_IMAGE)
        self.show_settings()

    def _load_resources(self) -> None:
        self.default_image: Path = resource_path(DEFAULT_IMAGE)
        self.tray_icon_path: Path = resource_path(TRAY_ICON)

    def _init_window(self) -> None:
        self.setWindowTitle("Custom Crosshair")
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setFixedSize(*WINDOW_SIZE)
        self.setStyleSheet("background:#121212; color:white;")

    def _init_ui(self) -> None:
        self.image_label = QLabel(alignment=Qt.AlignCenter)
        self.image_label.setFixedSize(CROSSHAIR_SIZE, CROSSHAIR_SIZE)
        self.image_label.setAttribute(Qt.WA_TranslucentBackground, True)

        self.reset_btn = QPushButton("Reset")
        self.select_btn = QPushButton("Select")
        self.center_btn = QPushButton("Center")
        self.pin_chk = QCheckBox("Topmost")
        self.pin_chk.setChecked(True)
        self.click_chk = QCheckBox("Click-Through")
        self.click_chk.setChecked(True)
        self.change_hotkey_btn = QPushButton("Change Hotkey")

        for w in (self.reset_btn, self.select_btn, self.center_btn, self.change_hotkey_btn):
            w.setStyleSheet("background:#2c2c2c; padding:8px; border-radius:6px;")
        self.pin_chk.setStyleSheet("padding:6px;")
        self.click_chk.setStyleSheet("padding:6px;")

        self.reset_btn.clicked.connect(self._on_reset)
        self.select_btn.clicked.connect(self._on_select)
        self.center_btn.clicked.connect(self._on_center)
        self.pin_chk.stateChanged.connect(self._on_pin_toggle)
        self.click_chk.stateChanged.connect(self._on_click_toggle)
        self.change_hotkey_btn.clicked.connect(self._on_change_hotkey_clicked)

        btn_layout = QVBoxLayout()
        for w in (self.reset_btn, self.select_btn, self.center_btn,
                  self.pin_chk, self.click_chk, self.change_hotkey_btn):
            btn_layout.addWidget(w)

        self.settings_layout = QHBoxLayout()
        self.settings_layout.setContentsMargins(0, 0, 0, 0)
        self.settings_layout.setSpacing(10)
        self.settings_layout.addWidget(self.image_label)
        self.settings_layout.addLayout(btn_layout)

    def _init_tray(self) -> None:
        icon = QIcon(str(self.tray_icon_path))
        self.tray = QSystemTrayIcon(icon, self)
        self.tray.setContextMenu(None)
        self.tray.show()
        self.popup_menu = TrayMenuPopup(self)
        self.tray.activated.connect(self._on_tray_activated)

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self.show_settings()
        elif reason == QSystemTrayIcon.Context:
            pos = QApplication.instance().desktop().cursor().pos()
            self.popup_menu.show_at(pos)

    def _init_hotkey(self) -> None:
        if hasattr(self, '_hotkey_shortcut'):
            try:
                self._hotkey_shortcut.activated.disconnect()
            except Exception:
                pass
            self._hotkey_shortcut.setParent(None)
        self._hotkey_shortcut = QShortcut(QKeySequence(self.current_hotkey), self)
        self._hotkey_shortcut.activated.connect(self._toggle_visibility)

    def _toggle_visibility(self) -> None:
        if self.isVisible():
            self.hide()
        else:
            self.show_settings()

    def _on_change_hotkey_clicked(self) -> None:
        dlg = HotkeyDialog(self.current_hotkey, self)
        if dlg.exec_() == QDialog.Accepted and dlg.key_sequence:
            self.current_hotkey = dlg.key_sequence.toString()
            self._init_hotkey()
            QMessageBox.information(self, "Hotkey Changed", f"New hotkey: {self.current_hotkey}")

    def load_image(self, path: Path) -> None:
        path_to_load: Path = path if path.exists() else self.default_image
        pix = QPixmap(str(path_to_load))
        if pix.isNull():
            QMessageBox.warning(self, "Error", f"Cannot load: {path_to_load}")
            return
        scaled_pix = pix.scaled(CROSSHAIR_SIZE, CROSSHAIR_SIZE,
                                Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_label.setPixmap(scaled_pix)
        self.image_label.setFixedSize(scaled_pix.size())

    def _on_reset(self) -> None:
        self.load_image(self.default_image)
        self.show_settings()

    def _on_select(self) -> None:
        f, _ = QFileDialog.getOpenFileName(self, "Select Image", filter="PNG (*.png)")
        if f:
            self.load_image(Path(f))

    def _on_center(self) -> None:
        self._enter_overlay()

    def _on_pin_toggle(self) -> None:
        self.setWindowFlag(Qt.WindowStaysOnTopHint, self.pin_chk.isChecked())
        self.show()

    def _on_click_toggle(self) -> None:
        self.click_through = self.click_chk.isChecked()
        if self.click_through:
            set_click_through(self)
        else:
            unset_click_through(self)

    def _center(self) -> None:
        screen_geom = QApplication.primaryScreen().geometry()
        x = screen_geom.left() + (screen_geom.width() - self.width()) // 2
        y = screen_geom.top() + (screen_geom.height() - self.height()) // 2
        self.move(x, y)

    def _enter_overlay(self) -> None:
        for w in (self.reset_btn, self.select_btn, self.center_btn,
                  self.pin_chk, self.click_chk, self.change_hotkey_btn):
            w.hide()
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        pix = self.image_label.pixmap()
        size = pix.size() if pix else QSize(CROSSHAIR_SIZE, CROSSHAIR_SIZE)
        self.setFixedSize(size)
        self._center()
        self.show()
        if self.click_through:
            set_click_through(self)

    def show_settings(self) -> None:
        for w in (self.reset_btn, self.select_btn, self.center_btn,
                  self.pin_chk, self.click_chk, self.change_hotkey_btn):
            w.show()
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setFixedSize(*WINDOW_SIZE)
        self.setLayout(self.settings_layout)
        self.show()
        self._center()

    def show_overlay(self) -> None:
        self._enter_overlay()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = CrosshairApp()
    win.show()
    sys.exit(app.exec_())
