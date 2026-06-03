"""
Payment Simulation Module
Handles SIMULATION-ONLY payment and payout flows with clear UI indicators.
"""

import logging
from typing import Dict, Tuple
from datetime import datetime
from database.db_manager import db

logger = logging.getLogger(__name__)


class PaymentSimulator:
    """Simulate payment flows for testing and demo."""
    
    def __init__(self):
        logger.info("Payment Simulator initialized (SIMULATION MODE ONLY)")
    
    def simulate_payment_received(self, transaction_id: int, amount: float,
                                  payment_method: str = 'simulation') -> Tuple[bool, str]:
        """
        Simulate farmer payment received.
        Returns (success: bool, payment_ref: str)
        """
        try:
            payment_ref = f"SIM-PAY-{transaction_id}-{int(datetime.now().timestamp())}"
            
            # Update transaction
            db.update(
                'transactions',
                {
                    'payment_status': 'paid',
                    'payment_method': payment_method,
                    'payment_ref': payment_ref
                },
                'id = ?',
                (transaction_id,)
            )
            
            # Log payment event
            db.insert('payment_events', {
                'transaction_id': transaction_id,
                'event_type': 'payment_success',
                'amount': amount,
                'payment_ref': payment_ref,
                'simulated': 1
            })
            
            logger.info(f"[SIM] Payment received: ₹{amount} for txn {transaction_id}")
            print(f"
{'='*60}")
            print(f"PAYMENT SIMULATION - RECEIVED")
            print(f"Transaction ID: {transaction_id}")
            print(f"Amount: ₹{amount}")
            print(f"Reference: {payment_ref}")
            print(f"{'='*60}
")
            
            return True, payment_ref
        
        except Exception as e:
            logger.error(f"Payment simulation failed: {e}")
            return False, ""
    
    def simulate_payout_sent(self, transaction_id: int, farmer_id: int,
                            amount: float, bank_account: str = "XXXX1234") -> Tuple[bool, str]:
        """
        Simulate payout to farmer (for selling/buying).
        Returns (success: bool, payout_ref: str)
        """
        try:
            payout_ref = f"SIM-PAYOUT-{transaction_id}-{int(datetime.now().timestamp())}"
            
            # Update transaction
            db.update(
                'transactions',
                {
                    'payment_status': 'paid',
                    'payment_method': 'bank_transfer',
                    'payment_ref': payout_ref
                },
                'id = ?',
                (transaction_id,)
            )
            
            # Log payout event
            db.insert('payment_events', {
                'transaction_id': transaction_id,
                'event_type': 'payout_success',
                'amount': amount,
                'payment_ref': payout_ref,
                'simulated': 1
            })
            
            logger.info(f"[SIM] Payout sent: ₹{amount} to farmer {farmer_id}")
            print(f"
{'='*60}")
            print(f"PAYOUT SIMULATION - SENT")
            print(f"Transaction ID: {transaction_id}")
            print(f"Farmer ID: {farmer_id}")
            print(f"Amount: ₹{amount}")
            print(f"Bank Account: {bank_account}")
            print(f"Reference: {payout_ref}")
            print(f"{'='*60}
")
            
            return True, payout_ref
        
        except Exception as e:
            logger.error(f"Payout simulation failed: {e}")
            return False, ""
    
    def generate_receipt(self, transaction_id: int, language: str = 'en') -> Dict:
        """Generate receipt data for display/print."""
        txn = db.fetchone(
            """
            SELECT t.*, f.name as farmer_name, f.phone as farmer_phone,
                   u.full_name as operator_name
            FROM transactions t
            JOIN farmers f ON t.farmer_id = f.id
            JOIN users u ON t.operator_id = u.id
            WHERE t.id = ?
            """,
            (transaction_id,)
        )
        
        if not txn:
            return {}
        
        receipt = dict(txn)
        receipt['is_simulation'] = True
        receipt['receipt_number'] = f"RCP-{transaction_id:06d}"
        receipt['receipt_date'] = datetime.now().strftime('%d/%m/%Y %H:%M')
        
        return receipt