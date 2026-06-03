"""
Expiry Management and Confiscation
Automated expiry checks, notifications, and confiscation workflow.
"""

import logging
from typing import List, Dict
from datetime import datetime, timedelta
from database.db_manager import db
from comms.whatsapp_queue import get_whatsapp
from comms.whatsapp_templates import WhatsAppTemplates

logger = logging.getLogger(__name__)


class ExpiryManager:
    """Manage expiry checks, warnings, and confiscation."""
    
    def __init__(self, config: Dict):
        self.config = config
        self.godown_name = config.get('godown_name', 'Godown')
        self.contact_number = config.get('contact_number', '1800-XXX-XXXX')
    
    def check_expiring_batches(self, warning_days: int = 7) -> List[Dict]:
        """
        Check for batches expiring soon.
        Returns list of batches within warning threshold.
        """
        threshold_date = (datetime.now() + timedelta(days=warning_days)).date()
        
        rows = db.fetchall(
            """
            SELECT b.*, f.name as farmer_name, f.phone as farmer_phone
            FROM batches b
            JOIN farmers f ON b.farmer_id = f.id
            WHERE b.status = 'stored' AND b.expiry_date <= ?
            ORDER BY b.expiry_date ASC
            """,
            (threshold_date.isoformat(),)
        )
        
        batches = [dict(row) for row in rows]
        logger.info(f"Found {len(batches)} batches expiring within {warning_days} days")
        return batches
    
    def send_expiry_warnings(self, language: str = 'en') -> int:
        """
        Send WhatsApp warnings for expiring batches.
        Returns number of warnings sent.
        """
        batches = self.check_expiring_batches(warning_days=7)
        whatsapp = get_whatsapp()
        
        count = 0
        for batch in batches:
            expiry_date = datetime.fromisoformat(batch['expiry_date']).date()
            days_remaining = (expiry_date - datetime.now().date()).days
            
            if days_remaining < 0:
                continue  # Already expired, will be confiscated
            
            message = WhatsAppTemplates.format_message(
                'EXPIRY_WARNING',
                language,
                {
                    'godown_name': self.godown_name,
                    'farmer_name': batch['farmer_name'],
                    'batch_code': batch['batch_code'],
                    'crop_type': batch['crop_type'],
                    'weight_kg': batch['weight_kg'],
                    'expiry_date': expiry_date.strftime('%d/%m/%Y'),
                    'days_remaining': days_remaining,
                    'contact_number': self.contact_number
                }
            )
            
            whatsapp.enqueue(
                batch['farmer_phone'],
                message,
                language,
                template_name='EXPIRY_WARNING',
                priority=8
            )
            count += 1
        
        logger.info(f"Sent {count} expiry warnings")
        return count
    
    def confiscate_expired(self) -> int:
        """
        Confiscate all expired batches and update inventory.
        Returns number of batches confiscated.
        """
        today = datetime.now().date()
        
        expired = db.fetchall(
            """
            SELECT b.*, f.name as farmer_name, f.phone as farmer_phone
            FROM batches b
            JOIN farmers f ON b.farmer_id = f.id
            WHERE b.status = 'stored' AND b.expiry_date < ?
            """,
            (today.isoformat(),)
        )
        
        count = 0
        for batch in expired:
            try:
                # Update batch status
                db.update(
                    'batches',
                    {
                        'status': 'confiscated',
                        'confiscation_reason': 'Expired - Not withdrawn in time',
                        'confiscation_date': today.isoformat()
                    },
                    'id = ?',
                    (batch['id'],)
                )
                
                # Update crop stock
                db.update_crop_stock(batch['crop_type'], -batch['weight_kg'])
                
                # Update stack weight
                if batch['stack_location']:
                    from core.inventory import InventoryManager
                    inv = InventoryManager(self.config)
                    inv.update_stack_weight(batch['stack_location'], -batch['weight_kg'])
                
                # Release RFID tag
                if batch['rfid_uid']:
                    db.update(
                        'rfid_tags',
                        {'status': 'available', 'assigned_to_batch_id': None},
                        'uid = ?',
                        (batch['rfid_uid'],)
                    )
                
                # Log event
                db.log_event(
                    session_id=None,
                    event_type='batch_confiscated',
                    entity_type='batch',
                    entity_id=batch['id'],
                    old_value=batch['status'],
                    new_value='confiscated',
                    operator_id=None
                )
                
                count += 1
                logger.info(f"Confiscated batch {batch['batch_code']}")
            
            except Exception as e:
                logger.error(f"Failed to confiscate batch {batch['id']}: {e}")
        
        logger.info(f"Confiscated {count} expired batches")
        return count
    
    def get_confiscated_inventory(self) -> List[Dict]:
        """Get list of all confiscated batches."""
        rows = db.fetchall(
            """
            SELECT b.*, f.name as farmer_name, f.phone as farmer_phone
            FROM batches b
            JOIN farmers f ON b.farmer_id = f.id
            WHERE b.status = 'confiscated'
            ORDER BY b.confiscation_date DESC
            """
        )
        return [dict(row) for row in rows]
    
    def daily_expiry_check(self, language: str = 'en'):
        """
        Daily automated check: send warnings and confiscate expired.
        Should be run via cron job.
        """
        logger.info("Running daily expiry check...")
        
        warnings_sent = self.send_expiry_warnings(language)
        confiscated = self.confiscate_expired()
        
        logger.info(f"Daily expiry check complete: {warnings_sent} warnings, {confiscated} confiscated")
        
        return {
            'warnings_sent': warnings_sent,
            'confiscated': confiscated,
            'timestamp': datetime.now().isoformat()
        }