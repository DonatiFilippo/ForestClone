from __future__ import annotations

from pathlib import Path
import sys

from PySide6.QtCore import QStandardPaths
from PySide6.QtWidgets import QApplication, QMessageBox

from forest_clone.app import FocusController
from forest_clone.storage import Storage
from forest_clone.ui.main_window import MainWindow


def main() -> int:
    application = QApplication(sys.argv)
    application.setApplicationName("Pocket Forest")
    application.setOrganizationName("PocketForest")
    application.setQuitOnLastWindowClosed(True)

    data_dir = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation))
    try:
        storage = Storage(data_dir / "forest.db")
    except (OSError, RuntimeError) as error:
        QMessageBox.critical(None, "Pocket Forest", f"Could not open local data:\n{error}")
        return 1

    controller = FocusController(storage)
    window = MainWindow(controller, storage)
    window.show()
    result = application.exec()
    storage.close()
    return result


if __name__ == "__main__":
    raise SystemExit(main())
