"""
Selling Flow Screen - PyQt5
Farmer sells stored crop back to godown.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QGridLayout, QDialog, QMessageBox,
    QProgressBar, QTableWidget, QTableWidgetItem
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
    """Selling flow screen."""
    
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
        title_font.setPointSize(20)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        header_layout.addWidget(self.title_label, stretch=1)
        
        btn_back = QPushButton('← Back')
        btn_back.setFont(QFont('Arial', 12))
        btn_back.setFixedWidth(100)
        btn_back.setStyleSheet("background-color: #CC3333; color: white;")
        btn_back.clicked.connect(self._on_back)
        header_layout.addWidget(btn_back)
        
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
        
        # Show batch scan screen
        self.show_batch_scan()
    
    def show_batch_scan(self):
        """Step 1: Scan batch RFID."""
        self._clear_content()
        
        self.title_label.setText('Step 1: Scan Batch RFID')
        self.progress.setValue(20)
        
        info = QVBoxLayout()
        
        scan_label = QLabel('Scan the RFID tag on the sacks...')
        scan_label.setFont(QFont('Arial', 16, QFont.Bold))
        scan_label.setStyleSheet("color: green;")
        info.addWidget(scan_label, stretch=1)
        
        self.content_area.addLayout(info, stretch=1)
        
        # Control buttons
        btn_scan = QPushButton('Start Scan')
        btn_scan.setFixedHeight(50)
        btn_scan.setStyleSheet("background-color: #33CC33; color: white;")
        btn_scan.clicked.connect(self._on_rfid_scan)
        self.control_buttons.addWidget(btn_scan)
        
        btn_manual = QPushButton('Manual Entry (Sim)')
        btn_manual.setFixedHeight(50)
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
            QMessageBox.warning(self, 'Error', 'RFID scan timeout')
    
    def _on_manual_rfid(self):
        """Manual RFID entry (simulation)."""
        row = db.fetchone("SELECT rfid_uid FROM batches WHERE status = 'stored' LIMIT 1")
        if row:
            self._on_rfid_received(row['rfid_uid'])
        else:
            QMessageBox.warning(self, 'Error', 'No stored batches found')
    
    def _on_rfid_received(self, uid):
        """Handle RFID scan result."""
        batch = db.get_batch_by_rfid(uid)
        
        if not batch:
            QMessageBox.critical(self, 'Error', f'Batch not found for RFID {uid}')
            return
        
        self.batch = batch
        self.farmer = db.get_farmer_by_phone(batch['farmer_phone'])
        self.flow_data['batch_id'] = batch['id']
        self.flow_data['farmer_id'] = self.farmer['id']
        
        user_id = self.app.current_user['id']
        self.session = SessionManager(operator_id=user_id, mode='selling')
        self.session.start(farmer_id=self.farmer['id'])
        
        logger.info(f"Batch found: {batch['batch_code']}")
        
        self.show_batch_details()
    
    def show_batch_details(self):
        """Step 2: Show batch details and calculate amount."""
        self._clear_content()
        
        self.title_label.setText('Step 2: Batch Details')
        self.progress.setValue(50)
        
        batch = self.batch
        
        details = QVBoxLayout()
        
        title = QLabel('[Batch Information]')
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        details.addWidget(title)
        
        details.addWidget(QLabel(f"Batch Code: {batch['batch_code']}"))
        details.addWidget(QLabel(f"Farmer: {batch['farmer_name']}"))
        details.addWidget(QLabel(f"Crop: {batch['crop_type'].upper()}"))
        details.addWidget(QLabel(f"Weight: {batch['weight_kg']:.2f} kg"))
        details.addWidget(QLabel(f"Quality: Grade {batch['quality_grade']}"))
        details.addWidget(QLabel(f"Stored: {batch['storage_date']}"))
        
        # Calculate selling amount
        amount, breakdown = self.billing.calculate_selling_amount(
            batch['crop_type'],
            batch['weight_kg'],
            batch['quality_grade']
        )
        
        self.flow_data['amount'] = amount
        self.flow_data['billing_breakdown'] = breakdown
        
        details.addSpacing(20)
        
        amount_label = QLabel(f"Amount to Pay Farmer: ₹{amount:.2f}")
        amount_font = QFont()
        amount_font.setPointSize(18)
        amount_font.setBold(True)
        amount_label.setFont(amount_font)
        amount_label.setStyleSheet("color: green;")
        details.addWidget(amount_label)
        
        rate_label = QLabel(f"(Rate: ₹{breakdown['base_rate']:.2f}/kg)")
        details.addWidget(rate_label)
        
        self.content_area.addLayout(details, stretch=1)
        
        # Control button
        btn_proceed = QPushButton('Proceed to Payout')
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
        
        # Update batch status
        db.update('batches', {
            'status': 'sold'
        }, 'id = ?', (self.batch['id'],))
        
        # Update inventory
        db.update_crop_stock(self.batch['crop_type'], -self.batch['weight_kg'])
        
        # Update stack
        if self.batch['stack_location']:
            self.inventory.update_stack_weight(self.batch['stack_location'], -self.batch['weight_kg'])
        
        # Release RFID
        db.update('rfid_tags', {
            'status': 'available',
            'assigned_to_batch_id': None
        }, 'uid = ?', (self.batch['rfid_uid'],))
        
        # Send WhatsApp
        whatsapp = get_whatsapp()
        message = WhatsAppTemplates.format_message(
            'SELLING_CONFIRMATION',
            self.app.current_language,
            {
                'godown_name': self.app.app_config.get('godown_name', 'Godown'),
                'farmer_name': self.farmer['name'],
                'batch_code': self.batch['batch_code'],
                'crop_type': self.batch['crop_type'],
                'weight_kg': self.batch['weight_kg'],
                'rate': self.flow_data['billing_breakdown']['base_rate'],
                'amount': self.flow_data['amount'],
                'payment_method': 'Bank Transfer (Simulated)',
                'txn_code': txn_code,
                'txn_date': datetime.now().strftime('%d/%m/%Y %H:%M')
            }
        )
        
        whatsapp.enqueue(
            self.farmer['phone'],
            message,
            self.app.current_language,
            template_name='SELLING_CONFIRMATION',
            priority=10
        )
        
        # Commit session
        self.session.commit()
        
        # Show success
        self.progress.setValue(100)
        QMessageBox.information(self, 'Success', 
            f'Selling completed successfully!\n\n'
            f'Amount: ₹{self.flow_data["amount"]:.2f}\n'
            f'WhatsApp notification sent to farmer.')
        
        # Return to startup
        self.app.show_screen('startup')
    
    def _clear_content(self):
        """Clear content area."""
        while self.content_area.count():
            widget = self.content_area.takeAt(0).widget()
            if widget:
                widget.deleteLater()
            else:
                layout = self.content_area.takeAt(0)
                while layout and layout.count():
                    item = layout.takeAt(0)
                    if item.widget():
                        item.widget().deleteLater()
        
        while self.control_buttons.count():
            widget = self.control_buttons.takeAt(0).widget()
            if widget:
                widget.deleteLater()
    
    def _on_back(self):
        """Go back to startup."""
        if self.session:
            self.session.rollback()
        self.app.show_screen('startup')