#!/usr/bin/env python3
"""
Sanjeevani Shelf v1.1 - Main Entry Point
PyQt5 Application
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from PyQt5.QtWidgets import QApplication
from ui.app import SanjeevaniApp


if __name__ == "__main__":
    # Create QApplication FIRST (before any widgets)
    qt_app = QApplication(sys.argv)
    
    # Create main window
    window = SanjeevaniApp()
    window.show()
    
    # Run the application
    sys.exit(qt_app.exec_())