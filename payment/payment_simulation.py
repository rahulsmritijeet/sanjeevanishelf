"""
Payment Simulation Module
Handles payment and payout flows.
"""

import logging
from typing import Dict, Tuple
from datetime import datetime
from database.db_manager import db

logger = logging.getLogger(__name__)


class PaymentSimulator:
    """Handle simulated payments."""
    
    def __init__(self, simulation: bool = True):
        self.simulation = simulation
        logger.info(f"Payment handler initialized")
    
    def simulate_payment_received(self, transaction_id: int, amount: float,
                                  payment_method: str = 'simulation') -> Tuple[bool, str]:
        """Mark payment as received."""
        try:
            payment_ref = f"PAY-{int(datetime.now().timestamp())}"
            
            # Only update transaction if ID is valid
            if transaction_id and transaction_id > 0:
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
                try:
                    db.insert('payment_events', {
                        'transaction_id': transaction_id,
                        'event_type': 'payment_success',
                        'amount': amount,
                        'payment_ref': payment_ref,
                        'simulated': 1
                    })
                except Exception as e:
                    logger.warning(f"Payment event log skipped: {e}")
            
            logger.info(f"Payment received: Rs.{amount} ref={payment_ref}")
            
            print(f"\n{'='*60}")
            print(f"PAYMENT RECEIVED")
            print(f"Amount: Rs.{amount}")
            print(f"Method: {payment_method}")
            print(f"Reference: {payment_ref}")
            print(f"{'='*60}\n")
            
            return True, payment_ref
        
        except Exception as e:
            logger.error(f"Payment simulation failed: {e}")
            return False, ""
    
    def simulate_payout_sent(self, transaction_id: int, farmer_id: int,
                            amount: float, bank_account: str = "XXXX1234") -> Tuple[bool, str]:
        """Mark payout as sent."""
        try:
            payout_ref = f"PAYOUT-{int(datetime.now().timestamp())}"
            
            # Only update transaction if ID is valid
            if transaction_id and transaction_id > 0:
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
                try:
                    db.insert('payment_events', {
                        'transaction_id': transaction_id,
                        'event_type': 'payout_success',
                        'amount': amount,
                        'payment_ref': payout_ref,
                        'simulated': 1
                    })
                except Exception as e:
                    logger.warning(f"Payout event log skipped: {e}")
            
            logger.info(f"Payout sent: Rs.{amount} to farmer {farmer_id} ref={payout_ref}")
            
            print(f"\n{'='*60}")
            print(f"PAYOUT SENT")
            print(f"Farmer ID: {farmer_id}")
            print(f"Amount: Rs.{amount}")
            print(f"Bank Account: {bank_account}")
            print(f"Reference: {payout_ref}")
            print(f"{'='*60}\n")
            
            return True, payout_ref
        
        except Exception as e:
            logger.error(f"Payout failed: {e}")
            return False, ""
    
    def generate_receipt(self, transaction_id: int, language: str = 'en') -> Dict:
        """Generate receipt data."""
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
        receipt['is_simulation'] = self.simulation
        receipt['receipt_number'] = f"RCP-{transaction_id:06d}"
        receipt['receipt_date'] = datetime.now().strftime('%d/%m/%Y %H:%M')
        
        return receipt