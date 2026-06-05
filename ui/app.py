"""
Sanjeevani Shelf v1.1 - PyQt5 Application
Full multi-language support, UTF-8 logging, session management.
"""

import sys
import os
import logging
from pathlib import Path
import yaml
import json
from datetime import datetime

# Fix Windows Unicode
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QStackedWidget, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QPushButton, QLineEdit, QComboBox, QGridLayout,
    QMessageBox, QDialog, QTableWidget, QTableWidgetItem, QTabWidget
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

from database.db_manager import db
from database.migrations import apply_migrations
from hardware.hardware_manager import init_hardware
from comms.whatsapp_queue import init_whatsapp


class SanjeevaniApp(QMainWindow):
    """Main PyQt5 Application."""
    
    def __init__(self):
        super().__init__()
        
        # Setup logging FIRST
        self._setup_logging()
        
        # Load configuration
        self.app_config = self._load_config()
        
        # Application state
        self.current_language = self.app_config.get('default_language', 'en')
        self.current_user = None
        self.current_mode = None
        self.simulation_mode = self.app_config.get('simulation_mode', True)
        
        # Translations
        self.translations = self._load_translations()
        
        # Initialize subsystems
        self._init_subsystems()
        
        # Setup UI
        self.setWindowTitle('Sanjeevani Shelf v1.1 - Godown Management')
        
        display = self.app_config.get('display', {})
        self.setGeometry(0, 0,
            display.get('width', 800),
            display.get('height', 480)
        )
        
        # Create central widget
        self.central_widget = QStackedWidget()
        self.setCentralWidget(self.central_widget)
        
        # Create screens
        self._create_screens()
        
        # Show startup screen
        self.show_screen('startup')
        
        logging.info("Sanjeevani Shelf v1.1 PyQt5 initialized")
    
    def _setup_logging(self):
        """Setup application logging with UTF-8 support."""
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        
        # Clear existing handlers
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        root_logger.setLevel(logging.INFO)
        
        # File handler (UTF-8)
        file_handler = logging.FileHandler('logs/app.log', encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        ))
        root_logger.addHandler(file_handler)
        
        # Console handler (UTF-8 safe for Windows)
        try:
            if sys.platform == 'win32':
                console_stream = open(sys.stdout.fileno(), 'w', encoding='utf-8', closefd=False)
            else:
                console_stream = sys.stdout
            
            console_handler = logging.StreamHandler(console_stream)
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(logging.Formatter(
                '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
            ))
            root_logger.addHandler(console_handler)
        except Exception:
            # Fallback console handler
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(logging.Formatter(
                '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
            ))
            root_logger.addHandler(console_handler)
    
    def _load_config(self):
        """Load configuration from YAML."""
        config_path = Path('config/settings.yaml')
        
        if not config_path.exists():
            logging.error("Configuration file not found!")
            return {}
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        logging.info(f"Configuration loaded from {config_path}")
        return config
    
    def _load_translations(self):
        """Load all translation files."""
        translations = {}
        i18n_dir = Path('i18n')
        
        if not i18n_dir.exists():
            logging.warning("i18n directory not found")
            return translations
        
        for lang_file in i18n_dir.glob('*.json'):
            lang_code = lang_file.stem
            try:
                with open(lang_file, 'r', encoding='utf-8') as f:
                    translations[lang_code] = json.load(f)
            except Exception as e:
                logging.error(f"Failed to load {lang_file}: {e}")
        
        logging.info(f"Loaded translations for: {list(translations.keys())}")
        return translations
    
    def _init_subsystems(self):
        """Initialize hardware and communication subsystems."""
        # Database migrations
        try:
            apply_migrations()
        except Exception as e:
            logging.warning(f"Database migration: {e}")
        
        # Hardware
        simulation = self.app_config.get('simulation_mode', True)
        try:
            self.hardware = init_hardware(self.app_config, simulation)
        except Exception as e:
            logging.warning(f"Hardware init: {e}")
            self.hardware = None
        
        # SMS/WhatsApp queue
        try:
            self.sms = init_whatsapp(self.app_config, simulation)
        except Exception as e:
            logging.warning(f"SMS init: {e}")
            self.sms = None
        
        # Recover open sessions
        try:
            from core.session_manager import SessionManager
            open_sessions = SessionManager.recover_open_sessions()
            if open_sessions:
                logging.warning(f"Recovered {len(open_sessions)} open sessions")
        except Exception as e:
            logging.warning(f"Session recovery: {e}")
    
    def _create_screens(self):
        """Create all application screens."""
        self.screens = {}
        
        try:
            from ui.screens.startup_screen import StartupScreen
            from ui.screens.storage_screen import StorageScreen
            from ui.screens.selling_screen import SellingScreen
            from ui.screens.buying_screen import BuyingScreen
            from ui.screens.admin_screen import AdminScreen
            from ui.screens.payment_screen import PaymentScreen
            
            self.screens['startup'] = StartupScreen(self)
            self.screens['storage'] = StorageScreen(self)
            self.screens['selling'] = SellingScreen(self)
            self.screens['buying'] = BuyingScreen(self)
            self.screens['admin'] = AdminScreen(self)
            self.screens['payment'] = PaymentScreen(self)
            
            for screen in self.screens.values():
                self.central_widget.addWidget(screen)
            
            logging.info(f"Created {len(self.screens)} screens")
        
        except Exception as e:
            logging.error(f"Failed to create screens: {e}")
            import traceback
            traceback.print_exc()
    
    def show_screen(self, screen_name):
        """Show a specific screen."""
        if screen_name in self.screens:
            self.central_widget.setCurrentWidget(self.screens[screen_name])
            logging.info(f"Showing screen: {screen_name}")
        else:
            logging.error(f"Screen not found: {screen_name}")
    
    def translate(self, key, language=None):
        """Translate a key."""
        if language is None:
            language = self.current_language
        
        lang_data = self.translations.get(language, self.translations.get('en', {}))
        
        keys = key.split('.')
        value = lang_data
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return key
        
        return value if value else key
    
    def closeEvent(self, event):
        """Cleanup on exit."""
        logging.info("Application stopping...")
        
        if hasattr(self, 'sms') and self.sms:
            try:
                self.sms.stop()
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
        
        logging.info("Application stopped cleanly")
        event.accept()