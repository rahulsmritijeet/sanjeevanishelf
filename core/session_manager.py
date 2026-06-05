"""
Session Management with 5-Minute Auto-Timeout
"""

import logging
import json
import uuid
import threading
import time
from typing import Dict, Optional, Any, Callable
from datetime import datetime, timedelta
from database.db_manager import db

logger = logging.getLogger(__name__)


class SessionManager:
    """Manage transactional sessions with 5-minute auto-timeout."""
    
    _timeout_seconds = 300  # 5 minutes
    
    # Callback for UI notification on timeout
    on_timeout_callback = None
    
    def __init__(self, operator_id: int, mode: str):
        self.session_id = str(uuid.uuid4())
        self.operator_id = operator_id
        self.mode = mode
        self.snapshot = {}
        self.changes = []
        self.started = False
        self._timer_thread = None
        self._cancelled = False
        self._committed = False
        self._start_time = None
        
        logger.info(f"Session created: {self.session_id} (mode: {mode})")
    
    def start(self, farmer_id: Optional[int] = None):
        """Start session with 5-minute timer."""
        try:
            db.insert('sessions', {
                'session_id': self.session_id,
                'operator_id': self.operator_id,
                'mode': self.mode,
                'farmer_id': farmer_id,
                'status': 'open',
                'snapshot_data': json.dumps(self.snapshot)
            })
            self.started = True
            self._start_time = datetime.now()
            self._cancelled = False
            self._committed = False
            
            # Start timeout thread
            self._timer_thread = threading.Thread(target=self._timeout_watcher, daemon=True)
            self._timer_thread.start()
            
            logger.info(f"Session started: {self.session_id} (5-min timer)")
        except Exception as e:
            logger.error(f"Failed to start session: {e}")
            raise
    
    def _timeout_watcher(self):
        """Auto-cancel after 5 minutes."""
        elapsed = 0
        while elapsed < self._timeout_seconds:
            if self._cancelled or self._committed:
                return
            time.sleep(1)
            elapsed += 1
        
        if not self._cancelled and not self._committed and self.started:
            logger.warning(f"Session {self.session_id} TIMED OUT")
            try:
                db.update(
                    'sessions',
                    {
                        'status': 'timed_out',
                        'ended_at': datetime.now().isoformat()
                    },
                    'session_id = ?',
                    (self.session_id,)
                )
            except Exception as e:
                logger.error(f"Timeout update failed: {e}")
    
    def get_remaining_time(self) -> int:
        """Get remaining seconds."""
        if not self._start_time:
            return self._timeout_seconds
        
        elapsed = (datetime.now() - self._start_time).total_seconds()
        remaining = max(0, int(self._timeout_seconds - elapsed))
        return remaining
    
    def get_time_display(self) -> str:
        """Get MM:SS format."""
        remaining = self.get_remaining_time()
        minutes = remaining // 60
        seconds = remaining % 60
        return f"{minutes:02d}:{seconds:02d}"
    
    def is_expired(self) -> bool:
        """Check if session expired."""
        return self.get_remaining_time() <= 0
    
    def is_active(self) -> bool:
        """Check if session is still active."""
        return self.started and not self._cancelled and not self._committed and not self.is_expired()
    
    def cancel(self):
        """Cancel session manually."""
        logger.info(f"Session {self.session_id} cancelled by user")
        self._cancelled = True
        self.started = False
        
        try:
            db.update(
                'sessions',
                {
                    'status': 'cancelled',
                    'ended_at': datetime.now().isoformat()
                },
                'session_id = ?',
                (self.session_id,)
            )
        except Exception as e:
            logger.error(f"Cancel update failed: {e}")
    
    def commit(self):
        """Commit session successfully."""
        try:
            self._committed = True
            self._cancelled = True  # Stop timer
            self.started = False
            
            db.update(
                'sessions',
                {
                    'status': 'committed',
                    'ended_at': datetime.now().isoformat()
                },
                'session_id = ?',
                (self.session_id,)
            )
            logger.info(f"Session committed: {self.session_id}")
        except Exception as e:
            logger.error(f"Failed to commit session: {e}")
            raise
    
    def rollback(self):
        """Rollback all changes."""
        logger.warning(f"Rolling back session: {self.session_id}")
        
        try:
            self._cancelled = True
            self.started = False
            
            for change in reversed(self.changes):
                self._revert_change(change)
            
            db.update(
                'sessions',
                {
                    'status': 'rolled_back',
                    'ended_at': datetime.now().isoformat()
                },
                'session_id = ?',
                (self.session_id,)
            )
            
            logger.info(f"Session rolled back: {self.session_id}")
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
    
    def snapshot_entity(self, entity_type: str, entity_id: int, data: Dict):
        """Take snapshot for rollback."""
        key = f"{entity_type}:{entity_id}"
        self.snapshot[key] = data
        
        try:
            db.update(
                'sessions',
                {'snapshot_data': json.dumps(self.snapshot)},
                'session_id = ?',
                (self.session_id,)
            )
        except:
            pass
    
    def log_change(self, event_type: str, entity_type: str, entity_id: int,
                   old_value: Any, new_value: Any):
        """Log a change for audit."""
        change = {
            'event_type': event_type,
            'entity_type': entity_type,
            'entity_id': entity_id,
            'old_value': json.dumps(old_value) if not isinstance(old_value, str) else old_value,
            'new_value': json.dumps(new_value) if not isinstance(new_value, str) else new_value,
            'timestamp': datetime.now().isoformat()
        }
        self.changes.append(change)
        
        try:
            db.log_event(
                session_id=self.session_id,
                event_type=event_type,
                entity_type=entity_type,
                entity_id=entity_id,
                old_value=change['old_value'],
                new_value=change['new_value'],
                operator_id=self.operator_id
            )
        except:
            pass
    
    def _revert_change(self, change: Dict):
        """Revert a single change."""
        entity_type = change['entity_type']
        entity_id = change['entity_id']
        old_value = change['old_value']
        
        try:
            old_data = json.loads(old_value) if old_value else {}
        except:
            old_data = {}
        
        try:
            if entity_type == 'batch':
                db.update('batches', old_data, 'id = ?', (entity_id,))
            elif entity_type == 'transaction':
                db.update('transactions', old_data, 'id = ?', (entity_id,))
            elif entity_type == 'rfid_tag':
                db.update('rfid_tags', old_data, 'uid = ?', (entity_id,))
            elif entity_type == 'crop_capacity':
                db.update('crop_capacity', old_data, 'crop_type = ?', (entity_id,))
        except Exception as e:
            logger.error(f"Revert failed for {entity_type}:{entity_id}: {e}")
    
    @staticmethod
    def recover_open_sessions() -> list:
        """Find and recover open sessions."""
        try:
            open_sessions = db.get_open_sessions()
            
            if open_sessions:
                logger.warning(f"Found {len(open_sessions)} open sessions")
                for session in open_sessions:
                    try:
                        db.update(
                            'sessions',
                            {
                                'status': 'recovered',
                                'ended_at': datetime.now().isoformat()
                            },
                            'session_id = ?',
                            (session['session_id'],)
                        )
                    except:
                        pass
            
            return open_sessions
        except:
            return []
    
    @staticmethod
    def force_rollback_session(session_id: str):
        """Force rollback a specific session."""
        try:
            db.update(
                'sessions',
                {
                    'status': 'force_rolled_back',
                    'ended_at': datetime.now().isoformat()
                },
                'session_id = ?',
                (session_id,)
            )
            logger.info(f"Force rolled back session: {session_id}")
        except Exception as e:
            logger.error(f"Force rollback failed: {e}")