"""
SMS Queue via Twilio
Same interface as WhatsApp queue.
"""

import logging
import threading
import time
from typing import Optional, Dict
from datetime import datetime
from database.db_manager import db

logger = logging.getLogger(__name__)


class WhatsAppQueue:
    """Sends SMS via Twilio."""
    
    def __init__(self, config: Dict, simulation: bool = False):
        self.config = config
        self.simulation = simulation
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.client = None
        self.enabled = False
        
        # Load Twilio config
        twilio_config = config.get('twilio', {})
        self.account_sid = twilio_config.get('account_sid', '').strip()
        self.auth_token  = twilio_config.get('auth_token', '').strip()
        self.from_number = twilio_config.get('from_number', '').strip()
        self.enabled     = twilio_config.get('enabled', False)
        
        # Debug: print what we loaded
        logger.info(f"Twilio config loaded:")
        logger.info(f"  account_sid: {self.account_sid[:10]}..." if self.account_sid else "  account_sid: EMPTY")
        logger.info(f"  auth_token:  {self.auth_token[:5]}..." if self.auth_token else "  auth_token: EMPTY")
        logger.info(f"  from_number: {self.from_number}")
        logger.info(f"  enabled:     {self.enabled}")
        logger.info(f"  simulation:  {simulation}")
        
        # Initialize Twilio client
        if not simulation and self.enabled:
            if not self.account_sid or self.account_sid.startswith('AC') is False:
                logger.error("Invalid Twilio Account SID - must start with 'AC'")
                self.simulation = True
            elif not self.auth_token:
                logger.error("Twilio Auth Token is empty")
                self.simulation = True
            elif not self.from_number:
                logger.error("Twilio From Number is empty")
                self.simulation = True
            else:
                try:
                    from twilio.rest import Client
                    self.client = Client(self.account_sid, self.auth_token)
                    
                    # Test connection
                    account = self.client.api.accounts(self.account_sid).fetch()
                    logger.info(f"Twilio connected: {account.friendly_name} ({account.status})")
                    self.simulation = False
                    
                except ImportError:
                    logger.error("Twilio not installed! Run: pip install twilio")
                    self.simulation = True
                except Exception as e:
                    logger.error(f"Twilio init failed: {e}")
                    self.simulation = True
        else:
            if simulation:
                logger.info("SMS: simulation mode (not sending real SMS)")
            elif not self.enabled:
                logger.info("SMS: disabled in config (twilio.enabled = false)")
            self.simulation = True
    
    def enqueue(self, phone: str, message: str, language: str = 'en',
                template_name: Optional[str] = None, priority: int = 5) -> int:
        """Add SMS to queue."""
        try:
            msg_id = db.insert('whatsapp_queue', {
                'recipient_phone': phone,
                'message': message,
                'language': language,
                'template_name': template_name,
                'priority': priority,
                'status': 'pending'
            })
            logger.info(f"SMS queued for {phone} (ID: {msg_id}, template: {template_name})")
            return msg_id
        except Exception as e:
            logger.error(f"Failed to queue SMS: {e}")
            return -1
    
    def send_now(self, phone: str, message: str) -> bool:
        """Send SMS immediately (bypass queue)."""
        return self._send_sms(phone, message)
    
    def _send_sms(self, to_number: str, message: str) -> bool:
        """Send a single SMS."""
        to_number = self._format_number(to_number)
        
        # Simulation mode
        if self.simulation or not self.client:
            print(f"\n{'='*60}")
            print(f"SMS (SIMULATION - NOT SENT FOR REAL)")
            print(f"To:   {to_number}")
            print(f"From: {self.from_number or 'Not configured'}")
            print(f"{'='*60}")
            print(message)
            print(f"{'='*60}\n")
            logger.info(f"[SIM] SMS to {to_number}")
            return True
        
        # Real SMS via Twilio
        try:
            logger.info(f"Sending SMS to {to_number}...")
            
            msg = self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=to_number
            )
            
            logger.info(f"SMS SENT to {to_number}")
            logger.info(f"  SID:    {msg.sid}")
            logger.info(f"  Status: {msg.status}")
            return True
        
        except Exception as e:
            logger.error(f"SMS FAILED to {to_number}: {e}")
            
            # Log specific Twilio errors
            error_str = str(e)
            if '21608' in error_str:
                logger.error("ERROR 21608: Recipient not verified!")
                logger.error("Go to: https://console.twilio.com/us1/develop/phone-numbers/manage/verified")
                logger.error("Add and verify the recipient phone number.")
            elif '20003' in error_str:
                logger.error("ERROR 20003: Authentication failed - check SID and token")
            elif '21211' in error_str:
                logger.error("ERROR 21211: Invalid To phone number")
            
            return False
    
    def _format_number(self, phone: str) -> str:
        """Format phone to E.164 format (+91XXXXXXXXXX)."""
        phone = phone.strip().replace(' ', '').replace('-', '')
        
        if phone.startswith('+'):
            return phone
        if phone.startswith('91') and len(phone) == 12:
            return f"+{phone}"
        if len(phone) == 10:
            return f"+91{phone}"
        
        return phone
    
    def start(self):
        """Start background queue processor."""
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._process_queue, daemon=True)
        self.thread.start()
        logger.info("SMS queue processor started")
    
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
                        logger.info(f"SMS queue item {msg['id']} processed successfully")
                    else:
                        new_attempts = msg['attempts'] + 1
                        db.update(
                            'whatsapp_queue',
                            {
                                'attempts': new_attempts,
                                'status': 'failed' if new_attempts >= 3 else 'pending',
                                'error': 'Send failed'
                            },
                            'id = ?',
                            (msg['id'],)
                        )
                        logger.warning(f"SMS queue item {msg['id']} failed (attempt {new_attempts})")
                
                time.sleep(5)
            
            except Exception as e:
                logger.error(f"Queue processing error: {e}")
                time.sleep(10)
    
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
    """Initialize global SMS queue."""
    global whatsapp_queue
    whatsapp_queue = WhatsAppQueue(config, simulation)
    whatsapp_queue.start()
    return whatsapp_queue


def get_whatsapp() -> WhatsAppQueue:
    """Get global SMS queue."""
    if whatsapp_queue is None:
        raise RuntimeError("SMS queue not initialized")
    return whatsapp_queue