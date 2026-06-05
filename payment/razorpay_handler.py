"""
Razorpay Payment Integration
QR generation using qrcode library only (no PIL needed).
Uses Razorpay TEST API keys.
"""

import logging
from typing import Dict, Optional, Tuple
from io import BytesIO
import json

logger = logging.getLogger(__name__)


class RazorpayHandler:
    """Handle Razorpay payments with test API keys."""
    
    def __init__(self, config: Dict, simulation: bool = False):
        self.config = config
        self.simulation = simulation
        
        rp_config = config.get('razorpay', {})
        self.key_id = rp_config.get('key_id', '')
        self.key_secret = rp_config.get('key_secret', '')
        self.merchant_name = rp_config.get('merchant_name', 'Panchayat Godown')
        
        self.client = None
        
        # Try to initialize Razorpay client with test keys
        if self.key_id and self.key_secret:
            try:
                import razorpay
                self.client = razorpay.Client(auth=(self.key_id, self.key_secret))
                self.simulation = False
                logger.info(f"Razorpay client initialized (TEST mode)")
                logger.info(f"Key ID: {self.key_id[:15]}...")
            except ImportError:
                logger.warning("razorpay package not installed. Run: pip install razorpay")
                self.simulation = True
            except Exception as e:
                logger.error(f"Razorpay init failed: {e}")
                self.simulation = True
        else:
            self.simulation = True
            logger.info("Razorpay in SIMULATION mode (no keys provided)")
    
    def create_order(self, amount: float, receipt: str,
                     notes: Dict = None) -> Optional[Dict]:
        """
        Create a Razorpay order.
        Returns order data dict with 'id', 'amount', 'status'.
        """
        if self.simulation:
            order = {
                'id': f'order_sim_{receipt}',
                'amount': int(amount * 100),
                'currency': 'INR',
                'receipt': receipt,
                'status': 'created'
            }
            logger.info(f"[SIM] Order created: {order['id']}")
            return order
        
        try:
            order_data = {
                'amount': int(amount * 100),  # paise
                'currency': 'INR',
                'receipt': receipt,
                'notes': notes or {}
            }
            
            order = self.client.order.create(data=order_data)
            logger.info(f"Razorpay order created: {order['id']}")
            return order
        
        except Exception as e:
            logger.error(f"Order creation failed: {e}")
            return None
    
    def create_payment_link(self, amount: float, customer_phone: str,
                           customer_name: str, description: str,
                           reference_id: str) -> Optional[str]:
        """
        Create payment link for UPI/cards.
        Returns short URL.
        """
        if self.simulation:
            link = f"https://rzp.io/sim/{reference_id}"
            logger.info(f"[SIM] Payment link: {link}")
            return link
        
        try:
            link_data = self.client.payment_link.create({
                'amount': int(amount * 100),
                'currency': 'INR',
                'description': description,
                'customer': {
                    'name': customer_name,
                    'contact': customer_phone
                },
                'notify': {
                    'sms': True,
                    'email': False
                },
                'reminder_enable': False,
                'reference_id': reference_id
            })
            
            link_url = link_data.get('short_url')
            logger.info(f"Payment link created: {link_url}")
            return link_url
        
        except Exception as e:
            logger.error(f"Payment link creation failed: {e}")
            return None
    
    def create_qr_code(self, amount: float, transaction_id: str,
                       description: str = "Storage Fee") -> Tuple[Optional[str], Optional[bytes]]:
        """
        Create QR code for UPI payment.
        Returns (upi_string, qr_image_bytes).
        """
        # Generate UPI payment string
        upi_string = (
            f"upi://pay?"
            f"pa=godown@paytm&"
            f"pn={self.merchant_name}&"
            f"am={amount}&"
            f"tn={description}&"
            f"tr={transaction_id}"
        )
        
        try:
            import qrcode
            
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(upi_string)
            qr.make(fit=True)
            
            # Create image WITHOUT PIL - use PNG writer
            buffer = BytesIO()
            qr.make_image().save(buffer, format='PNG')
            qr_bytes = buffer.getvalue()
            
            logger.info(f"QR code created for Rs.{amount}, txn: {transaction_id}")
            return upi_string, qr_bytes
        
        except Exception as e:
            logger.error(f"QR generation failed: {e}")
            # Return text-based fallback
            return upi_string, None
    
    def verify_payment(self, payment_id: str) -> Tuple[bool, Dict]:
        """
        Verify payment status.
        Returns (success, payment_data).
        """
        if self.simulation:
            logger.info(f"[SIM] Payment verified: {payment_id}")
            return True, {
                'id': payment_id,
                'status': 'captured',
                'amount': 0,
                'method': 'simulation'
            }
        
        try:
            payment = self.client.payment.fetch(payment_id)
            status = payment.get('status')
            success = status == 'captured'
            
            logger.info(f"Payment {payment_id} status: {status}")
            return success, payment
        
        except Exception as e:
            logger.error(f"Payment verification failed: {e}")
            return False, {}
    
    def verify_payment_link(self, payment_link_id: str) -> Tuple[bool, Dict]:
        """Check if payment link has been paid."""
        if self.simulation:
            return False, {}
        
        try:
            link = self.client.payment_link.fetch(payment_link_id)
            status = link.get('status')
            paid = status == 'paid'
            
            logger.info(f"Payment link {payment_link_id} status: {status}")
            return paid, link
        
        except Exception as e:
            logger.error(f"Payment link check failed: {e}")
            return False, {}