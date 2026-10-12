#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Einstiegspunkt für Astrorust — Native Qt6 Astrologie Desktop-App.
"""

import os
import sys

# Ensure gui directory is on path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from appsettings import AppSettings
import i18n
import styles


def main():
    settings = AppSettings.load()
    i18n.set_language(settings.language)
    from mainwindow import MainWindow  # erst nach der Sprachwahl importieren (tr() läuft schon beim Aufbau)

    app = QApplication(sys.argv)
    app.setApplicationName("Astrorust")
    app.setApplicationVersion("1.1.0")
    app.setOrganizationName("Astrorust")
    app.setDesktopFileName("astrorust")

    # Apply Breeze Dark / LME Stylesheet
    app.setStyleSheet(styles.DARK_STYLESHEET)

    # Set icon if exists
    icon_path = os.path.join(current_dir, "astrorust.svg")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    window = MainWindow(settings)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
