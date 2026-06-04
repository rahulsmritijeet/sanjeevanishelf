"""
WhatsApp Queue Manager
Handles queuing, sending, and retry logic for WhatsApp messages.
"""

import logging
import time
import threading
from typing import Optional, Dict, Any
from datetime import datetime
from database.db_manager import db

logger = logging.getLogger(__name__)


class WhatsAppQueue:
    """Background queue processor for WhatsApp messages."""
    
    def __init__(self, config: Dict, simulation: bool = False):
        self.config = config
        self.simulation = simulation
        self.running = False
        self.thread: Optional[threading.Thread] = None
        
        self.mode = config.get('whatsapp', {}).get('mode', 'simulation')
        self.sender_number = config.get('whatsapp', {}).get('sender_number', '')
        
        # Initialize sender based on mode
        if self.mode == 'pywhatkit' and not simulation:
            try:
                import pywhatkit
                self.pywhatkit = pywhatkit
                logger.info("WhatsApp using pywhatkit (requires WhatsApp Web login)")
            except ImportError:
                logger.warning("pywhatkit not installed, falling back to simulation")
                self.mode = 'simulation'
        elif self.mode == 'cloud_api' and not simulation:
            # Future: Implement cloud API (e.g., Twilio, MessageBird)
            logger.warning("Cloud API not implemented, falling back to simulation")
            self.mode = 'simulation'
        else:
            self.mode = 'simulation'
    
    def enqueue(self, phone: str, message: str, language: str = 'en',
                template_name: Optional[str] = None, priority: int = 5) -> int:
        """Add a message to the queue."""
        try:
            msg_id = db.insert('whatsapp_queue', {
                'recipient_phone': phone,
                'message': message,
                'language': language,
                'template_name': template_name,
                'priority': priority,
                'status': 'pending'
            })
            logger.info(f"Message queued for {phone} (ID: {msg_id})")
            return msg_id
        except Exception as e:
            logger.error(f"Failed to enqueue message: {e}")
            return -1
    
    def start(self):
        """Start background queue processor."""
        if self.running:
            logger.warning("WhatsApp queue already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._process_queue, daemon=True)
        self.thread.start()
        logger.info("WhatsApp queue started")
    
    def stop(self):
        """Stop background queue processor."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("WhatsApp queue stopped")
    
    def _process_queue(self):
        """Background thread to process pending messages."""
        while self.running:
            try:
                # Get pending messages (highest priority first)
                pending = db.fetchall(
                    """
                    SELECT * FROM whatsapp_queue
                    WHERE status = 'pending' AND attempts < 3
                    ORDER BY priority DESC, created_at ASC
                    LIMIT 10
                    """
                )
                
                for msg in pending:
                    success = self._send_message(dict(msg))
                    
                    if success:
                        db.update(
                            'whatsapp_queue',
                            {
                                'status': 'sent' if self.mode != 'simulation' else 'simulated',
                                'sent_at': datetime.now().isoformat()
                            },
                            'id = ?',
                            (msg['id'],)
                        )
                    else:
                        db.update(
                            'whatsapp_queue',
                            {
                                'attempts': msg['attempts'] + 1,
                                'status': 'failed' if msg['attempts'] + 1 >= 3 else 'pending',
                                'error': 'Send failed'
                            },
                            'id = ?',
                            (msg['id'],)
                        )
                
                # Sleep between batches
                time.sleep(5)
            
            except Exception as e:
                logger.error(f"Queue processing error: {e}")
                time.sleep(10)
    
    def _send_message(self, msg: Dict) -> bool:
        """Send a single message."""
        phone = msg['recipient_phone']
        text = msg['message']
        
        try:
            if self.mode == 'simulation':
                # Simulation mode: just log
                logger.info(f"[SIM] WhatsApp to {phone}:{text}")
                print(f"{'='*60}")
                print(f"WHATSAPP MESSAGE (SIMULATION)")
                print(f"To: {phone}")
                print(f"{'='*60}")
                print(text)
                print(f"{'='*60}")
                return True
            
            elif self.mode == 'pywhatkit':
                # Use pywhatkit (requires WhatsApp Web to be logged in on the Pi)
                import pywhatkit
                pywhatkit.sendwhatmsg_instantly(
                    phone_no=phone,
                    message=text,
                    wait_time=10,
                    tab_close=True
                )
                logger.info(f"Message sent via pywhatkit to {phone}")
                return True
            
            elif self.mode == 'cloud_api':
                # Future: Implement cloud API
                logger.warning("Cloud API not implemented")
                return False
            
            else:
                logger.error(f"Unknown WhatsApp mode: {self.mode}")
                return False
        
        except Exception as e:
            logger.error(f"Failed to send message to {phone}: {e}")
            return False
    
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


# Global singleton
whatsapp_queue: Optional[WhatsAppQueue] = None


def init_whatsapp(config: Dict, simulation: bool = False):
    """Initialize global WhatsApp queue."""
    global whatsapp_queue
    whatsapp_queue = WhatsAppQueue(config, simulation)
    whatsapp_queue.start()
    return whatsapp_queue


def get_whatsapp() -> WhatsAppQueue:
    """Get global WhatsApp queue instance."""
    if whatsapp_queue is None:
        raise RuntimeError("WhatsApp queue not initialized")
    return whatsapp_queue