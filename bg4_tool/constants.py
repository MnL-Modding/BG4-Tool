from pathlib import Path

from PySide6 import QtWidgets


APP_NAME = "bg4_tool"
APP_DISPLAY_NAME = "BG4 Tool"

QtWidgets.QApplication.setApplicationName(APP_NAME)
QtWidgets.QApplication.setApplicationDisplayName(APP_DISPLAY_NAME)


SCRIPT_DIR = Path(__file__).parent
FILES_DIR = SCRIPT_DIR / 'files'