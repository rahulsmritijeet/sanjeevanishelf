"""
Startup Screen - PyQt5
Language selection and mode selection.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGridLayout, QLineEdit, QDialog, QMessageBox
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
import logging
import bcrypt
from database.db_manager import db

logger = logging.getLogger(__name__)


class StartupScreen(QWidget):
    """Startup screen with language and mode selection."""
    
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.selected_language = 'en'
        self.selected_mode = None
        self._build_ui()
    
    def _build_ui(self):
        """Build startup UI."""
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel('Sanjeevani Shelf v1.1\nGodown Management System')
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title, stretch=20)
        
        # Language selection
        lang_label = QLabel('Select Language / भाषा चुनें / ভাষা নির্বাচন করুন')
        lang_font = QFont()
        lang_font.setPointSize(14)
        lang_label.setFont(lang_font)
        layout.addWidget(lang_label)
        
        # Language buttons
        lang_layout = QHBoxLayout()
        langs = [('en', 'English'), ('hi', 'हिन्दी'), ('bn', 'বাংলা')]
        
        self.lang_buttons = {}
        for lang_code, lang_name in langs:
            btn = QPushButton(lang_name)
            btn_font = QFont()
            btn_font.setPointSize(12)
            btn.setFont(btn_font)
            btn.setFixedHeight(50)
            btn.clicked.connect(lambda checked, lc=lang_code: self._on_language_selected(lc))
            
            if lang_code == self.selected_language:
                btn.setStyleSheet("background-color: #33CC33; color: white; font-weight: bold;")
            else:
                btn.setStyleSheet("background-color: #CCCCCC; color: black;")
            
            self.lang_buttons[lang_code] = btn
            lang_layout.addWidget(btn)
        
        layout.addLayout(lang_layout, stretch=10)
        
        # Mode selection
        mode_label = QLabel(self.app.translate('startup.select_mode', self.selected_language))
        mode_font = QFont()
        mode_font.setPointSize(14)
        mode_label.setFont(mode_font)
        layout.addWidget(mode_label)
        
        # Mode buttons
        mode_grid = QGridLayout()
        modes = [
            ('storage', 'startup.mode_storage', '#3366FF'),
            ('selling', 'startup.mode_selling', '#FFAA00'),
            ('buying', 'startup.mode_buying', '#33CC33'),
            ('admin', 'startup.mode_admin', '#CC33FF'),
        ]
        
        for i, (mode_id, label_key, color) in enumerate(modes):
            btn = QPushButton(self.app.translate(label_key, self.selected_language))
            btn.setFixedHeight(80)
            btn_font = QFont()
            btn_font.setPointSize(12)
            btn_font.setBold(True)
            btn.setFont(btn_font)
            btn.setStyleSheet(f"background-color: {color}; color: white; border-radius: 5px; font-weight: bold;")
            btn.clicked.connect(lambda checked, mid=mode_id: self._on_mode_selected(mid))
            
            mode_grid.addWidget(btn, i // 2, i % 2)
        
        layout.addLayout(mode_grid, stretch=30)
        
        # Footer
        sim_mode = self.app.app_config.get('simulation_mode', False)
        footer_text = '⚠️ SIMULATION MODE' if sim_mode else '✓ PRODUCTION MODE'
        footer = QLabel(footer_text)
        footer_font = QFont()
        footer_font.setPointSize(10)
        footer.setFont(footer_font)
        footer.setAlignment(Qt.AlignCenter)
        
        if sim_mode:
            footer.setStyleSheet("color: red; font-weight: bold;")
        else:
            footer.setStyleSheet("color: green; font-weight: bold;")
        
        layout.addWidget(footer)
        
        self.setLayout(layout)
    
    def _on_language_selected(self, lang_code):
        """Handle language selection."""
        self.selected_language = lang_code
        self.app.current_language = lang_code
        logger.info(f"Language changed to {lang_code}")
        
        # Update button colors
        for lc, btn in self.lang_buttons.items():
            if lc == lang_code:
                btn.setStyleSheet("background-color: #33CC33; color: white; font-weight: bold;")
            else:
                btn.setStyleSheet("background-color: #CCCCCC; color: black;")
    
    def _on_mode_selected(self, mode_id):
        """Handle mode selection."""
        self.selected_mode = mode_id
        logger.info(f"Mode selected: {mode_id}")
        
        # Show PIN entry dialog
        self._show_pin_dialog()
    
    def _show_pin_dialog(self):
        """Show PIN entry dialog."""
        dialog = QDialog(self)
        dialog.setWindowTitle('Operator Login')
        dialog.setGeometry(150, 100, 500, 300)
        dialog.setStyleSheet("background-color: white;")
        
        layout = QVBoxLayout()
        
        # Title
        title = QLabel(self.app.translate('auth.enter_pin', self.selected_language))
        title_font = QFont()
        title_font.setPointSize(14)
        title.setFont(title_font)
        layout.addWidget(title)
        
        # PIN input
        pin_input = QLineEdit()
        pin_input.setEchoMode(QLineEdit.Password)
        pin_input.setFont(QFont('Arial', 18))
        pin_input.setFixedHeight(50)
        layout.addWidget(pin_input)
        
        # Status message
        status = QLabel('')
        status.setStyleSheet("color: red; font-weight: bold;")
        layout.addWidget(status)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        def on_login():
            pin = pin_input.text()
            user = self._verify_pin(pin)
            
            if user:
                dialog.accept()
                self.app.current_user = user
                self.app.current_mode = self.selected_mode
                self.app.show_screen(self.selected_mode)
            else:
                pin_input.setText('')
                status.setText(self.app.translate('auth.invalid_pin', self.selected_language))
        
        btn_login = QPushButton(self.app.translate('auth.login', self.selected_language))
        btn_login.setFixedHeight(50)
        btn_login.setFont(QFont('Arial', 12))
        btn_login.clicked.connect(on_login)
        btn_layout.addWidget(btn_login)
        
        btn_cancel = QPushButton(self.app.translate('common.cancel', self.selected_language))
        btn_cancel.setFixedHeight(50)
        btn_cancel.setFont(QFont('Arial', 12))
        btn_cancel.clicked.connect(dialog.reject)
        btn_layout.addWidget(btn_cancel)
        
        layout.addLayout(btn_layout)
        
        dialog.setLayout(layout)
        dialog.exec_()
    
    def _verify_pin(self, pin):
        """Verify operator PIN."""
        try:
            users = db.fetchall("SELECT * FROM users WHERE active = 1")
            
            for user in users:
                stored_hash = user['pin_hash']
                if bcrypt.checkpw(pin.encode('utf-8'), stored_hash.encode('utf-8')):
                    logger.info(f"User authenticated: {user['username']}")
                    return dict(user)
        except Exception as e:
            logger.error(f"PIN verification error: {e}")
        
        logger.warning(f"Authentication failed for PIN")
        return None