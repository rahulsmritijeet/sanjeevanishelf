"""
Sanjeevani Shelf v1.1 - PyQt5 Application
Full multi-language support for English, Hindi, Bengali
"""

import sys
import logging
from pathlib import Path
import yaml
import json
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QStackedWidget, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QPushButton, QLineEdit, QComboBox, QGridLayout,
    QMessageBox, QDialog, QTableWidget, QTableWidgetItem, QTabWidget
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt5.QtGui import QFont, QPixmap, QColor
from PyQt5.QtCore import QSize

from database.db_manager import db
from database.migrations import apply_migrations
from hardware.hardware_manager import init_hardware
from comms.whatsapp_queue import init_whatsapp


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class SanjeevaniApp(QMainWindow):
    """Main PyQt5 Application."""
    
    def __init__(self):
        super().__init__()
        
        # Load configuration
        self.app_config = self._load_config()
        
        # Application state
        self.current_language = self.app_config.get('default_language', 'en')
        self.current_user = None
        self.current_mode = None
        
        # Translations
        self.translations = self._load_translations()
        
        # Initialize subsystems
        self._init_subsystems()
        
        # Setup UI
        self.setWindowTitle('Sanjeevani Shelf v1.1 - Godown Management')
        self.setGeometry(0, 0, 800, 480)
        
        # Create central widget with stacked pages
        self.central_widget = QStackedWidget()
        self.setCentralWidget(self.central_widget)
        
        # Create screens
        self._create_screens()
        
        # Show startup screen
        self.show_screen('startup')
        
        logger.info("Sanjeevani Shelf v1.1 PyQt5 initialized")
    
    def _load_config(self):
        """Load application configuration from YAML."""
        config_path = Path('config/settings.yaml')
        
        if not config_path.exists():
            logger.error("Configuration file not found!")
            return {}
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        logger.info(f"Configuration loaded from {config_path}")
        return config
    
    def _load_translations(self):
        """Load all translation files."""
        translations = {}
        i18n_dir = Path('i18n')
        
        for lang_file in i18n_dir.glob('*.json'):
            lang_code = lang_file.stem
            with open(lang_file, 'r', encoding='utf-8') as f:
                translations[lang_code] = json.load(f)
        
        logger.info(f"Loaded translations for: {list(translations.keys())}")
        return translations
    
    def _init_subsystems(self):
        """Initialize hardware and communication subsystems."""
        try:
            apply_migrations()
        except Exception as e:
            logger.warning(f"Database migration skipped: {e}")
        
        simulation = self.app_config.get('simulation_mode', True)
        try:
            self.hardware = init_hardware(self.app_config, simulation)
        except Exception as e:
            logger.warning(f"Hardware initialization failed: {e}")
            self.hardware = None
        
        try:
            self.whatsapp = init_whatsapp(self.app_config, simulation)
        except Exception as e:
            logger.warning(f"WhatsApp initialization failed: {e}")
            self.whatsapp = None
    
    def _create_screens(self):
        """Create all application screens."""
        self.screens = {}
        
        # Import screens
        from ui.screens.startup_screen import StartupScreen
        from ui.screens.storage_screen import StorageScreen
        from ui.screens.selling_screen import SellingScreen
        from ui.screens.buying_screen import BuyingScreen
        from ui.screens.admin_screen import AdminScreen
        from ui.screens.payment_screen import PaymentScreen
        
        # Create instances
        self.screens['startup'] = StartupScreen(self)
        self.screens['storage'] = StorageScreen(self)
        self.screens['selling'] = SellingScreen(self)
        self.screens['buying'] = BuyingScreen(self)
        self.screens['admin'] = AdminScreen(self)
        self.screens['payment'] = PaymentScreen(self)
        
        # Add to stacked widget
        for screen in self.screens.values():
            self.central_widget.addWidget(screen)
    
    def show_screen(self, screen_name):
        """Show a specific screen."""
        if screen_name in self.screens:
            self.central_widget.setCurrentWidget(self.screens[screen_name])
            logger.info(f"Showing screen: {screen_name}")
    
    def translate(self, key, language=None):
        """
        Translate a key to the current or specified language.
        Key format: "section.subsection.key"
        """
        if language is None:
            language = self.current_language
        
        lang_data = self.translations.get(language, self.translations.get('en', {}))
        
        # Navigate nested dictionary
        keys = key.split('.')
        value = lang_data
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return key
        
        return value if value else key
    
    def closeEvent(self, event):
        """Cleanup on application exit."""
        logger.info("Application stopping...")
        
        if hasattr(self, 'whatsapp') and self.whatsapp:
            try:
                self.whatsapp.stop()
            except:
                pass
        
        if hasattr(self, 'hardware') and self.hardware:
            try:
                self.hardware.close_all()
            except:
                pass
        
        try:
            db.close()
        except:
            pass
        
        logger.info("Application stopped cleanly")
        event.accept()