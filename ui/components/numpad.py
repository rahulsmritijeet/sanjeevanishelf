"""
Numeric Keypad Component
On-screen numpad for touch input.
"""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.properties import StringProperty, ObjectProperty
import logging

logger = logging.getLogger(__name__)


class NumPad(BoxLayout):
    """On-screen numeric keypad."""
    
    value = StringProperty('')
    on_submit = ObjectProperty(None)
    
    def __init__(self, max_length=10, allow_decimal=False, on_submit_callback=None, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = 10
        self.spacing = 10
        self.size_hint = (1, 1)
        
        self.max_length = max_length
        self.allow_decimal = allow_decimal
        self.on_submit = on_submit_callback
        
        # Display
        self.display = TextInput(
            text='',
            multiline=False,
            readonly=True,
            font_size='32sp',
            size_hint_y=None,
            height=80,
            halign='right',
            padding=(10, 10)
        )
        self.add_widget(self.display)
        
        # Create keypad
        self._build_keypad()
    
    def _build_keypad(self):
        """Build numpad UI."""
        # Keypad grid
        keypad = GridLayout(cols=3, spacing=5, padding=5, size_hint_y=0.9)
        
        # Number buttons (7-9, 4-6, 1-3)
        buttons = [
            ['7', '8', '9'],
            ['4', '5', '6'],
            ['1', '2', '3'],
        ]
        
        for row in buttons:
            for num in row:
                btn = Button(
                    text=num,
                    font_size='28sp',
                    bold=True,
                    background_color=(0.3, 0.3, 0.3, 1)
                )
                btn.bind(on_press=lambda x, n=num: self._on_number_press(n))
                keypad.add_widget(btn)
        
        # Bottom row (C, 0, Decimal/Backspace)
        btn_clear = Button(
            text='C',
            font_size='28sp',
            bold=True,
            background_color=(0.8, 0.2, 0.2, 1)
        )
        btn_clear.bind(on_press=self._on_clear)
        keypad.add_widget(btn_clear)
        
        btn_zero = Button(
            text='0',
            font_size='28sp',
            bold=True,
            background_color=(0.3, 0.3, 0.3, 1)
        )
        btn_zero.bind(on_press=lambda x: self._on_number_press('0'))
        keypad.add_widget(btn_zero)
        
        if self.allow_decimal:
            btn_decimal = Button(
                text='.',
                font_size='28sp',
                bold=True,
                background_color=(0.3, 0.3, 0.3, 1)
            )
            btn_decimal.bind(on_press=lambda x: self._on_number_press('.'))
            keypad.add_widget(btn_decimal)
        else:
            btn_backspace = Button(
                text='⌫',
                font_size='28sp',
                bold=True,
                background_color=(0.6, 0.6, 0.2, 1)
            )
            btn_backspace.bind(on_press=self._on_backspace)
            keypad.add_widget(btn_backspace)
        
        self.add_widget(keypad)
        
        # Enter button
        btn_enter = Button(
            text='ENTER',
            font_size='24sp',
            bold=True,
            background_color=(0.2, 0.6, 0.2, 1),
            size_hint_y=0.1
        )
        btn_enter.bind(on_press=self._on_submit)
        self.add_widget(btn_enter)
    
    def _on_number_press(self, number):
        """Handle number button press."""
        current = self.display.text
        
        # Check length limit
        if len(current) >= self.max_length:
            return
        
        # Check decimal
        if number == '.' and '.' in current:
            return
        
        self.display.text += number
        self.value = self.display.text
    
    def _on_clear(self, *args):
        """Clear display."""
        self.display.text = ''
        self.value = ''
    
    def _on_backspace(self, *args):
        """Remove last character."""
        if len(self.display.text) > 0:
            self.display.text = self.display.text[:-1]
            self.value = self.display.text
    
    def _on_submit(self, *args):
        """Submit value."""
        if self.on_submit and self.value:
            self.on_submit(self.value)
    
    def get_value(self):
        """Get current value."""
        return self.display.text
    
    def set_value(self, value):
        """Set display value."""
        self.display.text = str(value)
        self.value = str(value)
    
    def reset(self):
        """Reset numpad."""
        self._on_clear()