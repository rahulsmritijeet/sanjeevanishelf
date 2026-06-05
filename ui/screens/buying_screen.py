"""
Buying Flow Screen - PyQt5
Godown purchases crop directly from farmer.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QGridLayout, QDialog, QMessageBox,
    QProgressBar
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, QTimer
from datetime import datetime, date
import logging
from core.inventory import InventoryManager
from core.quality import QualityControl
from core.billing import BillingEngine
from core.session_manager import SessionManager
from hardware.hardware_manager import get_hardware
from comms.whatsapp_queue import get_whatsapp
from comms.whatsapp_templates import WhatsAppTemplates
from payment.payment_simulation import PaymentSimulator
from database.db_manager import db

logger = logging.getLogger(__name__)


class BuyingScreen(QWidget):
    """Buying flow screen."""
    
    def __init__(self, app):
        super().__init__()
        self.app = app
        
        self.inventory = InventoryManager(app.app_config)
        self.quality = QualityControl()
        self.billing = BillingEngine(app.app_config)
        self.payment_sim = PaymentSimulator()
        
        self.session = None
        self.farmer = None
        self.flow_data = {}
        
        self._build_ui()
    
    def _build_ui(self):
        """Build buying UI."""
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Header
        header_layout = QHBoxLayout()
        
        self.title_label = QLabel('BUYING FLOW')
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
        
        # Show farmer lookup
        self.show_farmer_lookup()
    
    def show_farmer_lookup(self):
        """Step 1: Farmer lookup."""
        self._clear_content()
        
        self.title_label.setText('Step 1: Farmer Lookup')
        self.progress.setValue(10)
        
        label = QLabel('Enter Farmer Phone Number (10 digits):')
        label.setFont(QFont('Arial', 14))
        self.content_area.addWidget(label)
        
        self.phone_input = QLineEdit()
        self.phone_input.setFont(QFont('Arial', 16))
        self.phone_input.setFixedHeight(50)
        self.phone_input.setMaxLength(10)
        self.content_area.addWidget(self.phone_input)
        
        btn_submit = QPushButton('Search Farmer')
        btn_submit.setFont(QFont('Arial', 12))
        btn_submit.setFixedHeight(50)
        btn_submit.setStyleSheet("background-color: #33CC33; color: white;")
        btn_submit.clicked.connect(self._on_phone_submitted)
        self.control_buttons.addWidget(btn_submit)
    
    def _on_phone_submitted(self):
        """Handle phone submission."""
        phone = self.phone_input.text()
        
        if len(phone) != 10:
            QMessageBox.warning(self, 'Error', 'Please enter 10-digit phone number')
            return
        
        farmer = db.get_farmer_by_phone(phone)
        
        if farmer:
            self.farmer = farmer
            self.flow_data['farmer_id'] = farmer['id']
            user_id = self.app.current_user['id']
            self.session = SessionManager(operator_id=user_id, mode='buying')
            self.session.start(farmer_id=farmer['id'])
            self.show_crop_selection()
        else:
            self._show_farmer_registration(phone)
    
    def _show_farmer_registration(self, phone):
        """Show farmer registration form."""
        dialog = QDialog(self)
        dialog.setWindowTitle('Register New Farmer')
        dialog.setGeometry(100, 100, 400, 300)
        
        layout = QVBoxLayout()
        layout.addWidget(QLabel('Register New Farmer'))
        
        form = QGridLayout()
        form.addWidget(QLabel('Phone:'), 0, 0)
        phone_field = QLineEdit(phone)
        phone_field.setReadOnly(True)
        form.addWidget(phone_field, 0, 1)
        
        form.addWidget(QLabel('Name:'), 1, 0)
        name_field = QLineEdit()
        form.addWidget(name_field, 1, 1)
        
        form.addWidget(QLabel('Village:'), 2, 0)
        village_field = QLineEdit()
        form.addWidget(village_field, 2, 1)
        
        layout.addLayout(form)
        
        btn_layout = QHBoxLayout()
        
        def on_register():
            name = name_field.text().strip()
            if not name:
                QMessageBox.warning(dialog, 'Error', 'Name is required')
                return
            
            farmer_id = db.insert('farmers', {
                'phone': phone,
                'name': name,
                'village': village_field.text().strip()
            })
            
            self.farmer = db.get_farmer_by_phone(phone)
            self.flow_data['farmer_id'] = farmer_id
            user_id = self.app.current_user['id']
            self.session = SessionManager(operator_id=user_id, mode='buying')
            self.session.start(farmer_id=farmer_id)
            
            dialog.accept()
            self.show_crop_selection()
        
        btn_register = QPushButton('Register')
        btn_register.setStyleSheet("background-color: #33CC33; color: white;")
        btn_register.clicked.connect(on_register)
        btn_layout.addWidget(btn_register)
        
        btn_cancel = QPushButton('Cancel')
        btn_cancel.clicked.connect(dialog.reject)
        btn_layout.addWidget(btn_cancel)
        
        layout.addLayout(btn_layout)
        dialog.setLayout(layout)
        dialog.exec_()
    
    def show_crop_selection(self):
        """Step 2: Crop selection."""
        self._clear_content()
        
        self.title_label.setText('Step 2: Select Crop Type')
        self.progress.setValue(25)
        
        label = QLabel('Select Crop Type:')
        label.setFont(QFont('Arial', 14))
        self.content_area.addWidget(label)
        
        crops = ['rice', 'wheat', 'maize', 'pulses']
        crop_grid = QGridLayout()
        
        for i, crop in enumerate(crops):
            btn = QPushButton(crop.upper())
            btn.setFont(QFont('Arial', 12, QFont.Bold))
            btn.setFixedHeight(80)
            btn.setStyleSheet("background-color: #3366FF; color: white;")
            btn.clicked.connect(lambda checked, c=crop: self._on_crop_selected(c))
            crop_grid.addWidget(btn, i // 2, i % 2)
        
        self.content_area.addLayout(crop_grid, stretch=1)
    
    def _on_crop_selected(self, crop_type):
        """Handle crop selection."""
        self.flow_data['crop_type'] = crop_type
        self.show_weight_measurement()
    
    def show_weight_measurement(self):
        """Step 3: Weight measurement."""
        self._clear_content()
        
        self.title_label.setText('Step 3: Weight Measurement')
        self.progress.setValue(40)
        
        info = QVBoxLayout()
        
        label = QLabel('Place crop on the scale')
        label.setFont(QFont('Arial', 14))
        info.addWidget(label)
        
        self.weight_label = QLabel('Weight: --- kg')
        weight_font = QFont()
        weight_font.setPointSize(24)
        weight_font.setBold(True)
        self.weight_label.setFont(weight_font)
        self.weight_label.setStyleSheet("color: green;")
        info.addWidget(self.weight_label, stretch=1)
        
        self.content_area.addLayout(info, stretch=1)
        
        btn_tare = QPushButton('Tare Scale')
        btn_tare.setFixedHeight(50)
        btn_tare.setStyleSheet("background-color: #FFAA00; color: white;")
        btn_tare.clicked.connect(self._on_tare_scale)
        self.control_buttons.addWidget(btn_tare)
        
        btn_read = QPushButton('Read Weight')
        btn_read.setFixedHeight(50)
        btn_read.setStyleSheet("background-color: #33CC33; color: white;")
        btn_read.clicked.connect(self._on_read_weight)
        self.control_buttons.addWidget(btn_read)
    
    def _on_tare_scale(self):
        """Tare scale."""
        hw = get_hardware()
        hw.weight.tare()
        self.weight_label.setText('Weight: 0.00 kg (Tared)')
    
    def _on_read_weight(self):
        """Read weight."""
        hw = get_hardware()
        weight = hw.weight.read_weight()
        
        if weight and weight > 0:
            self.flow_data['weight_kg'] = weight
            self.weight_label.setText(f'Weight: {weight:.2f} kg')
            
            QTimer.singleShot(2000, self.show_moisture_measurement)
        else:
            QMessageBox.warning(self, 'Error', 'Invalid weight')
    
    def show_moisture_measurement(self):
        """Step 4: Moisture measurement."""
        self._clear_content()
        
        self.title_label.setText('Step 4: Moisture Measurement')
        self.progress.setValue(55)
        
        info = QVBoxLayout()
        
        label = QLabel('Insert moisture probe')
        label.setFont(QFont('Arial', 14))
        info.addWidget(label)
        
        self.moisture_label = QLabel('Moisture: ---%')
        moisture_font = QFont()
        moisture_font.setPointSize(24)
        moisture_font.setBold(True)
        self.moisture_label.setFont(moisture_font)
        self.moisture_label.setStyleSheet("color: green;")
        info.addWidget(self.moisture_label, stretch=1)
        
        self.content_area.addLayout(info, stretch=1)
        
        btn_read = QPushButton('Read Moisture')
        btn_read.setFixedHeight(50)
        btn_read.setStyleSheet("background-color: #33CC33; color: white;")
        btn_read.clicked.connect(self._on_read_moisture)
        self.control_buttons.addWidget(btn_read)
    
    def _on_read_moisture(self):
        """Read moisture."""
        hw = get_hardware()
        readings = hw.moisture.read_moisture()
        
        if readings:
            avg_moisture = readings[-1]
            self.flow_data['moisture_percent'] = avg_moisture
            self.moisture_label.setText(f'Moisture: {avg_moisture:.2f}%')
            
            QTimer.singleShot(2000, self._validate_and_calculate)
        else:
            QMessageBox.warning(self, 'Error', 'Failed to read moisture')
    
    def _validate_and_calculate(self):
        """Step 5: Quality check and payment calculation."""
        crop_type = self.flow_data['crop_type']
        weight_kg = self.flow_data['weight_kg']
        moisture = self.flow_data['moisture_percent']
        
        # Quality check
        accepted, grade, message = self.quality.validate_moisture(crop_type, moisture)
        
        if not accepted:
            QMessageBox.critical(self, 'Quality Rejected', f"Quality Rejected: {message}")
            return
        
        self.flow_data['quality_grade'] = grade
        
        # Capacity check
        capacity_ok, capacity_msg = self.inventory.check_capacity(crop_type, weight_kg)
        if not capacity_ok:
            QMessageBox.critical(self, 'Error', capacity_msg)
            return
        
        # Calculate payment
        amount, breakdown = self.billing.calculate_buying_amount(
            crop_type, weight_kg, grade
        )
        
        self.flow_data['amount'] = amount
        self.flow_data['billing_breakdown'] = breakdown
        
        self.show_summary()

    def show_summary(self):

        self._clear_content()
        self.title_label.setText('Storage Summary')
        self.progress.setValue(85)
    
        widget = QWidget()
        vlayout = QVBoxLayout()
    
        d = self.flow_data
        breakdown = d.get('billing_breakdown', {})
    
    # Title
        title = QLabel('📋 Storage Details')
        title.setFont(QFont('Arial', 14, QFont.Bold))
        vlayout.addWidget(title)
    
        vlayout.addSpacing(10)
    
    # Farmer info
        vlayout.addWidget(QLabel(f"👨‍🌾 Farmer: {self.farmer['name']}"))
        vlayout.addWidget(QLabel(f"📱 Phone: {self.farmer['phone']}"))
    
        vlayout.addSpacing(10)
    
    # Crop info
        vlayout.addWidget(QLabel(f"🌾 Crop: {d['crop_type'].upper()}"))
        vlayout.addWidget(QLabel(f"⚖️ Weight: {d['weight_kg']:.2f} kg"))
        vlayout.addWidget(QLabel(f"💧 Moisture: {d['moisture_percent']:.2f}%"))
        vlayout.addWidget(QLabel(f"📊 Quality: Grade {d['quality_grade']}"))
        vlayout.addWidget(QLabel(f"📍 Stack: {d['stack_location']}"))
        vlayout.addWidget(QLabel(f"📅 Expiry: {d['expiry_date']}"))
    
        vlayout.addSpacing(15)
    
    # Rate breakdown
        rate_title = QLabel('💰 Billing Breakdown')
        rate_title.setFont(QFont('Arial', 12, QFont.Bold))
        vlayout.addWidget(rate_title)
    
    # Storage rate
        rate = breakdown.get('rate_per_kg_per_month', self.app.app_config.get('billing', {}).get('storage_rate_per_kg_per_month', 2.0))
        duration = breakdown.get('duration_months', 1.0)
        base_fee = breakdown.get('base_fee', d.get('storage_fee', 0))
        quality_adj = breakdown.get('quality_adjustment', 0)
    
        rate_label = QLabel(f"   Rate: ₹{rate:.2f} per kg per month")
        rate_label.setStyleSheet("color: #555;")
        vlayout.addWidget(rate_label)
    
        duration_label = QLabel(f"   Duration: {duration:.1f} month(s)")
        duration_label.setStyleSheet("color: #555;")
        vlayout.addWidget(duration_label)
    
        weight_label = QLabel(f"   Weight: {d['weight_kg']:.2f} kg")
        weight_label.setStyleSheet("color: #555;")
        vlayout.addWidget(weight_label)
    
        base_label = QLabel(f"   Base Fee: ₹{rate:.2f} × {d['weight_kg']:.2f} kg × {duration:.1f} mo = ₹{base_fee:.2f}")
        base_label.setStyleSheet("color: #555;")
        vlayout.addWidget(base_label)
    
        if quality_adj != 0:
            adj_text = f"   Quality {'Premium' if quality_adj > 0 else 'Penalty'}: ₹{abs(quality_adj):.2f}"
            if quality_adj > 0:
                adj_text += f" (Grade {d['quality_grade']} +10%)"
            else:
                adj_text += f" (Grade {d['quality_grade']} -5%)"
            adj_label = QLabel(adj_text)
            adj_label.setStyleSheet("color: #555;")
            vlayout.addWidget(adj_label)
    
        vlayout.addSpacing(10)
    
    # Separator line
        line = QLabel('─' * 40)
        line.setStyleSheet("color: #999;")
        vlayout.addWidget(line)
    
    # Total fee
        fee_label = QLabel(f"   TOTAL: ₹{d['storage_fee']:.2f}")
        fee_font = QFont()
        fee_font.setPointSize(20)
        fee_font.setBold(True)
        fee_label.setFont(fee_font)
        fee_label.setStyleSheet("color: green;")
        vlayout.addWidget(fee_label)
    
        vlayout.addStretch(1)
        widget.setLayout(vlayout)
        self.content_area.addWidget(widget, stretch=1)
    
        btn = QPushButton('Proceed to Payment')
        btn.setFixedHeight(60)
        btn.setFont(QFont('Arial', 14, QFont.Bold))
        btn.setStyleSheet("background-color: #33CC33; color: white;")
        btn.clicked.connect(self._show_payment)
        self.control_buttons.addWidget(btn) 


    def _show_payment(self):
        """Show payment screen."""
        self.app.show_screen('payment')
        self.app.screens['payment'].setup_payment(
            amount=self.flow_data['amount'],
            transaction_type='buying',
            flow_data=self.flow_data,
            farmer=self.farmer,
            session=self.session,
            on_complete=self._on_payment_complete
        )
    
    def _on_payment_complete(self, payment_ref):
        """Handle payment completion."""
        # Create batch and store crop
        batch_code = f"BUY-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        stack_location = self.inventory.allocate_stack(
            self.flow_data['crop_type'],
            self.flow_data['weight_kg']
        )
        
        rfid_uid = db.get_available_rfid()
        
        storage_date = date.today()
        expiry_date = self.quality.calculate_expiry_date(
            self.flow_data['crop_type'],
            storage_date
        )
        
        batch_id = db.insert('batches', {
            'batch_code': batch_code,
            'farmer_id': self.farmer['id'],
            'crop_type': self.flow_data['crop_type'],
            'weight_kg': self.flow_data['weight_kg'],
            'moisture_percent': self.flow_data['moisture_percent'],
            'quality_grade': self.flow_data['quality_grade'],
            'rfid_uid': rfid_uid,
            'stack_location': stack_location,
            'storage_date': storage_date.isoformat(),
            'expiry_date': expiry_date,
            'status': 'stored'
        })
        
        # Create transaction
        txn_code = f"BUY-TXN-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        txn_id = db.insert('transactions', {
            'txn_type': 'buying',
            'txn_code': txn_code,
            'farmer_id': self.farmer['id'],
            'batch_id': batch_id,
            'operator_id': self.app.current_user['id'],
            'crop_type': self.flow_data['crop_type'],
            'weight_kg': self.flow_data['weight_kg'],
            'amount': self.flow_data['amount'],
            'payment_status': 'paid',
            'payment_method': 'cash',
            'payment_ref': payment_ref
        })
        
        # Update inventory
        db.update_crop_stock(self.flow_data['crop_type'], self.flow_data['weight_kg'])
        
        # Update stack
        self.inventory.update_stack_weight(stack_location, self.flow_data['weight_kg'])
        
        # Update RFID
        db.update('rfid_tags', {
            'status': 'assigned',
            'assigned_to_batch_id': batch_id
        }, 'uid = ?', (rfid_uid,))
        
        # Write RFID
        hw = get_hardware()
        hw.rfid.write_data(rfid_uid, batch_code)
        
        # Send WhatsApp
        whatsapp = get_whatsapp()
        message = WhatsAppTemplates.format_message(
            'STORAGE_CONFIRMATION',
            self.app.current_language,
            {
                'godown_name': self.app.app_config.get('godown_name', 'Godown'),
                'farmer_name': self.farmer['name'],
                'batch_code': batch_code,
                'crop_type': self.flow_data['crop_type'],
                'weight_kg': self.flow_data['weight_kg'],
                'quality_grade': self.flow_data['quality_grade'],
                'moisture': self.flow_data['moisture_percent'],
                'amount': self.flow_data['amount'],
                'payment_status': 'Paid (Purchase)',
                'expiry_date': expiry_date,
                'rfid_uid': rfid_uid,
                'stack_location': stack_location
            }
        )
        
        whatsapp.enqueue(
            self.farmer['phone'],
            message,
            self.app.current_language,
            template_name='STORAGE_CONFIRMATION',
            priority=10
        )
        
        # Commit session
        self.session.commit()
        
        # Show success
        self.progress.setValue(100)
        QMessageBox.information(self, 'Success', 
            f'Purchase completed successfully!\n\n'
            f'Amount Paid: ₹{self.flow_data["amount"]:.2f}\n'
            f'Batch Code: {batch_code}\n'
            f'WhatsApp notification sent to farmer.')
        
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
        """Go back."""
        if self.session:
            self.session.rollback()
        self.app.show_screen('startup')