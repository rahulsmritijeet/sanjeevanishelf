"""
Storage Flow Screen - PyQt5
With Read Data + Confirm buttons for weight and moisture.
With 5-minute session timer.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QGridLayout, QDialog, QMessageBox,
    QProgressBar, QFrame
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


class StorageScreen(QWidget):
    """Storage flow screen with Read+Confirm for sensors."""
    
    def __init__(self, app):
        super().__init__()
        self.app = app
        
        self.inventory = InventoryManager(app.app_config)
        self.quality = QualityControl()
        self.billing = BillingEngine(app.app_config)
        self.payment_sim = PaymentSimulator()
        
        self.session = None
        self.farmer = None
        self.current_step = 0
        self.flow_data = {}
        
        # Temp sensor readings (not confirmed yet)
        self._temp_weight = None
        self._temp_moisture = None
        self._temp_moisture_readings = None
        
        # Session timer
        self._session_timer = QTimer(self)
        self._session_timer.timeout.connect(self._update_session_timer)
        
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
        title_font.setPointSize(18)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        header_layout.addWidget(self.title_label, stretch=1)
        
        # Timer
        self.timer_label = QLabel('timer 05:00')
        timer_font = QFont()
        timer_font.setPointSize(14)
        timer_font.setBold(True)
        self.timer_label.setFont(timer_font)
        self.timer_label.setStyleSheet("color: green; font-weight: bold;")
        header_layout.addWidget(self.timer_label)
        
        # Cancel button
        btn_cancel = QPushButton('Cancel')
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
        
        self.show_farmer_lookup()
    
    def _update_session_timer(self):
        """Update timer."""
        if self.session:
            time_str = self.session.get_time_display()
            self.timer_label.setText(f"timer {time_str}")
            
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
        """Handle timeout."""
        self._session_timer.stop()
        QMessageBox.critical(self, "Session Timeout",
            "5-minute session expired!\nAll changes rolled back.")
        self.app.show_screen('startup')
    
    def _cancel_session(self):
        """Cancel session."""
        reply = QMessageBox.question(self, 'Cancel',
            'Cancel session? All changes lost.',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self._session_timer.stop()
            if self.session:
                self.session.cancel()
            self.app.show_screen('startup')
    
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
        self.phone_input.setPlaceholderText('9876543210')
        self.content_area.addWidget(self.phone_input)
        
        self.content_area.addStretch(1)
        
        btn_search = QPushButton('Search Farmer')
        btn_search.setFont(QFont('Arial', 12))
        btn_search.setFixedHeight(50)
        btn_search.setStyleSheet("background-color: #33CC33; color: white;")
        btn_search.clicked.connect(self._on_phone_submitted)
        self.control_buttons.addWidget(btn_search)
    
    def _on_phone_submitted(self):
        """Handle phone submission."""
        phone = self.phone_input.text().strip()
        
        if len(phone) != 10:
            QMessageBox.warning(self, 'Error', 'Please enter 10-digit phone number')
            return
        
        farmer = db.get_farmer_by_phone(phone)
        
        if farmer:
            self.farmer = farmer
            self.flow_data['farmer_id'] = farmer['id']
            user_id = self.app.current_user['id']
            self.session = SessionManager(operator_id=user_id, mode='storage')
            self.session.start(farmer_id=farmer['id'])
            self._session_timer.start(1000)
            self.show_rfid_scan()
        else:
            self._show_farmer_registration(phone)
    
    def _show_farmer_registration(self, phone):
        """Show farmer registration."""
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
            self._session_timer.start(1000)
            
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
        
        widget = QWidget()
        vlayout = QVBoxLayout()
        
        vlayout.addWidget(QLabel(f"Farmer: {self.farmer['name']} ({self.farmer['phone']})"))
        
        scan_label = QLabel('Place RFID tag near scanner...')
        scan_label.setFont(QFont('Arial', 16, QFont.Bold))
        scan_label.setStyleSheet("color: green;")
        scan_label.setAlignment(Qt.AlignCenter)
        vlayout.addWidget(scan_label, stretch=1)
        
        widget.setLayout(vlayout)
        self.content_area.addWidget(widget, stretch=1)
        
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
        hw = get_hardware()
        uid = hw.rfid.read_uid(timeout=10)
        if uid:
            self._on_rfid_received(uid)
        else:
            QMessageBox.warning(self, 'Error', 'RFID scan timeout')
    
    def _on_manual_rfid(self):
        uid = db.get_available_rfid()
        if uid:
            self._on_rfid_received(uid)
        else:
            QMessageBox.warning(self, 'Error', 'No available RFID tags')
    
    def _on_rfid_received(self, uid):
        tag = db.fetchone("SELECT * FROM rfid_tags WHERE uid = ?", (uid,))
        if not tag or tag['status'] != 'available':
            QMessageBox.warning(self, 'Error', f'RFID {uid} not available')
            return
        self.flow_data['rfid_uid'] = uid
        logger.info(f"RFID scanned: {uid}")
        self.show_weight_measurement()
    
    def show_weight_measurement(self):
        """Step 3: Weight - READ DATA + CONFIRM."""
        self._clear_content()
        self.title_label.setText('Step 3: Weight Measurement')
        self.progress.setValue(40)
        self._temp_weight = None
        
        widget = QWidget()
        vlayout = QVBoxLayout()
        
        vlayout.addWidget(QLabel('Place crop sacks on the scale'))
        vlayout.addSpacing(10)
        
        # Weight display
        self.weight_label = QLabel('Weight: --- kg')
        wf = QFont()
        wf.setPointSize(28)
        wf.setBold(True)
        self.weight_label.setFont(wf)
        self.weight_label.setStyleSheet("color: #999999;")
        self.weight_label.setAlignment(Qt.AlignCenter)
        vlayout.addWidget(self.weight_label, stretch=1)
        
        # Status label
        self.weight_status = QLabel('Press "Read Data" to measure weight')
        self.weight_status.setFont(QFont('Arial', 11))
        self.weight_status.setStyleSheet("color: #666;")
        self.weight_status.setAlignment(Qt.AlignCenter)
        vlayout.addWidget(self.weight_status)
        
        widget.setLayout(vlayout)
        self.content_area.addWidget(widget, stretch=1)
        
        # Buttons
        btn_tare = QPushButton('Tare Scale')
        btn_tare.setFixedHeight(50)
        btn_tare.setStyleSheet("background-color: #FFAA00; color: white;")
        btn_tare.clicked.connect(self._on_tare_scale)
        self.control_buttons.addWidget(btn_tare)
        
        btn_read = QPushButton('Read Data')
        btn_read.setFixedHeight(50)
        btn_read.setFont(QFont('Arial', 12, QFont.Bold))
        btn_read.setStyleSheet("background-color: #2196F3; color: white;")
        btn_read.clicked.connect(self._on_read_weight)
        self.control_buttons.addWidget(btn_read)
        
        self.btn_confirm_weight = QPushButton('Confirm Weight')
        self.btn_confirm_weight.setFixedHeight(50)
        self.btn_confirm_weight.setFont(QFont('Arial', 12, QFont.Bold))
        self.btn_confirm_weight.setStyleSheet("background-color: #999999; color: white;")
        self.btn_confirm_weight.setEnabled(False)
        self.btn_confirm_weight.clicked.connect(self._on_confirm_weight)
        self.control_buttons.addWidget(self.btn_confirm_weight)
    
    def _on_tare_scale(self):
        """Tare scale."""
        hw = get_hardware()
        hw.weight.tare()
        self.weight_label.setText('Weight: 0.00 kg (Tared)')
        self.weight_label.setStyleSheet("color: #999;")
        self.weight_status.setText('Scale tared. Place sacks and press "Read Data"')
        self._temp_weight = None
        self.btn_confirm_weight.setEnabled(False)
        self.btn_confirm_weight.setStyleSheet("background-color: #999999; color: white;")
    
    def _on_read_weight(self):
        """Read weight from sensor - shows data but doesn't confirm."""
        hw = get_hardware()
        weight = hw.weight.read_weight(samples=5)
        
        if weight and weight > 0:
            self._temp_weight = weight
            self.weight_label.setText(f'Weight: {weight:.2f} kg')
            self.weight_label.setStyleSheet("color: #FF9800;")
            self.weight_status.setText('Reading taken. Press "Read Data" to retry or "Confirm Weight" to accept')
            self.weight_status.setStyleSheet("color: #FF9800; font-weight: bold;")
            
            # Enable confirm button
            self.btn_confirm_weight.setEnabled(True)
            self.btn_confirm_weight.setStyleSheet("background-color: #4CAF50; color: white;")
        else:
            self._temp_weight = None
            self.weight_label.setText('Weight: ERROR')
            self.weight_label.setStyleSheet("color: red;")
            self.weight_status.setText('Reading failed! Press "Read Data" to try again')
            self.weight_status.setStyleSheet("color: red;")
            self.btn_confirm_weight.setEnabled(False)
            self.btn_confirm_weight.setStyleSheet("background-color: #999999; color: white;")
    
    def _on_confirm_weight(self):
        """Confirm weight reading and proceed."""
        if self._temp_weight and self._temp_weight > 0:
            self.flow_data['weight_kg'] = self._temp_weight
            self.weight_label.setStyleSheet("color: green;")
            self.weight_status.setText(f'Weight CONFIRMED: {self._temp_weight:.2f} kg')
            self.weight_status.setStyleSheet("color: green; font-weight: bold;")
            logger.info(f"Weight confirmed: {self._temp_weight:.2f} kg")
            
            # Move to moisture after short delay
            QTimer.singleShot(1000, self.show_moisture_measurement)
        else:
            QMessageBox.warning(self, 'Error', 'No valid weight reading to confirm')
    
    def show_moisture_measurement(self):
        """Step 4: Moisture - READ DATA + CONFIRM."""
        self._clear_content()
        self.title_label.setText('Step 4: Moisture Measurement')
        self.progress.setValue(55)
        self._temp_moisture = None
        self._temp_moisture_readings = None
        
        widget = QWidget()
        vlayout = QVBoxLayout()
        
        vlayout.addWidget(QLabel('Insert moisture probe into crop sample'))
        vlayout.addSpacing(10)
        
        # Moisture display
        self.moisture_label = QLabel('Moisture: --- %')
        mf = QFont()
        mf.setPointSize(28)
        mf.setBold(True)
        self.moisture_label.setFont(mf)
        self.moisture_label.setStyleSheet("color: #999999;")
        self.moisture_label.setAlignment(Qt.AlignCenter)
        vlayout.addWidget(self.moisture_label)
        
        # Individual sensor readings
        self.sensor_readings_label = QLabel('')
        self.sensor_readings_label.setFont(QFont('Arial', 10))
        self.sensor_readings_label.setStyleSheet("color: #666;")
        self.sensor_readings_label.setAlignment(Qt.AlignCenter)
        vlayout.addWidget(self.sensor_readings_label)
        
        vlayout.addStretch(1)
        
        # Status label
        self.moisture_status = QLabel('Press "Read Data" to measure moisture')
        self.moisture_status.setFont(QFont('Arial', 11))
        self.moisture_status.setStyleSheet("color: #666;")
        self.moisture_status.setAlignment(Qt.AlignCenter)
        vlayout.addWidget(self.moisture_status)
        
        widget.setLayout(vlayout)
        self.content_area.addWidget(widget, stretch=1)
        
        # Buttons
        btn_read = QPushButton('Read Data')
        btn_read.setFixedHeight(50)
        btn_read.setFont(QFont('Arial', 12, QFont.Bold))
        btn_read.setStyleSheet("background-color: #2196F3; color: white;")
        btn_read.clicked.connect(self._on_read_moisture)
        self.control_buttons.addWidget(btn_read)
        
        self.btn_confirm_moisture = QPushButton('Confirm Moisture')
        self.btn_confirm_moisture.setFixedHeight(50)
        self.btn_confirm_moisture.setFont(QFont('Arial', 12, QFont.Bold))
        self.btn_confirm_moisture.setStyleSheet("background-color: #999999; color: white;")
        self.btn_confirm_moisture.setEnabled(False)
        self.btn_confirm_moisture.clicked.connect(self._on_confirm_moisture)
        self.control_buttons.addWidget(self.btn_confirm_moisture)
    
    def _on_read_moisture(self):
        """Read moisture from sensors - shows data but doesn't confirm."""
        hw = get_hardware()
        readings = hw.moisture.read_moisture()
        
        if readings and len(readings) >= 5:
            self._temp_moisture = readings[-1]  # Average
            self._temp_moisture_readings = readings[:-1]  # Individual sensors
            
            self.moisture_label.setText(f'Moisture: {readings[-1]:.2f} %')
            self.moisture_label.setStyleSheet("color: #FF9800;")
            
            # Show individual sensor readings
            sensor_text = f'Sensors: S1={readings[0]:.1f}%  S2={readings[1]:.1f}%  S3={readings[2]:.1f}%  S4={readings[3]:.1f}%'
            self.sensor_readings_label.setText(sensor_text)
            self.sensor_readings_label.setStyleSheet("color: #FF9800;")
            
            self.moisture_status.setText('Reading taken. Press "Read Data" to retry or "Confirm Moisture" to accept')
            self.moisture_status.setStyleSheet("color: #FF9800; font-weight: bold;")
            
            # Enable confirm button
            self.btn_confirm_moisture.setEnabled(True)
            self.btn_confirm_moisture.setStyleSheet("background-color: #4CAF50; color: white;")
        else:
            self._temp_moisture = None
            self._temp_moisture_readings = None
            self.moisture_label.setText('Moisture: ERROR')
            self.moisture_label.setStyleSheet("color: red;")
            self.sensor_readings_label.setText('')
            self.moisture_status.setText('Reading failed! Press "Read Data" to try again')
            self.moisture_status.setStyleSheet("color: red;")
            self.btn_confirm_moisture.setEnabled(False)
            self.btn_confirm_moisture.setStyleSheet("background-color: #999999; color: white;")
    
    def _on_confirm_moisture(self):
        """Confirm moisture reading and proceed."""
        if self._temp_moisture is not None:
            self.flow_data['moisture_percent'] = self._temp_moisture
            self.flow_data['moisture_readings'] = self._temp_moisture_readings
            self.moisture_label.setStyleSheet("color: green;")
            self.moisture_status.setText(f'Moisture CONFIRMED: {self._temp_moisture:.2f}%')
            self.moisture_status.setStyleSheet("color: green; font-weight: bold;")
            logger.info(f"Moisture confirmed: {self._temp_moisture:.2f}%")
            
            # Move to crop selection after short delay
            QTimer.singleShot(1000, self.show_crop_selection)
        else:
            QMessageBox.warning(self, 'Error', 'No valid moisture reading to confirm')
    
    def show_crop_selection(self):
        """Step 5: Crop selection."""
        self._clear_content()
        self.title_label.setText('Step 5: Select Crop Type')
        self.progress.setValue(70)
        
        self.content_area.addWidget(QLabel('Select Crop Type:'))
        
        widget = QWidget()
        grid = QGridLayout()
        
        for i, crop in enumerate(['rice', 'wheat', 'maize', 'pulses']):
            btn = QPushButton(crop.upper())
            btn.setFont(QFont('Arial', 12, QFont.Bold))
            btn.setFixedHeight(80)
            btn.setStyleSheet("background-color: #3366FF; color: white;")
            btn.clicked.connect(lambda checked, c=crop: self._on_crop_selected(c))
            grid.addWidget(btn, i // 2, i % 2)
        
        widget.setLayout(grid)
        self.content_area.addWidget(widget, stretch=1)
    
    def _on_crop_selected(self, crop_type):
        self.flow_data['crop_type'] = crop_type
        self._validate_and_calculate()
    
    def _validate_and_calculate(self):
        """Validate quality, capacity, calculate billing."""
        crop = self.flow_data['crop_type']
        weight = self.flow_data['weight_kg']
        moisture = self.flow_data['moisture_percent']
        
        accepted, grade, msg = self.quality.validate_moisture(crop, moisture)
        if not accepted:
            QMessageBox.critical(self, 'Quality Rejected', msg)
            return
        self.flow_data['quality_grade'] = grade
        
        weight_ok, wmsg = self.quality.validate_weight(weight)
        if not weight_ok:
            QMessageBox.critical(self, 'Error', wmsg)
            return
        
        cap_ok, cmsg = self.inventory.check_capacity(crop, weight)
        if not cap_ok:
            QMessageBox.critical(self, 'Error', cmsg)
            return
        
        stack = self.inventory.allocate_stack(crop, weight)
        if not stack:
            QMessageBox.critical(self, 'Error', 'No storage space')
            return
        self.flow_data['stack_location'] = stack
        
        fee, breakdown = self.billing.calculate_storage_fee(weight, 1.0, grade)
        self.flow_data['storage_fee'] = fee
        self.flow_data['billing_breakdown'] = breakdown
        
        sd = date.today()
        ed = self.quality.calculate_expiry_date(crop, sd)
        self.flow_data['storage_date'] = sd.isoformat()
        self.flow_data['expiry_date'] = ed
        
        self.show_summary()
    
    def show_summary(self):
        """Show storage summary with rate breakdown."""
        self._clear_content()
        self.title_label.setText('Storage Summary')
        self.progress.setValue(85)
        
        widget = QWidget()
        vlayout = QVBoxLayout()
        
        d = self.flow_data
        breakdown = d.get('billing_breakdown', {})
        
        title = QLabel('Storage Details')
        title.setFont(QFont('Arial', 14, QFont.Bold))
        vlayout.addWidget(title)
        
        vlayout.addSpacing(10)
        
        vlayout.addWidget(QLabel(f"Farmer: {self.farmer['name']}"))
        vlayout.addWidget(QLabel(f"Phone: {self.farmer['phone']}"))
        vlayout.addSpacing(5)
        vlayout.addWidget(QLabel(f"Crop: {d['crop_type'].upper()}"))
        vlayout.addWidget(QLabel(f"Weight: {d['weight_kg']:.2f} kg"))
        vlayout.addWidget(QLabel(f"Moisture: {d['moisture_percent']:.2f}%"))
        vlayout.addWidget(QLabel(f"Quality: Grade {d['quality_grade']}"))
        vlayout.addWidget(QLabel(f"Stack: {d['stack_location']}"))
        vlayout.addWidget(QLabel(f"Expiry: {d['expiry_date']}"))
        
        vlayout.addSpacing(15)
        
        # Rate breakdown
        rate_frame = QFrame()
        rate_frame.setFrameShape(QFrame.Box)
        rate_frame.setStyleSheet("background-color: #FFF3E0; border: 1px solid #FFB74D; border-radius: 5px;")
        rate_layout = QVBoxLayout()
        
        rate_title = QLabel('Billing Breakdown')
        rate_title.setFont(QFont('Arial', 12, QFont.Bold))
        rate_layout.addWidget(rate_title)
        
        rate = breakdown.get('rate_per_kg_per_month',
            self.app.app_config.get('billing', {}).get('storage_rate_per_kg_per_month', 2.0))
        duration = breakdown.get('duration_months', 1.0)
        base_fee = breakdown.get('base_fee', d.get('storage_fee', 0))
        quality_adj = breakdown.get('quality_adjustment', 0)
        
        rate_layout.addWidget(QLabel(f"   Rate: Rs.{rate:.2f}/kg/month"))
        rate_layout.addWidget(QLabel(f"   Weight: {d['weight_kg']:.2f} kg x {duration:.1f} month"))
        rate_layout.addWidget(QLabel(f"   Base Fee: Rs.{base_fee:.2f}"))
        
        if quality_adj != 0:
            adj_type = "Premium" if quality_adj > 0 else "Penalty"
            ql = QLabel(f"   Quality {adj_type} (Grade {d['quality_grade']}): Rs.{quality_adj:.2f}")
            ql.setStyleSheet("color: green;" if quality_adj > 0 else "color: red;")
            rate_layout.addWidget(ql)
        
        rate_layout.addWidget(QLabel('   ' + '-' * 35))
        
        fee_label = QLabel(f"   TOTAL: Rs.{d['storage_fee']:.2f}")
        fee_font = QFont()
        fee_font.setPointSize(18)
        fee_font.setBold(True)
        fee_label.setFont(fee_font)
        fee_label.setStyleSheet("color: green;")
        rate_layout.addWidget(fee_label)
        
        rate_frame.setLayout(rate_layout)
        vlayout.addWidget(rate_frame)
        
        vlayout.addStretch(1)
        widget.setLayout(vlayout)
        self.content_area.addWidget(widget, stretch=1)
        
        btn = QPushButton(f'Proceed to Payment (Rs.{d["storage_fee"]:.2f})')
        btn.setFixedHeight(60)
        btn.setFont(QFont('Arial', 14, QFont.Bold))
        btn.setStyleSheet("background-color: #33CC33; color: white;")
        btn.clicked.connect(self._show_payment)
        self.control_buttons.addWidget(btn)
    
    def _show_payment(self):
        """Go to payment screen."""
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
        self._session_timer.stop()
        
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
        
        txn_code = f"TXN-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        db.insert('transactions', {
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
        
        db.update('rfid_tags', {
            'status': 'assigned',
            'assigned_to_batch_id': batch_id
        }, 'uid = ?', (self.flow_data['rfid_uid'],))
        
        db.update_crop_stock(self.flow_data['crop_type'], self.flow_data['weight_kg'])
        self.inventory.update_stack_weight(self.flow_data['stack_location'], self.flow_data['weight_kg'])
        
        hw = get_hardware()
        hw.rfid.write_data(self.flow_data['rfid_uid'], batch_code)
        
        try:
            sms = get_whatsapp()
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
            sms.enqueue(self.farmer['phone'], message, self.app.current_language)
        except Exception as e:
            logger.error(f"SMS failed: {e}")
        
        self.session.commit()
        
        self.progress.setValue(100)
        QMessageBox.information(self, 'Success',
            f'Storage completed!\n\n'
            f'Batch: {batch_code}\n'
            f'Fee: Rs.{self.flow_data["storage_fee"]:.2f}\n\n'
            f'SMS sent to farmer.')
        
        self.app.show_screen('startup')
    
    def _clear_content(self):
        """Clear content area."""
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
        """Go back."""
        self._session_timer.stop()
        if self.session:
            self.session.cancel()
        self.app.show_screen('startup')