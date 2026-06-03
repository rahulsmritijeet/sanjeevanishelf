"""
Startup Screen
Language selection and mode selection.
"""

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
import logging
import bcrypt
from database.db_manager import db

logger = logging.getLogger(__name__)


class StartupScreen(Screen):
    """Initial screen for language and mode selection."""
    
    def __init__(self, app_instance, **kwargs):
        super().__init__(**kwargs)
        self.app = app_instance
        self.name = 'startup'
        self.selected_language = 'en'
        self.selected_mode = None
        
        self._build_ui()
    
    def _build_ui(self):
        """Build startup UI."""
        layout = BoxLayout(orientation='vertical', padding=20, spacing=20)
        
        # Title
        title = Label(
            text='[b]Sanjeevani Shelf v1.1[/b]
Godown Management System',
            markup=True,
            font_size='32sp',
            size_hint_y=0.2,
            halign='center'
        )
        layout.add_widget(title)
        
        # Language selection
        lang_label = Label(
            text='Select Language / भाषा चुनें / ভাষা নির্বাচন করুন',
            font_size='24sp',
            size_hint_y=0.1
        )
        layout.add_widget(lang_label)
        
        # Import language selector
        from ui.components.language_selector import LanguageSelector
        self.lang_selector = LanguageSelector()
        self.lang_selector.on_language_change = self._on_language_changed
        layout.add_widget(self.lang_selector)
        
        # Mode selection
        mode_label = Label(
            text=self._t('startup.select_mode'),
            font_size='24sp',
            size_hint_y=0.1
        )
        layout.add_widget(mode_label)
        
        mode_buttons = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=0.3)
        
        modes = [
            ('storage', 'startup.mode_storage', (0.2, 0.6, 0.8, 1)),
            ('selling', 'startup.mode_selling', (0.8, 0.6, 0.2, 1)),
            ('buying', 'startup.mode_buying', (0.2, 0.8, 0.2, 1)),
            ('admin', 'startup.mode_admin', (0.6, 0.2, 0.6, 1))
        ]
        
        for mode_id, label_key, color in modes:
            btn = Button(
                text=self._t(label_key),
                font_size='24sp',
                bold=True,
                background_color=color
            )
            btn.mode_id = mode_id
            btn.bind(on_press=self._on_mode_selected)
            mode_buttons.add_widget(btn)
        
        layout.add_widget(mode_buttons)
        
        # Footer
        footer = Label(
            text='Simulation Mode' if self.app.config.get('simulation_mode') else 'Production Mode',
            font_size='16sp',
            size_hint_y=0.05,
            color=(1, 0, 0, 1) if self.app.config.get('simulation_mode') else (0, 1, 0, 1)
        )
        layout.add_widget(footer)
        
        self.add_widget(layout)
    
    def _t(self, key):
        """Translate text using current language."""
        return self.app.translate(key, self.selected_language)
    
    def _on_language_changed(self, lang_code):
        """Handle language change."""
        self.selected_language = lang_code
        self.app.current_language = lang_code
        logger.info(f"Language changed to {lang_code}")
        # TODO: Update all UI text
    
    def _on_mode_selected(self, button):
        """Handle mode selection."""
        self.selected_mode = button.mode_id
        logger.info(f"Mode selected: {self.selected_mode}")
        
        # Show PIN entry popup
        self._show_pin_popup()
    
    def _show_pin_popup(self):
        """Show operator PIN entry."""
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        label = Label(
            text=self._t('auth.enter_pin'),
            font_size='20sp',
            size_hint_y=0.2
        )
        content.add_widget(label)
        
        pin_input = TextInput(
            multiline=False,
            password=True,
            font_size='24sp',
            size_hint_y=0.3
        )
        content.add_widget(pin_input)
        
        btn_layout = BoxLayout(size_hint_y=0.3, spacing=10)
        
        popup = Popup(
            title='Operator Login',
            content=content,
            size_hint=(0.6, 0.5),
            auto_dismiss=False
        )
        
        def on_login(*args):
            pin = pin_input.text
            user = self._verify_pin(pin)
            if user:
                popup.dismiss()
                self.app.current_user = user
                self.app.current_mode = self.selected_mode
                self._navigate_to_mode()
            else:
                pin_input.text = ''
                label.text = self._t('auth.invalid_pin')
                label.color = (1, 0, 0, 1)
        
        btn_login = Button(text=self._t('auth.login'), font_size='20sp')
        btn_login.bind(on_press=on_login)
        btn_layout.add_widget(btn_login)
        
        btn_cancel = Button(text=self._t('common.cancel'), font_size='20sp')
        btn_cancel.bind(on_press=popup.dismiss)
        btn_layout.add_widget(btn_cancel)
        
        content.add_widget(btn_layout)
        
        popup.open()
    
    def _verify_pin(self, pin):
        """Verify operator PIN."""
        # Hash the entered PIN and compare with database
        users = db.fetchall("SELECT * FROM users WHERE active = 1")
        
        for user in users:
            stored_hash = user['pin_hash']
            if bcrypt.checkpw(pin.encode('utf-8'), stored_hash.encode('utf-8')):
                logger.info(f"User authenticated: {user['username']}")
                return dict(user)
        
        logger.warning(f"Authentication failed for PIN")
        return None
    
    def _navigate_to_mode(self):
        """Navigate to selected mode screen."""
        screen_map = {
            'storage': 'storage',
            'selling': 'selling',
            'buying': 'buying',
            'admin': 'admin'
        }
        
        screen_name = screen_map.get(self.selected_mode)
        if screen_name:
            self.manager.current = screen_name
        else:
            logger.error(f"Unknown mode: {self.selected_mode}")