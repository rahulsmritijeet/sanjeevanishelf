"""
Language Selector Component
Dropdown/button group for switching languages.
"""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.properties import StringProperty, ObjectProperty
import json
import logging

logger = logging.getLogger(__name__)


class LanguageSelector(BoxLayout):
    """Language selection widget."""
    
    current_language = StringProperty('en')
    on_language_change = ObjectProperty(None)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = 60
        self.padding = 10
        self.spacing = 10
        
        self.languages = {
            'en': 'English',
            'hi': 'हिन्दी',
            'bn': 'বাংলা'
        }
        
        self._create_buttons()
    
    def _create_buttons(self):
        """Create language selection buttons."""
        for lang_code, lang_name in self.languages.items():
            btn = Button(
                text=lang_name,
                font_size='20sp',
                bold=True,
                size_hint=(1, 1)
            )
            btn.lang_code = lang_code
            btn.bind(on_press=self._on_language_selected)
            self.add_widget(btn)
            
            # Highlight current language
            if lang_code == self.current_language:
                btn.background_color = (0.2, 0.6, 0.2, 1)
    
    def _on_language_selected(self, button):
        """Handle language selection."""
        old_lang = self.current_language
        self.current_language = button.lang_code
        
        # Update button colors
        for child in self.children:
            if hasattr(child, 'lang_code'):
                if child.lang_code == self.current_language:
                    child.background_color = (0.2, 0.6, 0.2, 1)
                else:
                    child.background_color = (1, 1, 1, 1)
        
        logger.info(f"Language changed: {old_lang} -> {self.current_language}")
        
        # Trigger callback if set
        if self.on_language_change:
            self.on_language_change(self.current_language)
    
    def get_current_language(self):
        """Get current language code."""
        return self.current_language
    
    def set_language(self, lang_code):
        """Programmatically set language."""
        if lang_code in self.languages:
            self.current_language = lang_code
            # Update UI
            for child in self.children:
                if hasattr(child, 'lang_code') and child.lang_code == lang_code:
                    child.dispatch('on_press')