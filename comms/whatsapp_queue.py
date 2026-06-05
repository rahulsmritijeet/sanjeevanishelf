"""
WhatsApp Queue - Now sends SMS via Twilio
Same file name, same interface, same function names.
Just uses SMS instead of WhatsApp.
"""

import logging
import threading
import time
from typing import Optional, Dict
from datetime import datetime
from database.db_manager import db

logger = logging.getLogger(__name__)


class WhatsAppQueue:
    """
    Sends SMS via Twilio.
    Same interface as before - nothing else needs to change.
    """
    
    def __init__(self, config: Dict, simulation: bool = False):
        self.config = config
        self.simulation = simulation
        self.running = False
        self.thread: Optional[threading.Thread] = None
        
        twilio_config = config.get('twilio', {})
        self.account_sid = twilio_config.get('account_sid', '')
        self.auth_token = twilio_config.get('auth_token', '')
        self.from_number = twilio_config.get('from_number', '')
        self.enabled = twilio_config.get('enabled', False)
        
        self.client = None
        
        if not simulation and self.enabled and self.account_sid and self.auth_token:
            try:
                from twilio.rest import Client
                self.client = Client(self.account_sid, self.auth_token)
                logger.info("Twilio SMS client initialized successfully!")
            except ImportError:
                logger.error("Twilio not installed! Run: pip install twilio")
                self.simulation = True
            except Exception as e:
                logger.error(f"Twilio init failed: {e}")
                self.simulation = True
        else:
            logger.info("SMS in SIMULATION mode - printing to console")
    
    def enqueue(self, phone: str, message: str, language: str = 'en',
                template_name: Optional[str] = None, priority: int = 5) -> int:
        """Add SMS to queue - same interface as before."""
        try:
            msg_id = db.insert('whatsapp_queue', {
                'recipient_phone': phone,
                'message': message,
                'language': language,
                'template_name': template_name,
                'priority': priority,
                'status': 'pending'
            })
            logger.info(f"SMS queued for {phone} (ID: {msg_id})")
            return msg_id
        except Exception as e:
            logger.error(f"Failed to queue SMS: {e}")
            return -1
    
    def start(self):
        """Start background queue processor."""
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._process_queue, daemon=True)
        self.thread.start()
        logger.info("SMS queue started")
    
    def stop(self):
        """Stop background queue processor."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("SMS queue stopped")
    
    def _process_queue(self):
        """Process pending SMS from queue."""
        while self.running:
            try:
                pending = db.fetchall(
                    """
                    SELECT * FROM whatsapp_queue
                    WHERE status = 'pending' AND attempts < 3
                    ORDER BY priority DESC, created_at ASC
                    LIMIT 5
                    """
                )
                
                for msg in pending:
                    success = self._send_sms(
                        msg['recipient_phone'],
                        msg['message']
                    )
                    
                    if success:
                        db.update(
                            'whatsapp_queue',
                            {
                                'status': 'sent' if not self.simulation else 'simulated',
                                'sent_at': datetime.now().isoformat()
                            },
                            'id = ?',
                            (msg['id'],)
                        )
                    else:
                        new_attempts = msg['attempts'] + 1
                        db.update(
                            'whatsapp_queue',
                            {
                                'attempts': new_attempts,
                                'status': 'failed' if new_attempts >= 3 else 'pending',
                                'error': 'SMS send failed'
                            },
                            'id = ?',
                            (msg['id'],)
                        )
                
                time.sleep(5)
            
            except Exception as e:
                logger.error(f"Queue processing error: {e}")
                time.sleep(10)
    
    def _send_sms(self, to_number: str, message: str) -> bool:
        """Send a single SMS."""
        to_number = self._format_number(to_number)
        
        if self.simulation or not self.client:
            print(f"\n{'='*60}")
            print(f"SMS (SIMULATION)")
            print(f"To: {to_number}")
            print(f"From: {self.from_number}")
            print(f"{'='*60}")
            print(message)
            print(f"{'='*60}\n")
            logger.info(f"[SIM] SMS to {to_number}")
            return True
        
        try:
            msg = self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=to_number
            )
            logger.info(f"SMS sent to {to_number} | SID: {msg.sid} | Status: {msg.status}")
            return True
        except Exception as e:
            logger.error(f"SMS failed to {to_number}: {e}")
            return False
    
    def _format_number(self, phone: str) -> str:
        """Format phone number with India country code."""
        phone = phone.strip().replace(' ', '').replace('-', '')
        
        if phone.startswith('+'):
            return phone
        if phone.startswith('91') and len(phone) == 12:
            return f"+{phone}"
        if len(phone) == 10:
            return f"+91{phone}"
        
        return phone
    
    def get_stats(self) -> Dict[str, int]:
        """Get queue statistics."""
        stats = {}
        for status in ['pending', 'sent', 'failed', 'simulated']:
            row = db.fetchone(
                "SELECT COUNT(*) as count FROM whatsapp_queue WHERE status = ?",
                (status,)
            )
            stats[status] = row['count'] if row else 0
        return stats


# Global instance
whatsapp_queue: Optional[WhatsAppQueue] = None


def init_whatsapp(config: Dict, simulation: bool = False) -> WhatsAppQueue:
    """Initialize global SMS queue - same function name."""
    global whatsapp_queue
    whatsapp_queue = WhatsAppQueue(config, simulation)
    whatsapp_queue.start()
    return whatsapp_queue


def get_whatsapp() -> WhatsAppQueue:
    """Get global SMS queue - same function name."""
    if whatsapp_queue is None:
        raise RuntimeError("SMS queue not initialized")
    return whatsapp_queue