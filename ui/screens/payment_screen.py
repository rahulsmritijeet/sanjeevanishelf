"""
Payment Screen - PyQt5
QR display and simulation payment buttons.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QMessageBox, QFrame
)
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtCore import Qt
from datetime import datetime
import logging
from payment.razorpay_handler import RazorpayHandler
from payment.payment_simulation import PaymentSimulator
from database.db_manager import db

logger = logging.getLogger(__name__)


class PaymentScreen(QWidget):
    """Payment/QR display screen."""
    
    def __init__(self, app):
        super().__init__()
        self.app = app
        
        self.razorpay = RazorpayHandler(app.app_config, simulation=app.app_config.get('simulation_mode'))
        self.payment_sim = PaymentSimulator()
        
        self.amount = 0
        self.transaction_type = 'storage'
        self.flow_data = {}
        self.farmer = None
        self.session = None
        self.batch = None
        self.on_complete_callback = None
        
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)
    
    def setup_payment(self, amount, transaction_type='storage', flow_data=None, 
                     farmer=None, session=None, batch=None, on_complete=None):
        """Setup payment screen."""
        self.amount = amount
        self.transaction_type = transaction_type
        self.flow_data = flow_data or {}
        self.farmer = farmer
        self.session = session
        self.batch = batch
        self.on_complete_callback = on_complete
        
        # Clear layout
        while self.main_layout.count():
            child = self.main_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Build UI based on transaction type
        if transaction_type == 'storage':
            self._build_storage_payment()
        elif transaction_type == 'selling':
            self._build_payout_ui('selling')
        elif transaction_type == 'buying':
            self._build_payout_ui('buying')
    
    def _build_storage_payment(self):
        """Build storage payment UI."""
        # Title
        title = QLabel('💳 PAYMENT - Storage Fee')
        title_font = QFont()
        title_font.setPointSize(22)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(title)
        
        # Amount display
        amount_frame = QFrame()
        amount_frame.setFrameShape(QFrame.Box)
        amount_frame.setStyleSheet("background-color: #E8F5E9; border: 2px solid #4CAF50; border-radius: 5px;")
        amount_layout = QVBoxLayout()
        
        amount_label = QLabel(f'Amount to Pay: ₹{self.amount:.2f}')
        amount_font = QFont()
        amount_font.setPointSize(24)
        amount_font.setBold(True)
        amount_label.setFont(amount_font)
        amount_label.setStyleSheet("color: #2E7D32;")
        amount_label.setAlignment(Qt.AlignCenter)
        amount_layout.addWidget(amount_label)
        
        amount_frame.setLayout(amount_layout)
        amount_frame.setFixedHeight(100)
        self.main_layout.addWidget(amount_frame)
        
        # QR Code display
        qr_label = QLabel('📱 Scan QR Code to Pay')
        qr_label.setFont(QFont('Arial', 14))
        qr_label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(qr_label)
        
        # QR Code image (placeholder)
        qr_frame = QFrame()
        qr_frame.setFrameShape(QFrame.Box)
        qr_frame.setStyleSheet("background-color: white; border: 2px solid #CCCCCC;")
        qr_layout = QVBoxLayout()
        
        qr_placeholder = QLabel('[QR Code would be displayed here]')
        qr_placeholder.setFont(QFont('Arial', 12))
        qr_placeholder.setAlignment(Qt.AlignCenter)
        qr_placeholder.setStyleSheet("color: #999999;")
        qr_layout.addWidget(qr_placeholder)
        
        # Generate actual QR (if not simulation)
        self._generate_qr_code(qr_placeholder)
        
        qr_frame.setLayout(qr_layout)
        qr_frame.setFixedHeight(200)
        self.main_layout.addWidget(qr_frame, stretch=1)
        
        # Simulation payment button
        btn_pay = QPushButton(f'✓ PAYMENT DONE\n₹{self.amount:.2f}\n(SIMULATION)')
        btn_pay.setFixedHeight(100)
        btn_pay_font = QFont()
        btn_pay_font.setPointSize(16)
        btn_pay_font.setBold(True)
        btn_pay.setFont(btn_pay_font)
        btn_pay.setStyleSheet(
            "background-color: #4CAF50; color: white; border-radius: 5px; "
            "font-weight: bold; padding: 10px;"
        )
        btn_pay.clicked.connect(self._on_payment_done)
        self.main_layout.addWidget(btn_pay)
        
        # Cancel button
        btn_cancel = QPushButton('✗ Cancel')
        btn_cancel.setFixedHeight(50)
        btn_cancel.setFont(QFont('Arial', 12))
        btn_cancel.setStyleSheet("background-color: #F44336; color: white; border-radius: 5px;")
        btn_cancel.clicked.connect(self._on_cancel)
        self.main_layout.addWidget(btn_cancel)
    
    def _build_payout_ui(self, txn_type):
        """Build payout UI (for selling/buying)."""
        # Title
        if txn_type == 'selling':
            title_text = '💰 PAYOUT - Selling Payment'
        else:
            title_text = '💰 PAYMENT - Buying (to Farmer)'
        
        title = QLabel(title_text)
        title_font = QFont()
        title_font.setPointSize(22)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(title)
        
        # Amount display
        amount_frame = QFrame()
        amount_frame.setFrameShape(QFrame.Box)
        amount_frame.setStyleSheet("background-color: #FFF3E0; border: 2px solid #FF9800; border-radius: 5px;")
        amount_layout = QVBoxLayout()
        
        amount_label = QLabel(f'Amount to Pay Farmer: ₹{self.amount:.2f}')
        amount_font = QFont()
        amount_font.setPointSize(24)
        amount_font.setBold(True)
        amount_label.setFont(amount_font)
        amount_label.setStyleSheet("color: #E65100;")
        amount_label.setAlignment(Qt.AlignCenter)
        amount_layout.addWidget(amount_label)
        
        amount_frame.setLayout(amount_layout)
        amount_frame.setFixedHeight(100)
        self.main_layout.addWidget(amount_frame)
        
        # Farmer details
        if self.farmer:
            farmer_frame = QFrame()
            farmer_frame.setFrameShape(QFrame.Box)
            farmer_frame.setStyleSheet("background-color: #F5F5F5; border: 1px solid #CCCCCC;")
            farmer_layout = QVBoxLayout()
            
            farmer_layout.addWidget(QLabel(f"Farmer: {self.farmer['name']}"))
            farmer_layout.addWidget(QLabel(f"Phone: {self.farmer['phone']}"))
            
            if self.farmer.get('bank_account'):
                farmer_layout.addWidget(QLabel(f"Bank A/C: {self.farmer['bank_account']}"))
            
            farmer_frame.setLayout(farmer_layout)
            self.main_layout.addWidget(farmer_frame)
        
        # Payment method info
        method_label = QLabel('Payment Method: Bank Transfer (Simulated)')
        method_label.setFont(QFont('Arial', 12))
        method_label.setAlignment(Qt.AlignCenter)
        method_label.setStyleSheet("color: #666666;")
        self.main_layout.addWidget(method_label)
        
        self.main_layout.addStretch(1)
        
        # Simulation payout button
        btn_payout = QPushButton(f'✓ PAYOUT DONE\n₹{self.amount:.2f}\n(SIMULATION)')
        btn_payout.setFixedHeight(100)
        btn_payout_font = QFont()
        btn_payout_font.setPointSize(16)
        btn_payout_font.setBold(True)
        btn_payout.setFont(btn_payout_font)
        btn_payout.setStyleSheet(
            "background-color: #FF9800; color: white; border-radius: 5px; "
            "font-weight: bold; padding: 10px;"
        )
        btn_payout.clicked.connect(self._on_payout_done)
        self.main_layout.addWidget(btn_payout)
        
        # Cancel button
        btn_cancel = QPushButton('✗ Cancel')
        btn_cancel.setFixedHeight(50)
        btn_cancel.setFont(QFont('Arial', 12))
        btn_cancel.setStyleSheet("background-color: #F44336; color: white; border-radius: 5px;")
        btn_cancel.clicked.connect(self._on_cancel)
        self.main_layout.addWidget(btn_cancel)
    
    def _generate_qr_code(self, qr_widget):
        """Generate QR code for payment."""
        try:
            txn_id = f"TXN-{int(datetime.now().timestamp())}"
            qr_url, qr_bytes = self.razorpay.create_qr_code(
                self.amount,
                txn_id,
                f"{self.transaction_type.title()} Payment"
            )
            
            if qr_bytes:
                pixmap = QPixmap()
                pixmap.loadFromData(qr_bytes)
                pixmap = pixmap.scaled(180, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                qr_widget.setPixmap(pixmap)
                qr_widget.setText('')
            else:
                qr_widget.setText('[QR Generation Failed]')
        except Exception as e:
            logger.error(f"QR generation error: {e}")
            qr_widget.setText('[QR Code - Simulation Mode]')
    
    def _on_payment_done(self):
        """Handle payment simulation."""
        success, payment_ref = self.payment_sim.simulate_payment_received(
            transaction_id=0,
            amount=self.amount,
            payment_method='simulation'
        )
        
        if success and self.on_complete_callback:
            self.on_complete_callback(payment_ref)
    
    def _on_payout_done(self):
        """Handle payout simulation."""
        farmer_id = self.farmer['id'] if self.farmer else 0
        
        success, payout_ref = self.payment_sim.simulate_payout_sent(
            transaction_id=0,
            farmer_id=farmer_id,
            amount=self.amount,
            bank_account=self.farmer.get('bank_account', 'XXXX1234') if self.farmer else 'XXXX1234'
        )
        
        if success and self.on_complete_callback:
            self.on_complete_callback(payout_ref)
    
    def _on_cancel(self):
        """Cancel payment."""
        if self.session:
            self.session.rollback()
        self.app.show_screen('startup')