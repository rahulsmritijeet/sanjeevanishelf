"""
Buying Flow Screen - PyQt5
Godown purchases crop directly from farmer.
With 5-minute session timer, rate breakdown.
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


class BuyingScreen(QWidget):
    """Buying flow screen with timer and rate breakdown."""
    
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
        
        # Session timer
        self._session_timer = QTimer(self)
        self._session_timer.timeout.connect(self._update_session_timer)
        
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
        
        # Show farmer lookup
        self.show_farmer_lookup()
    
    def _update_session_timer(self):
        """Update timer every second."""
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
        
        btn_submit = QPushButton('Search Farmer')
        btn_submit.setFont(QFont('Arial', 12))
        btn_submit.setFixedHeight(50)
        btn_submit.setStyleSheet("background-color: #33CC33; color: white;")
        btn_submit.clicked.connect(self._on_phone_submitted)
        self.control_buttons.addWidget(btn_submit)
    
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
            self.session = SessionManager(operator_id=user_id, mode='buying')
            self.session.start(farmer_id=farmer['id'])
            self._session_timer.start(1000)
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
            self._session_timer.start(1000)
            
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
        
        widget = QWidget()
        grid = QGridLayout()
        
        crops = ['rice', 'wheat', 'maize', 'pulses']
        
        for i, crop in enumerate(crops):
            btn = QPushButton(crop.upper())
            btn.setFont(QFont('Arial', 12, QFont.Bold))
            btn.setFixedHeight(80)
            btn.setStyleSheet("background-color: #3366FF; color: white;")
            btn.clicked.connect(lambda checked, c=crop: self._on_crop_selected(c))
            grid.addWidget(btn, i // 2, i % 2)
        
        widget.setLayout(grid)
        self.content_area.addWidget(widget, stretch=1)
    
    def _on_crop_selected(self, crop_type):
        """Handle crop selection."""
        self.flow_data['crop_type'] = crop_type
        self.show_weight_measurement()
    
    def show_weight_measurement(self):
        """Step 3: Weight measurement."""
        self._clear_content()
        
        self.title_label.setText('Step 3: Weight Measurement')
        self.progress.setValue(40)
        
        widget = QWidget()
        vlayout = QVBoxLayout()
        
        vlayout.addWidget(QLabel('Place crop on the scale'))
        
        self.weight_label = QLabel('Weight: --- kg')
        wf = QFont()
        wf.setPointSize(24)
        wf.setBold(True)
        self.weight_label.setFont(wf)
        self.weight_label.setStyleSheet("color: green;")
        self.weight_label.setAlignment(Qt.AlignCenter)
        vlayout.addWidget(self.weight_label, stretch=1)
        
        widget.setLayout(vlayout)
        self.content_area.addWidget(widget, stretch=1)
        
        btn_tare = QPushButton('Tare Scale')
        btn_tare.setFixedHeight(50)
        btn_tare.setStyleSheet("background-color: #FFAA00; color: white;")
        btn_tare.clicked.connect(lambda: self.weight_label.setText('Weight: 0.00 kg (Tared)'))
        self.control_buttons.addWidget(btn_tare)
        
        btn_read = QPushButton('Read Weight')
        btn_read.setFixedHeight(50)
        btn_read.setStyleSheet("background-color: #33CC33; color: white;")
        btn_read.clicked.connect(self._on_read_weight)
        self.control_buttons.addWidget(btn_read)
    
    def _on_read_weight(self):
        """Read weight."""
        hw = get_hardware()
        weight = hw.weight.read_weight()
        
        if weight and weight > 0:
            self.flow_data['weight_kg'] = weight
            self.weight_label.setText(f'Weight: {weight:.2f} kg')
            QTimer.singleShot(1500, self.show_moisture_measurement)
        else:
            QMessageBox.warning(self, 'Error', 'Invalid weight')
    
    def show_moisture_measurement(self):
        """Step 4: Moisture measurement."""
        self._clear_content()
        
        self.title_label.setText('Step 4: Moisture Measurement')
        self.progress.setValue(55)
        
        widget = QWidget()
        vlayout = QVBoxLayout()
        
        vlayout.addWidget(QLabel('Insert moisture probe'))
        
        self.moisture_label = QLabel('Moisture: ---%')
        mf = QFont()
        mf.setPointSize(24)
        mf.setBold(True)
        self.moisture_label.setFont(mf)
        self.moisture_label.setStyleSheet("color: green;")
        self.moisture_label.setAlignment(Qt.AlignCenter)
        vlayout.addWidget(self.moisture_label, stretch=1)
        
        widget.setLayout(vlayout)
        self.content_area.addWidget(widget, stretch=1)
        
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
            avg = readings[-1]
            self.flow_data['moisture_percent'] = avg
            self.moisture_label.setText(f'Moisture: {avg:.2f}%')
            QTimer.singleShot(1500, self._validate_and_calculate)
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
        
        # Allocate stack BEFORE summary
        stack_location = self.inventory.allocate_stack(crop_type, weight_kg)
        if not stack_location:
            QMessageBox.critical(self, 'Error', 'No available storage space')
            return
        self.flow_data['stack_location'] = stack_location
        
        # Calculate payment
        amount, breakdown = self.billing.calculate_buying_amount(
            crop_type, weight_kg, grade
        )
        
        self.flow_data['amount'] = amount
        self.flow_data['billing_breakdown'] = breakdown
        
        # Calculate dates
        storage_date = date.today()
        expiry_date = self.quality.calculate_expiry_date(crop_type, storage_date)
        self.flow_data['storage_date'] = storage_date.isoformat()
        self.flow_data['expiry_date'] = expiry_date
        
        self.show_summary()
    
    def show_summary(self):
        """Show purchase summary with rate breakdown."""
        self._clear_content()
        
        self.title_label.setText('Purchase Summary')
        self.progress.setValue(75)
        
        widget = QWidget()
        summary = QVBoxLayout()
        
        data = self.flow_data
        breakdown = data.get('billing_breakdown', {})
        
        # Title
        title = QLabel('Purchase Details')
        title.setFont(QFont('Arial', 14, QFont.Bold))
        summary.addWidget(title)
        
        summary.addSpacing(10)
        
        # Farmer info
        summary.addWidget(QLabel(f"Farmer: {self.farmer['name']}"))
        summary.addWidget(QLabel(f"Phone: {self.farmer['phone']}"))
        
        summary.addSpacing(10)
        
        # Crop info
        summary.addWidget(QLabel(f"Crop: {data['crop_type'].upper()}"))
        summary.addWidget(QLabel(f"Weight: {data['weight_kg']:.2f} kg"))
        summary.addWidget(QLabel(f"Moisture: {data['moisture_percent']:.2f}%"))
        summary.addWidget(QLabel(f"Quality: Grade {data['quality_grade']}"))
        summary.addWidget(QLabel(f"Stack: {data.get('stack_location', 'Pending')}"))
        summary.addWidget(QLabel(f"Expiry: {data.get('expiry_date', 'Pending')}"))
        
        summary.addSpacing(15)
        
        # Rate breakdown frame
        rate_frame = QFrame()
        rate_frame.setFrameShape(QFrame.Box)
        rate_frame.setStyleSheet("background-color: #FFF3E0; border: 1px solid #FFB74D; border-radius: 5px;")
        rate_layout = QVBoxLayout()
        
        rate_title = QLabel('Payment Breakdown')
        rate_title.setFont(QFont('Arial', 12, QFont.Bold))
        rate_layout.addWidget(rate_title)
        
        # Market rate vs MSP
        market_rate = breakdown.get('market_rate', 0)
        msp_rate = breakdown.get('msp_rate', 0)
        applied_rate = breakdown.get('applied_rate', 0)
        quality_multiplier = breakdown.get('quality_multiplier', 1.0)
        
        rate_layout.addWidget(QLabel(f"   Market Rate: Rs.{market_rate:.2f}/kg"))
        rate_layout.addWidget(QLabel(f"   MSP Rate: Rs.{msp_rate:.2f}/kg"))
        
        # Show which rate is applied
        if applied_rate >= msp_rate:
            rate_source = "(Higher rate applied)"
        else:
            rate_source = "(MSP applied)"
        
        applied_label = QLabel(f"   Applied Rate: Rs.{applied_rate:.2f}/kg {rate_source}")
        applied_label.setStyleSheet("color: #0066CC; font-weight: bold;")
        rate_layout.addWidget(applied_label)
        
        # Base calculation
        base_amount = data['weight_kg'] * applied_rate
        rate_layout.addWidget(QLabel(f"   Base: Rs.{applied_rate:.2f} x {data['weight_kg']:.2f} kg = Rs.{base_amount:.2f}"))
        
        # Quality adjustment
        if quality_multiplier != 1.0:
            quality_percent = (quality_multiplier - 1.0) * 100
            prefix = "+" if quality_percent > 0 else ""
            quality_text = f"   Quality {'Premium' if quality_percent > 0 else 'Penalty'}: {prefix}{quality_percent:.0f}% (Grade {data['quality_grade']})"
            quality_label = QLabel(quality_text)
            if quality_percent > 0:
                quality_label.setStyleSheet("color: green;")
            else:
                quality_label.setStyleSheet("color: red;")
            rate_layout.addWidget(quality_label)
            
            adjusted = base_amount * quality_multiplier
            rate_layout.addWidget(QLabel(f"   After Quality: Rs.{adjusted:.2f}"))
        
        # Separator
        rate_layout.addWidget(QLabel('   ' + '-' * 35))
        
        # Total
        total_label = QLabel(f"   TOTAL TO PAY FARMER: Rs.{data['amount']:.2f}")
        total_font = QFont()
        total_font.setPointSize(16)
        total_font.setBold(True)
        total_label.setFont(total_font)
        total_label.setStyleSheet("color: #2E7D32;")
        rate_layout.addWidget(total_label)
        
        rate_frame.setLayout(rate_layout)
        summary.addWidget(rate_frame)
        
        summary.addStretch(1)
        
        widget.setLayout(summary)
        self.content_area.addWidget(widget, stretch=1)
        
        # Proceed button
        btn_payment = QPushButton(f'Proceed to Payment (Rs.{data["amount"]:.2f})')
        btn_payment.setFixedHeight(60)
        btn_payment.setFont(QFont('Arial', 14, QFont.Bold))
        btn_payment.setStyleSheet("background-color: #33CC33; color: white;")
        btn_payment.clicked.connect(self._show_payment)
        self.control_buttons.addWidget(btn_payment)
    
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
        self._session_timer.stop()
        
        # Create batch
        batch_code = f"BUY-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        rfid_uid = db.get_available_rfid()
        
        batch_id = db.insert('batches', {
            'batch_code': batch_code,
            'farmer_id': self.farmer['id'],
            'crop_type': self.flow_data['crop_type'],
            'weight_kg': self.flow_data['weight_kg'],
            'moisture_percent': self.flow_data['moisture_percent'],
            'quality_grade': self.flow_data['quality_grade'],
            'rfid_uid': rfid_uid,
            'stack_location': self.flow_data['stack_location'],
            'storage_date': self.flow_data['storage_date'],
            'expiry_date': self.flow_data['expiry_date'],
            'status': 'stored'
        })
        
        # Create transaction
        txn_code = f"BUY-TXN-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        db.insert('transactions', {
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
        self.inventory.update_stack_weight(
            self.flow_data['stack_location'],
            self.flow_data['weight_kg']
        )
        
        # Update RFID
        if rfid_uid:
            db.update('rfid_tags', {
                'status': 'assigned',
                'assigned_to_batch_id': batch_id
            }, 'uid = ?', (rfid_uid,))
            
            # Write RFID
            hw = get_hardware()
            hw.rfid.write_data(rfid_uid, batch_code)
        
        # Send SMS notification
        try:
            sms = get_whatsapp()
            breakdown = self.flow_data.get('billing_breakdown', {})
            
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
                    'expiry_date': self.flow_data['expiry_date'],
                    'rfid_uid': rfid_uid or 'N/A',
                    'stack_location': self.flow_data['stack_location']
                }
            )
            
            sms.enqueue(
                self.farmer['phone'],
                message,
                self.app.current_language,
                template_name='STORAGE_CONFIRMATION',
                priority=10
            )
        except Exception as e:
            logger.error(f"SMS notification failed: {e}")
        
        # Commit session
        self.session.commit()
        
        # Show success
        self.progress.setValue(100)
        breakdown = self.flow_data.get('billing_breakdown', {})
        
        QMessageBox.information(self, 'Purchase Complete!',
            f'Purchase completed successfully!\n\n'
            f'Batch: {batch_code}\n'
            f'Crop: {self.flow_data["crop_type"].upper()}\n'
            f'Weight: {self.flow_data["weight_kg"]:.2f} kg\n'
            f'Rate: Rs.{breakdown.get("applied_rate", 0):.2f}/kg\n'
            f'Amount Paid: Rs.{self.flow_data["amount"]:.2f}\n\n'
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