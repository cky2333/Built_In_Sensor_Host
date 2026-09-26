"""Sensor Hub Host - 机载传感器上位机."""

import logging
import os
import sys

_project_root = os.path.dirname(os.path.abspath(__file__))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from PySide6.QtWidgets import QApplication
from src.app_window import AppWindow

LOG_FILE = os.path.join(_project_root, "debug.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ],
)
_logger = logging.getLogger("main")
_logger.info(f"=== SensorHub Host starting, log file: {LOG_FILE} ===")


def main():
    _logger.info("Creating QApplication")
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    _logger.info("Creating AppWindow")
    window = AppWindow()
    window.show()
    _logger.info("Entering event loop")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
