"""
Selling Flow Screen - PyQt5
Farmer sells stored crop back to godown.
With 5-minute session timer, rate breakdown, SMS notification.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QGridLayout, QDialog, QMessageBox,
    QProgressBar, QFrame
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, QTimer
from datetime import datetime
import logging
from core.inventory import InventoryManager
from core.billing import BillingEngine
from core.session_manager import SessionManager
from hardware.hardware_manager import get_hardware
from comms.whatsapp_queue import get_whatsapp
from comms.whatsapp_templates import WhatsAppTemplates
from payment.payment_simulation import PaymentSimulator
from database.db_manager import db

logger = logging.getLogger(__name__)


class SellingScreen(QWidget):
    """Selling flow screen with timer and rate breakdown."""
    
    def __init__(self, app):
        super().__init__()
        self.app = app
        
        self.inventory = InventoryManager(app.app_config)
        self.billing = BillingEngine(app.app_config)
        self.payment_sim = PaymentSimulator()
        
        self.session = None
        self.batch = None
        self.farmer = None
        self.flow_data = {}
        
        # Session timer
        self._session_timer = QTimer(self)
        self._session_timer.timeout.connect(self._update_session_timer)
        
        self._build_ui()
    
    def _build_ui(self):
        """Build selling UI."""
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Header
        header_layout = QHBoxLayout()
        
        self.title_label = QLabel('SELLING FLOW')
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        header_layout.addWidget(self.title_label, stretch=1)
        
        # Timer
        self.timer_label = QLabel('⏱ 05:00')
        timer_font = QFont()
        timer_font.setPointSize(14)
        timer_font.setBold(True)
        self.timer_label.setFont(timer_font)
        self.timer_label.setStyleSheet("color: green; font-weight: bold;")
        header_layout.addWidget(self.timer_label)
        
        # Cancel button
        btn_cancel = QPushButton('✗ Cancel')
        btn_cancel.setFont(QFont('Arial', 11))
        btn_cancel.setFixedWidth(100)
        btn_cancel.setFixedHeight(40)
        btn_cancel.setStyleSheet("background-color: #F44336; color: white;")
        btn_cancel.clicked.connect(self._cancel_session)
        header_layout.addWidget(btn_cancel)
        
        layout.addLayout(header_layout)
        
        # Progress bar
        self.progress = QProgressBar()
        self.progress.setMaximum(100)
        self.progress.setValue(0)
        layout.addWidget(self.progress)
        
        # Content area
        self.content_area = QVBoxLayout()
        layout.addLayout(self.content_area, stretch=1)
        
        # Control buttons
        self.control_buttons = QHBoxLayout()
        layout.addLayout(self.control_buttons)
        
        self.setLayout(layout)
        
        # Show batch scan
        self.show_batch_scan()
    
    def _update_session_timer(self):
        """Update timer every second."""
        if self.session:
            time_str = self.session.get_time_display()
            self.timer_label.setText(f"⏱ {time_str}")
            
            remaining = self.session.get_remaining_time()
            if remaining <= 60:
                self.timer_label.setStyleSheet("color: red; font-weight: bold;")
            elif remaining <= 120:
                self.timer_label.setStyleSheet("color: orange; font-weight: bold;")
            else:
                self.timer_label.setStyleSheet("color: green; font-weight: bold;")
            
            if self.session.is_expired():
                self._on_session_timeout()
    
    def _on_session_timeout(self):
        """Handle 5-minute timeout."""
        self._session_timer.stop()
        QMessageBox.critical(
            self, "Session Timeout",
            "5-minute session expired!\nAll changes rolled back.\nPlease start again."
        )
        self.app.show_screen('startup')
    
    def _cancel_session(self):
        """Cancel session manually."""
        reply = QMessageBox.question(
            self, 'Cancel Session',
            'Cancel this session?\nAll changes will be lost.',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self._session_timer.stop()
            if self.session:
                self.session.cancel()
            self.app.show_screen('startup')
    
    def show_batch_scan(self):
        """Step 1: Scan batch RFID."""
        self._clear_content()
        
        self.title_label.setText('Step 1: Scan Batch RFID')
        self.progress.setValue(20)
        
        widget = QWidget()
        vlayout = QVBoxLayout()
        
        info_label = QLabel('Scan the RFID tag on the stored sacks to retrieve batch info.')
        info_label.setFont(QFont('Arial', 12))
        info_label.setWordWrap(True)
        vlayout.addWidget(info_label)
        
        vlayout.addSpacing(20)
        
        scan_label = QLabel('📡 Place RFID tag near scanner...')
        scan_label.setFont(QFont('Arial', 16, QFont.Bold))
        scan_label.setStyleSheet("color: green;")
        scan_label.setAlignment(Qt.AlignCenter)
        vlayout.addWidget(scan_label, stretch=1)
        
        widget.setLayout(vlayout)
        self.content_area.addWidget(widget, stretch=1)
        
        # Buttons
        btn_scan = QPushButton('📡 Start Scan')
        btn_scan.setFixedHeight(50)
        btn_scan.setFont(QFont('Arial', 12))
        btn_scan.setStyleSheet("background-color: #33CC33; color: white;")
        btn_scan.clicked.connect(self._on_rfid_scan)
        self.control_buttons.addWidget(btn_scan)
        
        btn_manual = QPushButton('🔧 Manual Entry (Sim)')
        btn_manual.setFixedHeight(50)
        btn_manual.setFont(QFont('Arial', 12))
        btn_manual.setStyleSheet("background-color: #FFAA00; color: white;")
        btn_manual.clicked.connect(self._on_manual_rfid)
        self.control_buttons.addWidget(btn_manual)
    
    def _on_rfid_scan(self):
        """Perform RFID scan."""
        hw = get_hardware()
        uid = hw.rfid.read_uid(timeout=10)
        
        if uid:
            self._on_rfid_received(uid)
        else:
            QMessageBox.warning(self, 'Error', 'RFID scan timeout. Try again.')
    
    def _on_manual_rfid(self):
        """Manual RFID entry (simulation)."""
        row = db.fetchone("SELECT rfid_uid FROM batches WHERE status = 'stored' LIMIT 1")
        if row and row['rfid_uid']:
            self._on_rfid_received(row['rfid_uid'])
        else:
            QMessageBox.warning(self, 'Error', 'No stored batches found in the system.')
    
    def _on_rfid_received(self, uid):
        """Handle RFID scan result."""
        batch = db.get_batch_by_rfid(uid)
        
        if not batch:
            QMessageBox.critical(self, 'Error', f'No stored batch found for RFID: {uid}')
            return
        
        self.batch = batch
        self.farmer = db.get_farmer_by_phone(batch['farmer_phone'])
        self.flow_data['batch_id'] = batch['id']
        self.flow_data['farmer_id'] = self.farmer['id']
        
        # Start session and timer
        user_id = self.app.current_user['id']
        self.session = SessionManager(operator_id=user_id, mode='selling')
        self.session.start(farmer_id=self.farmer['id'])
        self._session_timer.start(1000)
        
        logger.info(f"Batch found: {batch['batch_code']}")
        
        self.show_batch_details()
    
    def show_batch_details(self):
        """Step 2: Show batch details with rate breakdown."""
        self._clear_content()
        
        self.title_label.setText('Step 2: Batch Details & Pricing')
        self.progress.setValue(50)
        
        batch = self.batch
        
        # Calculate selling amount
        amount, breakdown = self.billing.calculate_selling_amount(
            batch['crop_type'],
            batch['weight_kg'],
            batch['quality_grade']
        )
        
        self.flow_data['amount'] = amount
        self.flow_data['billing_breakdown'] = breakdown
        
        # Build details widget
        widget = QWidget()
        details = QVBoxLayout()
        
        # Batch info section
        batch_frame = QFrame()
        batch_frame.setFrameShape(QFrame.Box)
        batch_frame.setStyleSheet("background-color: #E3F2FD; border: 1px solid #90CAF9; border-radius: 5px;")
        batch_layout = QVBoxLayout()
        
        batch_title = QLabel('📦 Batch Information')
        batch_title.setFont(QFont('Arial', 13, QFont.Bold))
        batch_layout.addWidget(batch_title)
        
        batch_layout.addWidget(QLabel(f"   Batch Code: {batch['batch_code']}"))
        batch_layout.addWidget(QLabel(f"   👨‍🌾 Farmer: {batch['farmer_name']}"))
        batch_layout.addWidget(QLabel(f"   🌾 Crop: {batch['crop_type'].upper()}"))
        batch_layout.addWidget(QLabel(f"   ⚖️ Weight: {batch['weight_kg']:.2f} kg"))
        batch_layout.addWidget(QLabel(f"   📊 Quality: Grade {batch['quality_grade']}"))
        batch_layout.addWidget(QLabel(f"   💧 Moisture: {batch['moisture_percent']:.2f}%"))
        batch_layout.addWidget(QLabel(f"   📅 Stored: {batch['storage_date']}"))
        batch_layout.addWidget(QLabel(f"   📅 Expiry: {batch['expiry_date']}"))
        
        batch_frame.setLayout(batch_layout)
        details.addWidget(batch_frame)
        
        details.addSpacing(10)
        
        # Rate breakdown section
        rate_frame = QFrame()
        rate_frame.setFrameShape(QFrame.Box)
        rate_frame.setStyleSheet("background-color: #FFF3E0; border: 1px solid #FFB74D; border-radius: 5px;")
        rate_layout = QVBoxLayout()
        
        rate_title = QLabel('💰 Selling Rate Breakdown')
        rate_title.setFont(QFont('Arial', 13, QFont.Bold))
        rate_layout.addWidget(rate_title)
        
        base_rate = breakdown.get('base_rate', 0)
        quality_multiplier = breakdown.get('quality_multiplier', 1.0)
        base_amount = breakdown.get('base_amount', 0)
        adjusted_amount = breakdown.get('adjusted_amount', 0)
        deductions = breakdown.get('deductions', 0)
        
        rate_layout.addWidget(QLabel(f"   📊 Market Rate: ₹{base_rate:.2f} per kg"))
        rate_layout.addWidget(QLabel(f"   ⚖️ Weight: {batch['weight_kg']:.2f} kg"))
        rate_layout.addWidget(QLabel(f"   💵 Base Amount: ₹{base_rate:.2f} × {batch['weight_kg']:.2f} = ₹{base_amount:.2f}"))
        
        if quality_multiplier != 1.0:
            quality_percent = (quality_multiplier - 1.0) * 100
            prefix = "+" if quality_percent > 0 else ""
            quality_text = f"   📊 Quality {'Premium' if quality_percent > 0 else 'Penalty'}: {prefix}{quality_percent:.0f}% (Grade {batch['quality_grade']})"
            quality_label = QLabel(quality_text)
            if quality_percent > 0:
                quality_label.setStyleSheet("color: green;")
            else:
                quality_label.setStyleSheet("color: red;")
            rate_layout.addWidget(quality_label)
            
            rate_layout.addWidget(QLabel(f"   💵 After Quality: ₹{adjusted_amount:.2f}"))
        
        if deductions > 0:
            ded_label = QLabel(f"   ⚠️ Deductions: -₹{deductions:.2f}")
            ded_label.setStyleSheet("color: red;")
            rate_layout.addWidget(ded_label)
        
        # Separator
        rate_layout.addWidget(QLabel('   ' + '─' * 35))
        
        # Total
        total_label = QLabel(f"   FARMER RECEIVES: ₹{amount:.2f}")
        total_font = QFont()
        total_font.setPointSize(18)
        total_font.setBold(True)
        total_label.setFont(total_font)
        total_label.setStyleSheet("color: #2E7D32;")
        rate_layout.addWidget(total_label)
        
        rate_frame.setLayout(rate_layout)
        details.addWidget(rate_frame)
        
        details.addStretch(1)
        
        widget.setLayout(details)
        self.content_area.addWidget(widget, stretch=1)
        
        # Proceed button
        btn_proceed = QPushButton(f'💰 Proceed to Payout (₹{amount:.2f})')
        btn_proceed.setFixedHeight(60)
        btn_proceed.setFont(QFont('Arial', 14, QFont.Bold))
        btn_proceed.setStyleSheet("background-color: #33CC33; color: white;")
        btn_proceed.clicked.connect(self._show_payment)
        self.control_buttons.addWidget(btn_proceed)
    
    def _show_payment(self):
        """Show payout screen."""
        self.app.show_screen('payment')
        self.app.screens['payment'].setup_payment(
            amount=self.flow_data['amount'],
            transaction_type='selling',
            flow_data=self.flow_data,
            farmer=self.farmer,
            session=self.session,
            batch=self.batch,
            on_complete=self._on_payout_complete
        )
    
    def _on_payout_complete(self, payout_ref):
        """Handle payout completion."""
        self._session_timer.stop()
        
        # Create transaction
        txn_code = f"SELL-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        txn_id = db.insert('transactions', {
            'txn_type': 'selling',
            'txn_code': txn_code,
            'farmer_id': self.farmer['id'],
            'batch_id': self.batch['id'],
            'operator_id': self.app.current_user['id'],
            'crop_type': self.batch['crop_type'],
            'weight_kg': self.batch['weight_kg'],
            'amount': self.flow_data['amount'],
            'payment_status': 'paid',
            'payment_method': 'bank_transfer',
            'payment_ref': payout_ref
        })
        
        # Update batch status to sold
        db.update('batches', {
            'status': 'sold'
        }, 'id = ?', (self.batch['id'],))
        
        # Update inventory (reduce stock)
        db.update_crop_stock(self.batch['crop_type'], -self.batch['weight_kg'])
        
        # Update stack (reduce weight)
        if self.batch['stack_location']:
            self.inventory.update_stack_weight(
                self.batch['stack_location'],
                -self.batch['weight_kg']
            )
        
        # Release RFID tag
        if self.batch['rfid_uid']:
            db.update('rfid_tags', {
                'status': 'available',
                'assigned_to_batch_id': None
            }, 'uid = ?', (self.batch['rfid_uid'],))
        
        # Send SMS notification
        try:
            sms = get_whatsapp()
            breakdown = self.flow_data.get('billing_breakdown', {})
            
            message = WhatsAppTemplates.format_message(
                'SELLING_CONFIRMATION',
                self.app.current_language,
                {
                    'godown_name': self.app.app_config.get('godown_name', 'Godown'),
                    'farmer_name': self.farmer['name'],
                    'batch_code': self.batch['batch_code'],
                    'crop_type': self.batch['crop_type'],
                    'weight_kg': self.batch['weight_kg'],
                    'rate': breakdown.get('base_rate', 0),
                    'amount': self.flow_data['amount'],
                    'payment_method': 'Bank Transfer (Simulated)',
                    'txn_code': txn_code,
                    'txn_date': datetime.now().strftime('%d/%m/%Y %H:%M')
                }
            )
            
            sms.enqueue(
                self.farmer['phone'],
                message,
                self.app.current_language,
                template_name='SELLING_CONFIRMATION',
                priority=10
            )
        except Exception as e:
            logger.error(f"SMS notification failed: {e}")
        
        # Commit session
        self.session.commit()
        
        # Show success
        self.progress.setValue(100)
        breakdown = self.flow_data.get('billing_breakdown', {})
        
        QMessageBox.information(self, 'Sale Completed!',
            f'✅ Sale completed successfully!\n\n'
            f'Batch: {self.batch["batch_code"]}\n'
            f'Crop: {self.batch["crop_type"].upper()}\n'
            f'Weight: {self.batch["weight_kg"]:.2f} kg\n'
            f'Rate: ₹{breakdown.get("base_rate", 0):.2f}/kg\n'
            f'Amount: ₹{self.flow_data["amount"]:.2f}\n\n'
            f'Transaction: {txn_code}\n'
            f'SMS sent to {self.farmer["phone"]}'
        )
        
        self.app.show_screen('startup')
    
    def _clear_content(self):
        """Clear content area safely."""
        if self.content_area:
            while self.content_area.count():
                item = self.content_area.takeAt(0)
                if item and item.widget():
                    item.widget().deleteLater()
        
        if self.control_buttons:
            while self.control_buttons.count():
                item = self.control_buttons.takeAt(0)
                if item and item.widget():
                    item.widget().deleteLater()
    
    def _on_back(self):
        """Go back to startup."""
        self._session_timer.stop()
        if self.session:
            self.session.cancel()
        self.app.show_screen('startup')