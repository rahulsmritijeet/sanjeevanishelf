"""
Razorpay Payment Integration
QR generation, payment link creation (simulation-safe).
"""

import logging
from typing import Dict, Optional, Tuple
import qrcode
from io import BytesIO
from PIL import Image

logger = logging.getLogger(__name__)


class RazorpayHandler:
    """Handle Razorpay payment QR generation and tracking."""
    
    def __init__(self, config: Dict, simulation: bool = False):
        self.config = config
        self.simulation = simulation
        
        rp_config = config.get('razorpay', {})
        self.key_id = rp_config.get('key_id', '')
        self.key_secret = rp_config.get('key_secret', '')
        self.merchant_name = rp_config.get('merchant_name', 'Panchayat Godown')
        
        self.client = None
        
        if not simulation and self.key_id and self.key_secret:
            try:
                import razorpay
                self.client = razorpay.Client(auth=(self.key_id, self.key_secret))
                logger.info("Razorpay client initialized (REAL mode)")
            except ImportError:
                logger.warning("razorpay package not installed, using simulation")
                self.simulation = True
        else:
            self.simulation = True
            logger.info("Razorpay in SIMULATION mode")
    
    def create_qr_code(self, amount: float, transaction_id: str, 
                       description: str = "Storage Fee") -> Tuple[Optional[str], Optional[bytes]]:
        """
        Create payment QR code.
        Returns (qr_url: str, qr_image_bytes: bytes)
        In simulation: returns local QR image.
        """
        if self.simulation:
            return self._create_simulation_qr(amount, transaction_id, description)
        
        try:
            # Create Razorpay QR code
            qr_data = self.client.qr_code.create({
                "type": "upi_qr",
                "name": self.merchant_name,
                "usage": "single_use",
                "fixed_amount": True,
                "payment_amount": int(amount * 100),  # Convert to paise
                "description": description,
                "customer_id": transaction_id,
                "close_by": int((datetime.now() + timedelta(hours=24)).timestamp())
            })
            
            qr_url = qr_data.get('image_url')
            logger.info(f"Razorpay QR created: {qr_url}")
            
            # Download QR image
            import requests
            response = requests.get(qr_url)
            qr_image = response.content if response.status_code == 200 else None
            
            return qr_url, qr_image
        
        except Exception as e:
            logger.error(f"Failed to create Razorpay QR: {e}")
            # Fallback to simulation
            return self._create_simulation_qr(amount, transaction_id, description)
    
    def _create_simulation_qr(self, amount: float, transaction_id: str,
                             description: str) -> Tuple[str, bytes]:
        """Create a simulated QR code image."""
        # Create UPI payment string
        upi_string = f"upi://pay?pa=godown@paytm&pn={self.merchant_name}&am={amount}&tn={description}&tr={transaction_id}"
        
        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(upi_string)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to bytes
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        qr_bytes = buffer.getvalue()
        
        logger.info(f"[SIM] QR code created for ₹{amount}, txn: {transaction_id}")
        
        return upi_string, qr_bytes
    
    def create_payment_link(self, amount: float, customer_phone: str,
                           customer_name: str, description: str) -> Optional[str]:
        """
        Create a payment link (for SMS/WhatsApp).
        In simulation: returns a dummy link.
        """
        if self.simulation:
            link = f"https://razorpay.com/pay/sim_{customer_phone}_{int(amount)}"
            logger.info(f"[SIM] Payment link: {link}")
            return link
        
        try:
            from datetime import datetime, timedelta
            
            link_data = self.client.payment_link.create({
                "amount": int(amount * 100),
                "currency": "INR",
                "description": description,
                "customer": {
                    "name": customer_name,
                    "contact": customer_phone
                },
                "notify": {
                    "sms": False,
                    "email": False
                },
                "reminder_enable": False,
                "callback_url": "",
                "callback_method": "get"
            })
            
            link_url = link_data.get('short_url')
            logger.info(f"Razorpay payment link created: {link_url}")
            return link_url
        
        except Exception as e:
            logger.error(f"Failed to create payment link: {e}")
            return None
    
    def verify_payment(self, payment_id: str) -> bool:
        """
        Verify payment status.
        In simulation: always returns True (manual button press).
        """
        if self.simulation:
            logger.info(f"[SIM] Payment verified: {payment_id}")
            return True
        
        try:
            payment = self.client.payment.fetch(payment_id)
            status = payment.get('status')
            return status == 'captured'
        except Exception as e:
            logger.error(f"Payment verification failed: {e}")
            return False