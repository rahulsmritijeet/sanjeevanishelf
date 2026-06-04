"""
Payment Screen
QR display and simulation payment buttons.
"""

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.image import Image as KivyImage
from kivy.core.image import Image as CoreImage
from io import BytesIO
import logging
from payment.razorpay_handler import RazorpayHandler
from payment.payment_simulation import PaymentSimulator

logger = logging.getLogger(__name__)


class PaymentScreen(Screen):
    """Payment/QR display screen."""
    
    def __init__(self, app_instance, **kwargs):
        super().__init__(**kwargs)
        self.app = app_instance
        self.name = 'payment'
        
        self.razorpay = RazorpayHandler(app_instance.app_config, simulation=app_instance.app_config.get('simulation_mode'))
        self.payment_sim = PaymentSimulator()
        
        self.amount = 0
        self.transaction_type = 'storage'
        self.on_complete_callback = None
        
        self._build_ui()
    
    def _build_ui(self):
        """Build payment UI."""
        layout = BoxLayout(orientation='vertical', padding=20, spacing=20)
        
        # Title
        self.title_label = Label(
            text='[b]PAYMENT[/b]',
            markup=True,
            font_size='32sp',
            size_hint_y=0.1
        )
        layout.add_widget(self.title_label)
        
        # Amount display
        self.amount_label = Label(
            text='Amount: ₹0.00',
            font_size='36sp',
            bold=True,
            color=(0, 1, 0, 1),
            size_hint_y=0.15
        )
        layout.add_widget(self.amount_label)
        
        # QR code area
        qr_container = BoxLayout(orientation='vertical', size_hint_y=0.5, padding=10)
        
        qr_container.add_widget(Label(
            text='Scan QR to Pay:',
            font_size='24sp',
            size_hint_y=0.1
        ))
        
        self.qr_image = KivyImage(
            size_hint_y=0.9,
            allow_stretch=True,
            keep_ratio=True
        )
        qr_container.add_widget(self.qr_image)
        
        layout.add_widget(qr_container)
        
        # Simulation buttons
        self.sim_buttons = BoxLayout(size_hint_y=0.25, spacing=10)
        layout.add_widget(self.sim_buttons)
        
        self.add_widget(layout)
    
    def setup_payment(self, amount, transaction_type='storage', on_payment_complete=None):
        """Setup payment screen."""
        self.amount = amount
        self.transaction_type = transaction_type
        self.on_complete_callback = on_payment_complete
        
        # Update UI
        if transaction_type == 'storage':
            self.title_label.text = '[b]PAYMENT - Storage Fee[/b]'
            self.amount_label.text = f'Amount to Pay: ₹{amount:.2f}'
        elif transaction_type == 'buying':
            self.title_label.text = '[b]PAYMENT - Purchase Payment[/b]'
            self.amount_label.text = f'Amount to Pay Farmer: ₹{amount:.2f}'
        elif transaction_type == 'selling':
            self.title_label.text = '[b]PAYOUT - Selling Payment[/b]'
            self.amount_label.text = f'Amount to Pay Farmer: ₹{amount:.2f}'
        
        # Generate QR
        self._generate_qr()
        
        # Setup buttons
        self._setup_buttons()
    
    def _generate_qr(self):
        """Generate and display QR code."""
        txn_id = f"TXN-{int(datetime.now().timestamp())}"
        
        qr_url, qr_bytes = self.razorpay.create_qr_code(
            self.amount,
            txn_id,
            f"{self.transaction_type.title()} Payment"
        )
        
        if qr_bytes:
            # Load QR image
            data = BytesIO(qr_bytes)
            core_image = CoreImage(data, ext='png')
            self.qr_image.texture = core_image.texture
        else:
            logger.warning("Failed to generate QR code")
    
    def _setup_buttons(self):
        """Setup simulation buttons."""
        self.sim_buttons.clear_widgets()
        
        if self.transaction_type == 'storage':
            # Payment received button
            btn_paid = Button(
                text=f'''[b]PAYMENT DONE
₹{self.amount:.2f}
(SIMULATION)[/b]''',
                markup=True,
                font_size='24sp',
                background_color=(0.2, 0.8, 0.2, 1)
            )
            btn_paid.bind(on_press=self._on_payment_done)
            self.sim_buttons.add_widget(btn_paid)
        
        elif self.transaction_type in ['selling', 'buying']:
            # Payout sent button
            btn_payout = Button(
                text=f'''[b]PAYOUT DONE
₹{self.amount:.2f}
(SIMULATION)[/b]''',
                markup=True,
                font_size='24sp',
                background_color=(0.2, 0.8, 0.2, 1)
            )
            btn_payout.bind(on_press=self._on_payout_done)
            self.sim_buttons.add_widget(btn_payout)
        
        # Cancel button
        btn_cancel = Button(
            text='Cancel',
            font_size='20sp',
            background_color=(0.8, 0.2, 0.2, 1),
            size_hint_x=0.3
        )
        btn_cancel.bind(on_press=self._on_cancel)
        self.sim_buttons.add_widget(btn_cancel)
    
    def _on_payment_done(self, *args):
        """Handle payment simulation."""
        from datetime import datetime
        
        # Simulate payment received
        success, payment_ref = self.payment_sim.simulate_payment_received(
            transaction_id=0,  # Will be set by caller
            amount=self.amount,
            payment_method='simulation'
        )
        
        if success and self.on_complete_callback:
            self.on_complete_callback(payment_ref)
    
    def _on_payout_done(self, *args):
        """Handle payout simulation."""
        # Simulate payout sent
        success, payout_ref = self.payment_sim.simulate_payout_sent(
            transaction_id=0,  # Will be set by caller
            farmer_id=0,  # Will be set by caller
            amount=self.amount
        )
        
        if success and self.on_complete_callback:
            self.on_complete_callback(payout_ref)
    
    def _on_cancel(self, *args):
        """Cancel payment."""
        self.manager.current = 'startup' 