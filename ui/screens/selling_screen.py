"""
Selling Flow Screen
Farmer sells stored crop back to godown.
"""

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.progressbar import ProgressBar
from kivy.uix.popup import Popup
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


class SellingScreen(Screen):
    """Selling flow screen."""
    
    def __init__(self, app_instance, **kwargs):
        super().__init__(**kwargs)
        self.app = app_instance
        self.name = 'selling'
        
        self.inventory = InventoryManager(app_instance.app_config)
        self.billing = BillingEngine(app_instance.app_config)
        self.payment_sim = PaymentSimulator()
        
        self.session = None
        self.batch = None
        self.farmer = None
        self.flow_data = {}
        
        self._build_ui()
    
    def _build_ui(self):
        """Build selling UI."""
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Header
        header = BoxLayout(size_hint_y=0.1, spacing=10)
        
        self.title_label = Label(
            text='[b]SELLING FLOW[/b]',
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
        
        # Progress
        self.progress = ProgressBar(max=100, size_hint_y=0.05)
        layout.add_widget(self.progress)
        
        # Content
        self.content_area = BoxLayout(orientation='vertical', size_hint_y=0.7, padding=20, spacing=15)
        layout.add_widget(self.content_area)
        
        # Controls
        self.control_buttons = BoxLayout(size_hint_y=0.15, spacing=10)
        layout.add_widget(self.control_buttons)
        
        self.add_widget(layout)
    
    def on_enter(self):
        """Initialize screen."""
        user_id = self.app.current_user['id']
        self.session = SessionManager(operator_id=user_id, mode='selling')
        
        self._show_batch_scan()
    
    def _show_batch_scan(self):
        """Step 1: Scan batch RFID."""
        self.content_area.clear_widgets()
        self.control_buttons.clear_widgets()
        
        self.title_label.text = '[b]Step 1: Scan Batch RFID[/b]'
        self.progress.value = 20
        
        info = BoxLayout(orientation='vertical', spacing=10)
        
        info.add_widget(Label(
            text='[b]Scan the RFID tag on the sacks...[/b]',
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
        
        import threading
        
        def scan_thread():
            uid = hw.rfid.read_uid(timeout=10)
            
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
        # Get a stored batch
        row = db.fetchone(
            "SELECT rfid_uid FROM batches WHERE status = 'stored' LIMIT 1"
        )
        if row:
            self._on_rfid_received(row['rfid_uid'])
        else:
            self._show_error("No stored batches found")
    
    def _on_rfid_received(self, uid):
        """Handle RFID scan result."""
        batch = db.get_batch_by_rfid(uid)
        
        if not batch:
            self._show_error(f"Batch not found for RFID {uid}")
            return
        
        self.batch = batch
        self.farmer = db.get_farmer_by_phone(batch['farmer_phone'])
        self.flow_data['batch_id'] = batch['id']
        self.flow_data['farmer_id'] = self.farmer['id']
        
        self.session.start(farmer_id=self.farmer['id'])
        
        logger.info(f"Batch found: {batch['batch_code']}")
        
        self._show_batch_details()
    
    def _show_batch_details(self):
        """Step 2: Show batch details and calculate amount."""
        self.content_area.clear_widgets()
        self.control_buttons.clear_widgets()
        
        self.title_label.text = '[b]Step 2: Batch Details[/b]'
        self.progress.value = 50
        
        batch = self.batch
        
        details = BoxLayout(orientation='vertical', spacing=10, padding=10)
        
        details.add_widget(Label(text='[b]Batch Information[/b]', markup=True, font_size='24sp', size_hint_y=0.1))
        details.add_widget(Label(text=f"Batch Code: {batch['batch_code']}", font_size='18sp', size_hint_y=0.08))
        details.add_widget(Label(text=f"Farmer: {batch['farmer_name']}", font_size='18sp', size_hint_y=0.08))
        details.add_widget(Label(text=f"Crop: {batch['crop_type'].upper()}", font_size='18sp', size_hint_y=0.08))
        details.add_widget(Label(text=f"Weight: {batch['weight_kg']:.2f} kg", font_size='18sp', size_hint_y=0.08))
        details.add_widget(Label(text=f"Quality: Grade {batch['quality_grade']}", font_size='18sp', size_hint_y=0.08))
        details.add_widget(Label(text=f"Stored: {batch['storage_date']}", font_size='18sp', size_hint_y=0.08))
        
        # Calculate selling amount
        amount, breakdown = self.billing.calculate_selling_amount(
            batch['crop_type'],
            batch['weight_kg'],
            batch['quality_grade']
        )
        
        self.flow_data['amount'] = amount
        self.flow_data['billing_breakdown'] = breakdown
        
        details.add_widget(Label(text='', size_hint_y=0.05))  # Spacer
        
        details.add_widget(Label(
            text=f"[b]Amount to Pay Farmer: ₹{amount:.2f}[/b]",
            markup=True,
            font_size='28sp',
            color=(0, 1, 0, 1),
            size_hint_y=0.15
        ))
        
        details.add_widget(Label(
            text=f"(Rate: ₹{breakdown['base_rate']}/kg)",
            font_size='16sp',
            size_hint_y=0.08
        ))
        
        self.content_area.add_widget(details)
        
        # Control button
        btn_proceed = Button(
            text='Proceed to Payout',
            font_size='24sp',
            bold=True,
            background_color=(0.2, 0.6, 0.2, 1)
        )
        btn_proceed.bind(on_press=self._show_payment)
        self.control_buttons.add_widget(btn_proceed)
    
    def _show_payment(self, *args):
        """Show payout screen."""
        payment_screen = self.manager.get_screen('payment')
        payment_screen.setup_payment(
            amount=self.flow_data['amount'],
            transaction_type='selling',
            on_payment_complete=self._on_payout_complete
        )
        self.manager.current = 'payment'
    
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
        
        # Show receipt
        self._show_receipt(txn_id)
    
    def _show_receipt(self, txn_id):
        """Show receipt."""
        self.progress.value = 100
        
        receipt_data = self.payment_sim.generate_receipt(txn_id, self.app.current_language)
        
        from ui.components.receipt_viewer import ReceiptViewer
        
        receipt_viewer = ReceiptViewer()
        receipt_viewer.show_receipt(receipt_data)
        
        popup = Popup(
            title='Selling Receipt',
            content=receipt_viewer,
            size_hint=(0.9, 0.9)
        )
        
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