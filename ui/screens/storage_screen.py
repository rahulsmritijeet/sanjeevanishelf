"""
Storage Flow Screen
Complete storage workflow with hardware integration.
"""

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.spinner import Spinner
from kivy.uix.popup import Popup
from kivy.uix.progressbar import ProgressBar
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


class StorageScreen(Screen):
    """Storage flow screen."""
    
    def __init__(self, app_instance, **kwargs):
        super().__init__(**kwargs)
        self.app = app_instance
        self.name = 'storage'
        
        # Initialize managers
        self.inventory = InventoryManager(app_instance.config)
        self.quality = QualityControl()
        self.billing = BillingEngine(app_instance.config)
        self.payment_sim = PaymentSimulator()
        
        # Session state
        self.session = None
        self.farmer = None
        self.current_step = 0
        self.flow_data = {}
        
        self._build_ui()
    
    def _build_ui(self):
        """Build storage UI."""
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Header
        header = BoxLayout(size_hint_y=0.1, spacing=10)
        
        self.title_label = Label(
            text='[b]STORAGE FLOW[/b]',
            markup=True,
            font_size='28sp'
        )
        header.add_widget(self.title_label)
        
        btn_back = Button(
            text='← Back',
            font_size='20sp',
            size_hint_x=0.2,
            background_color=(0.8, 0.2, 0.2, 1)
        )
        btn_back.bind(on_press=self._on_back)
        header.add_widget(btn_back)
        
        layout.add_widget(header)
        
        # Progress bar
        self.progress = ProgressBar(max=100, size_hint_y=0.05)
        layout.add_widget(self.progress)
        
        # Main content area
        self.content_area = BoxLayout(orientation='vertical', size_hint_y=0.7, padding=20, spacing=15)
        layout.add_widget(self.content_area)
        
        # Control buttons
        self.control_buttons = BoxLayout(size_hint_y=0.15, spacing=10)
        layout.add_widget(self.control_buttons)
        
        self.add_widget(layout)
        
        # Start with farmer lookup
        self._show_farmer_lookup()
    
    def on_enter(self):
        """Called when screen is displayed."""
        # Reset state
        self.current_step = 0
        self.flow_data = {}
        
        # Create new session
        user_id = self.app.current_user['id']
        self.session = SessionManager(operator_id=user_id, mode='storage')
        
        self._show_farmer_lookup()
    
    def _show_farmer_lookup(self):
        """Step 1: Farmer lookup/registration."""
        self.content_area.clear_widgets()
        self.control_buttons.clear_widgets()
        
        self.title_label.text = '[b]Step 1: Farmer Lookup[/b]'
        self.progress.value = 10
        
        # Phone input
        from ui.components.numpad import NumPad
        
        label = Label(
            text='Enter Farmer Phone Number:',
            font_size='24sp',
            size_hint_y=0.2
        )
        self.content_area.add_widget(label)
        
        self.phone_numpad = NumPad(max_length=10, allow_decimal=False)
        self.phone_numpad.on_submit = self._on_phone_submitted
        self.content_area.add_widget(self.phone_numpad)
        
        # Control button
        btn_submit = Button(
            text='Search Farmer',
            font_size='22sp',
            background_color=(0.2, 0.6, 0.2, 1)
        )
        btn_submit.bind(on_press=lambda x: self._on_phone_submitted(self.phone_numpad.get_value()))
        self.control_buttons.add_widget(btn_submit)
    
    def _on_phone_submitted(self, phone):
        """Handle phone number submission."""
        if len(phone) != 10:
            self._show_error("Please enter 10-digit phone number")
            return
        
        # Search farmer
        farmer = db.get_farmer_by_phone(phone)
        
        if farmer:
            self.farmer = farmer
            self.flow_data['farmer_id'] = farmer['id']
            self.session.start(farmer_id=farmer['id'])
            self._show_rfid_scan()
        else:
            # Show registration popup
            self._show_farmer_registration(phone)
    
    def _show_farmer_registration(self, phone):
        """Show farmer registration form."""
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        content.add_widget(Label(
            text='Farmer not found. Register new farmer:',
            font_size='20sp',
            size_hint_y=0.15
        ))
        
        form = GridLayout(cols=2, spacing=10, size_hint_y=0.6)
        
        form.add_widget(Label(text='Phone:', font_size='18sp'))
        phone_input = TextInput(text=phone, readonly=True, font_size='18sp')
        form.add_widget(phone_input)
        
        form.add_widget(Label(text='Name:', font_size='18sp'))
        name_input = TextInput(multiline=False, font_size='18sp')
        form.add_widget(name_input)
        
        form.add_widget(Label(text='Village:', font_size='18sp'))
        village_input = TextInput(multiline=False, font_size='18sp')
        form.add_widget(village_input)
        
        content.add_widget(form)
        
        btn_layout = BoxLayout(size_hint_y=0.25, spacing=10)
        
        popup = Popup(
            title='Register Farmer',
            content=content,
            size_hint=(0.7, 0.6),
            auto_dismiss=False
        )
        
        def on_register(*args):
            name = name_input.text.strip()
            village = village_input.text.strip()
            
            if not name:
                self._show_error("Name is required")
                return
            
            # Register farmer
            farmer_id = db.insert('farmers', {
                'phone': phone,
                'name': name,
                'village': village
            })
            
            self.farmer = db.get_farmer_by_phone(phone)
            self.flow_data['farmer_id'] = farmer_id
            self.session.start(farmer_id=farmer_id)
            
            popup.dismiss()
            self._show_rfid_scan()
        
        btn_register = Button(text='Register', font_size='20sp', background_color=(0.2, 0.6, 0.2, 1))
        btn_register.bind(on_press=on_register)
        btn_layout.add_widget(btn_register)
        
        btn_cancel = Button(text='Cancel', font_size='20sp')
        btn_cancel.bind(on_press=popup.dismiss)
        btn_layout.add_widget(btn_cancel)
        
        content.add_widget(btn_layout)
        popup.open()
    
    def _show_rfid_scan(self):
        """Step 2: RFID tag scan."""
        self.content_area.clear_widgets()
        self.control_buttons.clear_widgets()
        
        self.title_label.text = '[b]Step 2: RFID Tag Scan[/b]'
        self.progress.value = 25
        
        info = BoxLayout(orientation='vertical', spacing=10)
        
        info.add_widget(Label(
            text=f"Farmer: {self.farmer['name']} ({self.farmer['phone']})",
            font_size='20sp',
            size_hint_y=0.2
        ))
        
        info.add_widget(Label(
            text='[b]Place RFID tag near scanner...[/b]',
            markup=True,
            font_size='28sp',
            color=(0, 1, 0, 1),
            size_hint_y=0.5
        ))
        
        self.content_area.add_widget(info)
        
        # Control buttons
        btn_scan = Button(
            text='Start Scan',
            font_size='22sp',
            background_color=(0.2, 0.6, 0.2, 1)
        )
        btn_scan.bind(on_press=self._on_rfid_scan)
        self.control_buttons.add_widget(btn_scan)
        
        btn_manual = Button(
            text='Manual Entry (Sim)',
            font_size='22sp',
            background_color=(0.6, 0.6, 0.2, 1)
        )
        btn_manual.bind(on_press=self._on_manual_rfid)
        self.control_buttons.add_widget(btn_manual)
    
    def _on_rfid_scan(self, *args):
        """Perform RFID scan."""
        hw = get_hardware()
        
        # Show scanning popup
        popup_content = BoxLayout(orientation='vertical', padding=20, spacing=10)
        popup_content.add_widget(Label(text='Scanning RFID...', font_size='24sp'))
        
        progress = ProgressBar(max=100)
        popup_content.add_widget(progress)
        
        popup = Popup(
            title='RFID Scan',
            content=popup_content,
            size_hint=(0.5, 0.3),
            auto_dismiss=False
        )
        popup.open()
        
        # Scan in background (in real app, use threading)
        import threading
        
        def scan_thread():
            uid = hw.rfid.read_uid(timeout=10)
            
            # Close popup on main thread
            from kivy.clock import Clock
            Clock.schedule_once(lambda dt: popup.dismiss(), 0)
            
            if uid:
                Clock.schedule_once(lambda dt: self._on_rfid_received(uid), 0)
            else:
                Clock.schedule_once(lambda dt: self._show_error("RFID scan timeout"), 0)
        
        thread = threading.Thread(target=scan_thread, daemon=True)
        thread.start()
    
    def _on_manual_rfid(self, *args):
        """Manual RFID entry (simulation)."""
        # Get available RFID
        uid = db.get_available_rfid()
        if uid:
            self._on_rfid_received(uid)
        else:
            self._show_error("No available RFID tags")
    
    def _on_rfid_received(self, uid):
        """Handle RFID scan result."""
        # Check if RFID is available
        tag = db.fetchone("SELECT * FROM rfid_tags WHERE uid = ?", (uid,))
        
        if not tag or tag['status'] != 'available':
            self._show_error(f"RFID {uid} is not available")
            return
        
        self.flow_data['rfid_uid'] = uid
        logger.info(f"RFID scanned: {uid}")
        
        self._show_weight_measurement()
    
    def _show_weight_measurement(self):
        """Step 3: Weight measurement."""
        self.content_area.clear_widgets()
        self.control_buttons.clear_widgets()
        
        self.title_label.text = '[b]Step 3: Weight Measurement[/b]'
        self.progress.value = 40
        
        info = BoxLayout(orientation='vertical', spacing=10)
        
        info.add_widget(Label(
            text='Place sacks on the scale',
            font_size='24sp',
            size_hint_y=0.3
        ))
        
        self.weight_label = Label(
            text='Weight: --- kg',
            font_size='32sp',
            bold=True,
            color=(0, 1, 0, 1),
            size_hint_y=0.4
        )
        info.add_widget(self.weight_label)
        
        self.content_area.add_widget(info)
        
        # Control buttons
        btn_tare = Button(
            text='Tare Scale',
            font_size='22sp',
            background_color=(0.6, 0.6, 0.2, 1)
        )
        btn_tare.bind(on_press=self._on_tare_scale)
        self.control_buttons.add_widget(btn_tare)
        
        btn_read = Button(
            text='Read Weight',
            font_size='22sp',
            background_color=(0.2, 0.6, 0.2, 1)
        )
        btn_read.bind(on_press=self._on_read_weight)
        self.control_buttons.add_widget(btn_read)
    
    def _on_tare_scale(self, *args):
        """Tare the scale."""
        hw = get_hardware()
        success = hw.weight.tare()
        
        if success:
            self.weight_label.text = 'Weight: 0.00 kg (Tared)'
        else:
            self._show_error("Failed to tare scale")
    
    def _on_read_weight(self, *args):
        """Read weight from scale."""
        hw = get_hardware()
        weight = hw.weight.read_weight(samples=5)
        
        if weight and weight > 0:
            self.flow_data['weight_kg'] = weight
            self.weight_label.text = f'Weight: {weight:.2f} kg'
            
            # Auto-advance after 2 seconds
            from kivy.clock import Clock
            Clock.schedule_once(lambda dt: self._show_moisture_measurement(), 2)
        else:
            self._show_error("Invalid weight reading")
    
    def _show_moisture_measurement(self):
        """Step 4: Moisture measurement."""
        self.content_area.clear_widgets()
        self.control_buttons.clear_widgets()
        
        self.title_label.text = '[b]Step 4: Moisture Measurement[/b]'
        self.progress.value = 55
        
        info = BoxLayout(orientation='vertical', spacing=10)
        
        info.add_widget(Label(
            text='Insert moisture probe into crop',
            font_size='24sp',
            size_hint_y=0.3
        ))
        
        self.moisture_label = Label(
            text='Moisture: ---%',
            font_size='32sp',
            bold=True,
            color=(0, 1, 0, 1),
            size_hint_y=0.4
        )
        info.add_widget(self.moisture_label)
        
        self.content_area.add_widget(info)
        
        # Control button
        btn_read = Button(
            text='Read Moisture',
            font_size='22sp',
            background_color=(0.2, 0.6, 0.2, 1)
        )
        btn_read.bind(on_press=self._on_read_moisture)
        self.control_buttons.add_widget(btn_read)
    
    def _on_read_moisture(self, *args):
        """Read moisture from sensors."""
        hw = get_hardware()
        readings = hw.moisture.read_moisture()
        
        if readings:
            avg_moisture = readings[-1]  # Last element is average
            self.flow_data['moisture_percent'] = avg_moisture
            self.flow_data['moisture_readings'] = readings[:-1]  # Individual sensors
            
            self.moisture_label.text = f'Moisture: {avg_moisture:.2f}%'
            
            # Auto-advance
            from kivy.clock import Clock
            Clock.schedule_once(lambda dt: self._show_crop_selection(), 2)
        else:
            self._show_error("Failed to read moisture")
    
    def _show_crop_selection(self):
        """Step 5: Crop type selection."""
        self.content_area.clear_widgets()
        self.control_buttons.clear_widgets()
        
        self.title_label.text = '[b]Step 5: Select Crop Type[/b]'
        self.progress.value = 70
        
        label = Label(
            text='Select Crop Type:',
            font_size='24sp',
            size_hint_y=0.2
        )
        self.content_area.add_widget(label)
        
        crops = ['rice', 'wheat', 'maize', 'pulses']
        crop_buttons = GridLayout(cols=2, spacing=20, padding=20, size_hint_y=0.8)
        
        for crop in crops:
            btn = Button(
                text=crop.upper(),
                font_size='28sp',
                bold=True,
                background_color=(0.2, 0.6, 0.8, 1)
            )
            btn.crop_type = crop
            btn.bind(on_press=self._on_crop_selected)
            crop_buttons.add_widget(btn)
        
        self.content_area.add_widget(crop_buttons)
    
    def _on_crop_selected(self, button):
        """Handle crop selection."""
        crop_type = button.crop_type
        self.flow_data['crop_type'] = crop_type
        
        logger.info(f"Crop selected: {crop_type}")
        
        # Validate quality and capacity
        self._validate_and_calculate()
    
    def _validate_and_calculate(self):
        """Step 6: Quality check, capacity check, billing."""
        crop_type = self.flow_data['crop_type']
        weight_kg = self.flow_data['weight_kg']
        moisture = self.flow_data['moisture_percent']
        
        # Quality check
        accepted, grade, message = self.quality.validate_moisture(crop_type, moisture)
        
        if not accepted:
            self._show_error(f"Quality Rejected: {message}")
            return
        
        self.flow_data['quality_grade'] = grade
        
        # Weight validation
        weight_ok, weight_msg = self.quality.validate_weight(weight_kg)
        if not weight_ok:
            self._show_error(weight_msg)
            return
        
        # Capacity check
        capacity_ok, capacity_msg = self.inventory.check_capacity(crop_type, weight_kg)
        if not capacity_ok:
            self._show_error(capacity_msg)
            return
        
        # Allocate stack
        stack_location = self.inventory.allocate_stack(crop_type, weight_kg)
        if not stack_location:
            self._show_error("No available storage space")
            return
        
        self.flow_data['stack_location'] = stack_location
        
        # Calculate billing (assume 1 month storage)
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
        
        # Show summary and proceed to payment
        self._show_summary()
    
    def _show_summary(self):
        """Show storage summary and proceed to payment."""
        self.content_area.clear_widgets()
        self.control_buttons.clear_widgets()
        
        self.title_label.text = '[b]Storage Summary[/b]'
        self.progress.value = 85
        
        summary = BoxLayout(orientation='vertical', spacing=5, padding=10)
        
        data = self.flow_data
        
        summary.add_widget(Label(text='[b]Storage Details[/b]', markup=True, font_size='24sp', size_hint_y=0.1))
        summary.add_widget(Label(text=f"Farmer: {self.farmer['name']}", font_size='18sp', size_hint_y=0.08))
        summary.add_widget(Label(text=f"Crop: {data['crop_type'].upper()}", font_size='18sp', size_hint_y=0.08))
        summary.add_widget(Label(text=f"Weight: {data['weight_kg']:.2f} kg", font_size='18sp', size_hint_y=0.08))
        summary.add_widget(Label(text=f"Moisture: {data['moisture_percent']:.2f}%", font_size='18sp', size_hint_y=0.08))
        summary.add_widget(Label(text=f"Quality: Grade {data['quality_grade']}", font_size='18sp', size_hint_y=0.08))
        summary.add_widget(Label(text=f"Stack: {data['stack_location']}", font_size='18sp', size_hint_y=0.08))
        summary.add_widget(Label(text=f"Expiry: {data['expiry_date']}", font_size='18sp', size_hint_y=0.08))
        
        summary.add_widget(Label(text='', size_hint_y=0.05))  # Spacer
        
        summary.add_widget(Label(
            text=f"[b]Storage Fee: ₹{data['storage_fee']:.2f}[/b]",
            markup=True,
            font_size='28sp',
            color=(0, 1, 0, 1),
            size_hint_y=0.15
        ))
        
        self.content_area.add_widget(summary)
        
        # Control button
        btn_payment = Button(
            text='Proceed to Payment',
            font_size='24sp',
            bold=True,
            background_color=(0.2, 0.6, 0.2, 1)
        )
        btn_payment.bind(on_press=self._show_payment)
        self.control_buttons.add_widget(btn_payment)
    
    def _show_payment(self, *args):
        """Show payment screen."""
        # Switch to payment screen
        payment_screen = self.manager.get_screen('payment')
        payment_screen.setup_payment(
            amount=self.flow_data['storage_fee'],
            transaction_type='storage',
            on_payment_complete=self._on_payment_complete
        )
        self.manager.current = 'payment'
    
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
        
        # Update RFID tag
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
                'godown_name': self.app.config.get('godown_name', 'Godown'),
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
        self._show_receipt(txn_id)
    
    def _show_receipt(self, txn_id):
        """Show receipt."""
        self.progress.value = 100
        
        receipt_data = self.payment_sim.generate_receipt(txn_id, self.app.current_language)
        
        # Show receipt viewer
        from ui.components.receipt_viewer import ReceiptViewer
        
        receipt_viewer = ReceiptViewer()
        receipt_viewer.show_receipt(receipt_data)
        
        popup = Popup(
            title='Storage Receipt',
            content=receipt_viewer,
            size_hint=(0.9, 0.9)
        )
        
        # Override close to go back to startup
        original_close = receipt_viewer._on_close
        
        def new_close(*args):
            popup.dismiss()
            self.manager.current = 'startup'
        
        receipt_viewer._on_close = new_close
        
        popup.open()
    
    def _show_error(self, message):
        """Show error popup."""
        content = BoxLayout(orientation='vertical', padding=20, spacing=10)
        content.add_widget(Label(text=message, font_size='20sp'))
        
        popup = Popup(
            title='Error',
            content=content,
            size_hint=(0.6, 0.3)
        )
        
        btn_ok = Button(text='OK', font_size='20sp', size_hint_y=0.3)
        btn_ok.bind(on_press=popup.dismiss)
        content.add_widget(btn_ok)
        
        popup.open()
        logger.error(message)
    
    def _on_back(self, *args):
        """Go back to startup."""
        if self.session:
            self.session.rollback()
        self.manager.current = 'startup' 