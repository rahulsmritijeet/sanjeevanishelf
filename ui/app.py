"""
Sanjeevani Shelf v1.1 - Main Application
Kivy-based touchscreen UI for godown management.
"""

import os
import sys
import logging
from pathlib import Path
import yaml
import json

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.core.window import Window
from kivy.config import Config

from database.db_manager import db
from database.migrations import apply_migrations
from hardware.hardware_manager import init_hardware
from comms.whatsapp_queue import init_whatsapp


# Configure Kivy
Config.set('graphics', 'resizable', False)
Config.set('kivy', 'log_level', 'info')


class SanjeevaniApp(App):
    """Main application class."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Setup logging
        self._setup_logging()
        
        # Load configuration
        self.config = self._load_config()
        
        # Set window size
        display_config = self.config.get('display', {})
        Window.size = (
            display_config.get('width', 800),
            display_config.get('height', 480)
        )
        
        if display_config.get('fullscreen', False):
            Window.fullscreen = 'auto'
        
        # Application state
        self.current_language = self.config.get('default_language', 'en')
        self.current_user = None
        self.current_mode = None
        
        # Translations
        self.translations = self._load_translations()
        
        # Initialize subsystems
        self._init_subsystems()
        
        logging.info("Sanjeevani Shelf v1.1 initialized")
    
    def _setup_logging(self):
        """Setup application logging."""
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            handlers=[
                logging.FileHandler('logs/app.log'),
                logging.StreamHandler()
            ]
        )
    
    def _load_config(self):
        """Load application configuration."""
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
        
        for lang_file in i18n_dir.glob('*.json'):
            lang_code = lang_file.stem
            with open(lang_file, 'r', encoding='utf-8') as f:
                translations[lang_code] = json.load(f)
        
        logging.info(f"Loaded translations for: {list(translations.keys())}")
        return translations
    
    def _init_subsystems(self):
        """Initialize hardware and communication subsystems."""
        # Apply database migrations
        apply_migrations()
        
        # Initialize hardware
        simulation = self.config.get('simulation_mode', True)
        self.hardware = init_hardware(self.config, simulation)
        
        # Initialize WhatsApp queue
        self.whatsapp = init_whatsapp(self.config, simulation)
        
        # Check for open sessions (recovery)
        self._check_open_sessions()
    
    def _check_open_sessions(self):
        """Check for open sessions and offer recovery."""
        from core.session_manager import SessionManager
        
        open_sessions = SessionManager.recover_open_sessions()
        
        if open_sessions:
            logging.warning(f"Found {len(open_sessions)} open sessions from previous run")
            
            # In a real app, show recovery dialog
            # For now, auto-rollback
            for session in open_sessions:
                logging.info(f"Rolling back session {session['session_id']}")
                SessionManager.force_rollback_session(session['session_id'])
    
    def build(self):
        """Build the application UI."""
        # Create screen manager
        sm = ScreenManager()
        
        # Import screens
        from ui.screens.startup_screen import StartupScreen
        from ui.screens.storage_screen import StorageScreen
        from ui.screens.selling_screen import SellingScreen
        from ui.screens.buying_screen import BuyingScreen
        from ui.screens.admin_screen import AdminScreen
        from ui.screens.payment_screen import PaymentScreen
        
        # Add screens
        sm.add_widget(StartupScreen(app_instance=self, name='startup'))
        sm.add_widget(StorageScreen(app_instance=self, name='storage'))
        sm.add_widget(SellingScreen(app_instance=self, name='selling'))
        sm.add_widget(BuyingScreen(app_instance=self, name='buying'))
        sm.add_widget(AdminScreen(app_instance=self, name='admin'))
        sm.add_widget(PaymentScreen(app_instance=self, name='payment'))
        
        # Set initial screen
        sm.current = 'startup'
        
        return sm
    
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
                return key  # Return key itself if not found
        
        return value if value else key
    
    def on_stop(self):
        """Cleanup on application exit."""
        logging.info("Application stopping...")
        
        # Stop WhatsApp queue
        if hasattr(self, 'whatsapp') and self.whatsapp:
            self.whatsapp.stop()
        
        # Close hardware connections
        if hasattr(self, 'hardware') and self.hardware:
            self.hardware.close_all()
        
        # Close database
        db.close()
        
        logging.info("Application stopped cleanly")


def main():
    """Main entry point."""
    app = SanjeevaniApp()
    app.run()


if __name__ == '__main__':
    main()