"""
Session Management with Rollback/Recovery
Handles transactional sessions with full rollback capability.
"""

import logging
import json
import uuid
from typing import Dict, Optional, Any
from datetime import datetime
from database.db_manager import db

logger = logging.getLogger(__name__)


class SessionManager:
    """Manage transactional sessions with rollback support."""
    
    def __init__(self, operator_id: int, mode: str):
        self.session_id = str(uuid.uuid4())
        self.operator_id = operator_id
        self.mode = mode  # storage, selling, buying
        self.snapshot = {}
        self.changes = []
        self.started = False
        
        logger.info(f"Session created: {self.session_id} (mode: {mode}, operator: {operator_id})")
    
    def start(self, farmer_id: Optional[int] = None):
        """Start a new session and create DB record."""
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
            logger.info(f"Session started: {self.session_id}")
        except Exception as e:
            logger.error(f"Failed to start session: {e}")
            raise
    
    def snapshot_entity(self, entity_type: str, entity_id: int, data: Dict):
        """Take snapshot of entity state for potential rollback."""
        key = f"{entity_type}:{entity_id}"
        self.snapshot[key] = data
        
        # Update session snapshot in DB
        db.update(
            'sessions',
            {'snapshot_data': json.dumps(self.snapshot)},
            'session_id = ?',
            (self.session_id,)
        )
    
    def log_change(self, event_type: str, entity_type: str, entity_id: int,
                   old_value: Any, new_value: Any):
        """Log a change event for audit trail."""
        change = {
            'event_type': event_type,
            'entity_type': entity_type,
            'entity_id': entity_id,
            'old_value': json.dumps(old_value) if not isinstance(old_value, str) else old_value,
            'new_value': json.dumps(new_value) if not isinstance(new_value, str) else new_value,
            'timestamp': datetime.now().isoformat()
        }
        self.changes.append(change)
        
        # Log to database
        db.log_event(
            session_id=self.session_id,
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            old_value=change['old_value'],
            new_value=change['new_value'],
            operator_id=self.operator_id
        )
    
    def commit(self):
        """Commit the session (mark as successful)."""
        try:
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
        """
        Rollback all changes made in this session.
        Restores entities to snapshot state.
        """
        logger.warning(f"Rolling back session: {self.session_id}")
        
        try:
            # Reverse changes in reverse order
            for change in reversed(self.changes):
                self._revert_change(change)
            
            # Mark session as rolled back
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
            raise
    
    def _revert_change(self, change: Dict):
        """Revert a single change."""
        entity_type = change['entity_type']
        entity_id = change['entity_id']
        old_value = change['old_value']
        
        # Parse old_value
        try:
            old_data = json.loads(old_value) if old_value else {}
        except:
            old_data = {}
        
        # Revert based on entity type
        if entity_type == 'batch':
            db.update('batches', old_data, 'id = ?', (entity_id,))
        elif entity_type == 'transaction':
            db.update('transactions', old_data, 'id = ?', (entity_id,))
        elif entity_type == 'rfid_tag':
            db.update('rfid_tags', old_data, 'uid = ?', (entity_id,))
        elif entity_type == 'crop_capacity':
            db.update('crop_capacity', old_data, 'crop_type = ?', (entity_id,))
        
        logger.debug(f"Reverted {entity_type}:{entity_id}")
    
    @staticmethod
    def recover_open_sessions() -> list:
        """Find and recover any open sessions (e.g., after crash)."""
        open_sessions = db.get_open_sessions()
        
        if open_sessions:
            logger.warning(f"Found {len(open_sessions)} open sessions for recovery")
        
        return open_sessions
    
    @staticmethod
    def force_rollback_session(session_id: str):
        """Force rollback of a specific session."""
        session_data = db.fetchone(
            "SELECT * FROM sessions WHERE session_id = ?",
            (session_id,)
        )
        
        if not session_data:
            logger.error(f"Session not found: {session_id}")
            return
        
        # Load changes from event log
        changes = db.fetchall(
            """
            SELECT * FROM event_log
            WHERE session_id = ?
            ORDER BY occurred_at DESC
            """,
            (session_id,)
        )
        
        # Create temp session manager to perform rollback
        temp_session = SessionManager(
            operator_id=session_data['operator_id'],
            mode=session_data['mode']
        )
        temp_session.session_id = session_id
        temp_session.changes = [dict(c) for c in changes]
        temp_session.rollback()