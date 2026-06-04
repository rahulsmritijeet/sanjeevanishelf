"""
Storage Screen - PyQt5
Complete storage workflow with hardware integration.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QGridLayout, QDialog, QMessageBox,
    QProgressBar, QSpinBox, QDoubleSpinBox
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
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


class StorageScreen(QWidget):
    """Storage flow screen."""
    
    def __init__(self, app):
        super().__init__()
        self.app = app
        
        # Initialize managers
        self.inventory = InventoryManager(app.app_config)
        self.quality = QualityControl()
        self.billing = BillingEngine(app.app_config)
        self.payment_sim = PaymentSimulator()
        
        # Session state
        self.session = None
        self.farmer = None
        self.current_step = 0
        self.flow_data = {}
        
        self._build_ui()
    
    def _build_ui(self):
        """Build storage UI."""
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Header
        header_layout = QHBoxLayout()
        
        self.title_label = QLabel('STORAGE FLOW')
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
        
        # Show farmer lookup screen
        self.show_farmer_lookup()
    
    def show_farmer_lookup(self):
        """Step 1: Farmer lookup."""
        self._clear_content()
        
        self.title_label.setText('Step 1: Farmer Lookup')
        self.progress.setValue(10)
        
        # Phone input
        label = QLabel('Enter Farmer Phone Number (10 digits):')
        label.setFont(QFont('Arial', 14))
        self.content_area.addWidget(label)
        
        self.phone_input = QLineEdit()
        self.phone_input.setFont(QFont('Arial', 16))
        self.phone_input.setFixedHeight(50)
        self.phone_input.setMaxLength(10)
        self.content_area.addWidget(self.phone_input)
        
        # Button
        btn_search = QPushButton('Search Farmer')
        btn_search.setFont(QFont('Arial', 12))
        btn_search.setFixedHeight(50)
        btn_search.setStyleSheet("background-color: #33CC33; color: white;")
        btn_search.clicked.connect(self._on_phone_submitted)
        self.control_buttons.addWidget(btn_search)
    
    def _on_phone_submitted(self):
        """Handle phone submission."""
        phone = self.phone_input.text()
        
        if len(phone) != 10:
            QMessageBox.warning(self, 'Error', 'Please enter 10-digit phone number')
            return
        
        # Search farmer
        farmer = db.get_farmer_by_phone(phone)
        
        if farmer:
            self.farmer = farmer
            self.flow_data['farmer_id'] = farmer['id']
            user_id = self.app.current_user['id']
            self.session = SessionManager(operator_id=user_id, mode='storage')
            self.session.start(farmer_id=farmer['id'])
            self.show_rfid_scan()
        else:
            # Show registration dialog
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
            self.session = SessionManager(operator_id=user_id, mode='storage')
            self.session.start(farmer_id=farmer_id)
            
            dialog.accept()
            self.show_rfid_scan()
        
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
    
    def show_rfid_scan(self):
        """Step 2: RFID scan."""
        self._clear_content()
        
        self.title_label.setText('Step 2: RFID Scan')
        self.progress.setValue(25)
        
        info = QVBoxLayout()
        
        farmer_label = QLabel(f"Farmer: {self.farmer['name']} ({self.farmer['phone']})")
        farmer_label.setFont(QFont('Arial', 12))
        info.addWidget(farmer_label)
        
        scan_label = QLabel('Place RFID tag near scanner...')
        scan_label.setFont(QFont('Arial', 16, QFont.Bold))
        scan_label.setStyleSheet("color: green;")
        info.addWidget(scan_label, stretch=1)
        
        self.content_area.addLayout(info, stretch=1)
        
        # Buttons
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
        """Manual RFID entry."""
        uid = db.get_available_rfid()
        if uid:
            self._on_rfid_received(uid)
        else:
            QMessageBox.warning(self, 'Error', 'No available RFID tags')
    
    def _on_rfid_received(self, uid):
        """Handle RFID scan result."""
        tag = db.fetchone("SELECT * FROM rfid_tags WHERE uid = ?", (uid,))
        
        if not tag or tag['status'] != 'available':
            QMessageBox.warning(self, 'Error', f'RFID {uid} is not available')
            return
        
        self.flow_data['rfid_uid'] = uid
        logger.info(f"RFID scanned: {uid}")
        
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
        
        # Buttons
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
        success = hw.weight.tare()
        
        if success:
            self.weight_label.setText('Weight: 0.00 kg (Tared)')
        else:
            QMessageBox.warning(self, 'Error', 'Failed to tare scale')
    
    def _on_read_weight(self):
        """Read weight."""
        hw = get_hardware()
        weight = hw.weight.read_weight(samples=5)
        
        if weight and weight > 0:
            self.flow_data['weight_kg'] = weight
            self.weight_label.setText(f'Weight: {weight:.2f} kg')
            
            # Auto-advance
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(2000, self.show_moisture_measurement)
        else:
            QMessageBox.warning(self, 'Error', 'Invalid weight reading')
    
    def show_moisture_measurement(self):
        """Step 4: Moisture measurement."""
        self._clear_content()
        
        self.title_label.setText('Step 4: Moisture Measurement')
        self.progress.setValue(55)
        
        info = QVBoxLayout()
        
        label = QLabel('Insert moisture probe into crop')
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
            
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(2000, self.show_crop_selection)
        else:
            QMessageBox.warning(self, 'Error', 'Failed to read moisture')
    
    def show_crop_selection(self):
        """Step 5: Crop selection."""
        self._clear_content()
        
        self.title_label.setText('Step 5: Select Crop Type')
        self.progress.setValue(70)
        
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
        
        logger.info(f"Crop selected: {crop_type}")
        
        # Validate and calculate
        self._validate_and_calculate()
    
    def _validate_and_calculate(self):
        """Validate and calculate billing."""
        crop_type = self.flow_data['crop_type']
        weight_kg = self.flow_data['weight_kg']
        moisture = self.flow_data['moisture_percent']
        
        # Quality check
        accepted, grade, message = self.quality.validate_moisture(crop_type, moisture)
        
        if not accepted:
            QMessageBox.critical(self, 'Quality Rejected', f"Quality Rejected: {message}")
            return
        
        self.flow_data['quality_grade'] = grade
        
        # Weight validation
        weight_ok, weight_msg = self.quality.validate_weight(weight_kg)
        if not weight_ok:
            QMessageBox.critical(self, 'Error', weight_msg)
            return
        
        # Capacity check
        capacity_ok, capacity_msg = self.inventory.check_capacity(crop_type, weight_kg)
        if not capacity_ok:
            QMessageBox.critical(self, 'Error', capacity_msg)
            return
        
        # Allocate stack
        stack_location = self.inventory.allocate_stack(crop_type, weight_kg)
        if not stack_location:
            QMessageBox.critical(self, 'Error', 'No available storage space')
            return
        
        self.flow_data['stack_location'] = stack_location
        
        # Calculate billing
        storage_fee, billing_breakdown = self.billing.calculate_storage_fee(
            weight_kg, duration_months=1.0, quality_grade=grade
        )
        
        self.flow_data['storage_fee'] = storage_fee
        self.flow_data['billing_breakdown'] = billing_breakdown
        
        # Calculate expiry date
        storage_date = date.today()
        expiry_date = self.quality.calculate_expiry_date(crop_type, storage_date)
        self.flow_data['storage_date'] = storage_date.isoformat()
        self.flow_data['expiry_date'] = expiry_date
        
        # Show summary
        self.show_summary()
    
    def show_summary(self):
        """Show storage summary."""
        self._clear_content()
        
        self.title_label.setText('Storage Summary')
        self.progress.setValue(85)
        
        summary = QVBoxLayout()
        
        data = self.flow_data
        
        summary.addWidget(QLabel('[Storage Details]'))
        summary.addWidget(QLabel(f"Farmer: {self.farmer['name']}"))
        summary.addWidget(QLabel(f"Crop: {data['crop_type'].upper()}"))
        summary.addWidget(QLabel(f"Weight: {data['weight_kg']:.2f} kg"))
        summary.addWidget(QLabel(f"Quality: Grade {data['quality_grade']}"))
        summary.addWidget(QLabel(f"Stack: {data['stack_location']}"))
        summary.addWidget(QLabel(f"Expiry: {data['expiry_date']}"))
        
        summary.addSpacing(20)
        
        amount_label = QLabel(f"Storage Fee: ₹{data['storage_fee']:.2f}")
        amount_font = QFont()
        amount_font.setPointSize(18)
        amount_font.setBold(True)
        amount_label.setFont(amount_font)
        amount_label.setStyleSheet("color: green;")
        summary.addWidget(amount_label)
        
        self.content_area.addLayout(summary, stretch=1)
        
        btn_payment = QPushButton('Proceed to Payment')
        btn_payment.setFixedHeight(60)
        btn_payment.setFont(QFont('Arial', 14, QFont.Bold))
        btn_payment.setStyleSheet("background-color: #33CC33; color: white;")
        btn_payment.clicked.connect(self._show_payment)
        self.control_buttons.addWidget(btn_payment)
    
    def _show_payment(self):
        """Show payment screen."""
        self.app.show_screen('payment')
        self.app.screens['payment'].setup_payment(
            amount=self.flow_data['storage_fee'],
            transaction_type='storage',
            flow_data=self.flow_data,
            farmer=self.farmer,
            session=self.session,
            on_complete=self._on_payment_complete
        )
    
    def _on_payment_complete(self, payment_ref):
        """Handle payment completion."""
        # Create batch
        batch_code = f"BATCH-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        batch_id = db.insert('batches', {
            'batch_code': batch_code,
            'farmer_id': self.farmer['id'],
            'crop_type': self.flow_data['crop_type'],
            'weight_kg': self.flow_data['weight_kg'],
            'moisture_percent': self.flow_data['moisture_percent'],
            'quality_grade': self.flow_data['quality_grade'],
            'rfid_uid': self.flow_data['rfid_uid'],
            'stack_location': self.flow_data['stack_location'],
            'storage_date': self.flow_data['storage_date'],
            'expiry_date': self.flow_data['expiry_date'],
            'status': 'stored'
        })
        
        # Create transaction
        txn_code = f"TXN-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        txn_id = db.insert('transactions', {
            'txn_type': 'storage',
            'txn_code': txn_code,
            'farmer_id': self.farmer['id'],
            'batch_id': batch_id,
            'operator_id': self.app.current_user['id'],
            'crop_type': self.flow_data['crop_type'],
            'weight_kg': self.flow_data['weight_kg'],
            'amount': self.flow_data['storage_fee'],
            'payment_status': 'paid',
            'payment_method': 'simulation',
            'payment_ref': payment_ref
        })
        
        # Update RFID
        db.update('rfid_tags', {
            'status': 'assigned',
            'assigned_to_batch_id': batch_id
        }, 'uid = ?', (self.flow_data['rfid_uid'],))
        
        # Update inventory
        db.update_crop_stock(self.flow_data['crop_type'], self.flow_data['weight_kg'])
        
        # Update stack
        self.inventory.update_stack_weight(self.flow_data['stack_location'], self.flow_data['weight_kg'])
        
        # Write RFID
        hw = get_hardware()
        hw.rfid.write_data(self.flow_data['rfid_uid'], batch_code)
        
        # Send WhatsApp notification
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
                'amount': self.flow_data['storage_fee'],
                'payment_status': 'Paid',
                'expiry_date': self.flow_data['expiry_date'],
                'rfid_uid': self.flow_data['rfid_uid'],
                'stack_location': self.flow_data['stack_location']
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
        
        # Show receipt
        self.progress.setValue(100)
        QMessageBox.information(self, 'Success', 'Storage completed successfully!\n\nWhatsApp notification sent to farmer.')
        
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
                while layout.count():
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