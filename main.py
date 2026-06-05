#!/usr/bin/env python3
"""
Sanjeevani Shelf v1.1 - Main Entry Point
"""

import sys
import os
from pathlib import Path

# Fix Windows Unicode output
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from PyQt5.QtWidgets import QApplication
from ui.app import SanjeevaniApp


if __name__ == "__main__":
    qt_app = QApplication(sys.argv)
    window = SanjeevaniApp()
    window.show()
    sys.exit(qt_app.exec_())