"""Ana pencere: `lcc gui`."""

from __future__ import annotations

import logging
import os
import signal
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
APP_ID = "laptop-control-center"


def main(page: str = "monitor") -> int:
    logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s")
    # Denetimler kendi çizimimiz; platform temasının stilini zorlamasın.
    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")

    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QFontDatabase, QGuiApplication, QIcon
    from PySide6.QtQml import QQmlApplicationEngine

    from .bridge import Bridge
    from ..i18n import t

    app = QGuiApplication(sys.argv)
    app.setApplicationName(APP_ID)
    app.setApplicationDisplayName(t("app.title"))
    app.setDesktopFileName(APP_ID)     # Wayland app_id: pencere kuralları buna bakar
    app.setWindowIcon(QIcon.fromTheme("preferences-system-power"))
    for f in sorted((HERE / "fonts").glob("*.ttf")):
        QFontDatabase.addApplicationFont(str(f))

    bridge = Bridge()
    engine = QQmlApplicationEngine()
    engine.setInitialProperties({"bridge": bridge, "startPage": page})
    engine.load(QUrl.fromLocalFile(str(HERE / "qml" / "Main.qml")))
    if not engine.rootObjects():
        bridge.shutdown()
        return 1

    # Ctrl+C terminalden çalışırken de pencereyi kapatsın.
    signal.signal(signal.SIGINT, lambda *_: app.quit())
    from PySide6.QtCore import QTimer
    pulse = QTimer()
    pulse.timeout.connect(lambda: None)
    pulse.start(300)

    code = app.exec()
    bridge.shutdown()
    return code
