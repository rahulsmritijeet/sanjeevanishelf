"""
Numeric Keypad Component
On-screen numpad for touch input.
"""

from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.properties import StringProperty, ObjectProperty
import logging

logger = logging.getLogger(__name__)


class NumPad(GridLayout):
    """On-screen numeric keypad."""
    
    value = StringProperty('')
    on_submit = ObjectProperty(None)
    
    def __init__(self, max_length=10, allow_decimal=False, **kwargs):
        super().__init__(**kwargs)
        self.cols = 3
        self.spacing = 5
        self.padding = 10
        self.max_length = max_length
        self.allow_decimal = allow_decimal
        
        # Display
        self.display = TextInput(
            text='',
            multiline=False,
            readonly=True,
            font_size='32sp',
            size_hint_y=None,
            height=80,
            halign='right'
        )
        
        # Create layout
        self._build_ui()
    
    def _build_ui(self):
        """Build numpad UI."""
        # Add display at top (spanning all columns)
        self.add_widget(self.display)
        self.add_widget(Button(size_hint_y=None, height=0))  # Spacer
        self.add_widget(Button(size_hint_y=None, height=0))  # Spacer
        
        # Number buttons
        buttons = [
            '7', '8', '9',
            '4', '5', '6',
            '1', '2', '3',
        ]
        
        for num in buttons:
            btn = Button(
                text=num,
                font_size='28sp',
                bold=True,
                size_hint_y=None,
                height=80
            )
            btn.bind(on_press=lambda x, n=num: self._on_number_press(n))
            self.add_widget(btn)
        
        # Bottom row: Clear, 0, Backspace
        btn_clear = Button(
            text='C',
            font_size='28sp',
            bold=True,
            background_color=(0.8, 0.2, 0.2, 1),
            size_hint_y=None,
            height=80
        )
        btn_clear.bind(on_press=self._on_clear)
        self.add_widget(btn_clear)
        
        btn_zero = Button(
            text='0',
            font_size='28sp',
            bold=True,
            size_hint_y=None,
            height=80
        )
        btn_zero.bind(on_press=lambda x: self._on_number_press('0'))
        self.add_widget(btn_zero)
        
        if self.allow_decimal:
            btn_decimal = Button(
                text='.',
                font_size='28sp',
                bold=True,
                size_hint_y=None,
                height=80
            )
            btn_decimal.bind(on_press=lambda x: self._on_number_press('.'))
            self.add_widget(btn_decimal)
        else:
            btn_backspace = Button(
                text='⌫',
                font_size='28sp',
                bold=True,
                background_color=(0.6, 0.6, 0.2, 1),
                size_hint_y=None,
                height=80
            )
            btn_backspace.bind(on_press=self._on_backspace)
            self.add_widget(btn_backspace)
        
        # Enter button (spanning bottom)
        btn_enter = Button(
            text='ENTER',
            font_size='28sp',
            bold=True,
            background_color=(0.2, 0.6, 0.2, 1),
            size_hint_y=None,
            height=80
        )
        btn_enter.bind(on_press=self._on_submit)
        self.add_widget(btn_enter)
        self.add_widget(Button(size_hint_y=None, height=0))  # Spacer
        self.add_widget(Button(size_hint_y=None, height=0))  # Spacer
    
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