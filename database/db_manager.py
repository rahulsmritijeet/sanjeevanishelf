"""
Database Manager for Sanjeevani Shelf v1.1
Fixed: No more "index already exists" errors.
"""

import sqlite3
import os
import logging
from datetime import datetime
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, List, Dict, Any
import threading

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Singleton database manager."""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, db_path: str = "data/godown.db"):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, db_path: str = "data/godown.db"):
        if self._initialized:
            return
        
        self.db_path = db_path
        self._local = threading.local()
        self._initialized = True
        
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_database()
        
        logger.info(f"DatabaseManager initialized with {db_path}")
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local connection."""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            self._local.connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=30.0
            )
            self._local.connection.row_factory = sqlite3.Row
            self._local.connection.execute("PRAGMA foreign_keys = ON")
            self._local.connection.execute("PRAGMA journal_mode = WAL")
        return self._local.connection
    
    def _init_database(self):
        """Initialize database schema safely."""
        schema_path = Path(__file__).parent / "schema.sql"
        
        if not schema_path.exists():
            logger.warning(f"Schema file not found at {schema_path}")
            return
        
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        
        conn = self._get_connection()
        try:
            # Execute each statement separately to handle errors gracefully
            statements = schema_sql.split(';')
            
            for statement in statements:
                statement = statement.strip()
                if not statement:
                    continue
                
                try:
                    conn.execute(statement)
                except sqlite3.OperationalError as e:
                    error_msg = str(e).lower()
                    # Skip "already exists" errors - these are fine
                    if 'already exists' in error_msg:
                        continue
                    # Skip "duplicate column" errors
                    elif 'duplicate column' in error_msg:
                        continue
                    else:
                        logger.error(f"SQL error: {e}")
                        logger.error(f"Statement: {statement[:100]}...")
                except sqlite3.IntegrityError as e:
                    # Skip duplicate insert errors (INSERT OR IGNORE handles this)
                    if 'UNIQUE constraint' in str(e):
                        continue
                    else:
                        logger.error(f"Integrity error: {e}")
            
            conn.commit()
            logger.info("Database schema initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            conn.rollback()
    
    @contextmanager
    def transaction(self):
        """Context manager for transactions."""
        conn = self._get_connection()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Transaction rolled back: {e}")
            raise
    
    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute a single query."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor
        except Exception as e:
            conn.rollback()
            logger.error(f"Query failed: {query[:100]}... Error: {e}")
            raise
    
    def fetchone(self, query: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        """Fetch one result."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchone()
    
    def fetchall(self, query: str, params: tuple = ()) -> List[sqlite3.Row]:
        """Fetch all results."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()
    
    def insert(self, table: str, data: Dict[str, Any]) -> int:
        """Insert a row."""
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data])
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        cursor = self.execute(query, tuple(data.values()))
        return cursor.lastrowid
    
    def update(self, table: str, data: Dict[str, Any], where: str, where_params: tuple = ()) -> int:
        """Update rows."""
        set_clause = ', '.join([f"{k} = ?" for k in data.keys()])
        query = f"UPDATE {table} SET {set_clause} WHERE {where}"
        params = tuple(data.values()) + where_params
        cursor = self.execute(query, params)
        return cursor.rowcount
    
    def delete(self, table: str, where: str, where_params: tuple = ()) -> int:
        """Delete rows."""
        query = f"DELETE FROM {table} WHERE {where}"
        cursor = self.execute(query, where_params)
        return cursor.rowcount
    
    def close(self):
        """Close connection."""
        if hasattr(self._local, 'connection') and self._local.connection:
            self._local.connection.close()
            self._local.connection = None
            logger.info("Database connection closed")
    
    def get_farmer_by_phone(self, phone: str) -> Optional[Dict]:
        """Get farmer by phone."""
        row = self.fetchone("SELECT * FROM farmers WHERE phone = ?", (phone,))
        return dict(row) if row else None
    
    def get_batch_by_rfid(self, rfid_uid: str) -> Optional[Dict]:
        """Get batch by RFID."""
        query = """
        SELECT b.*, f.name as farmer_name, f.phone as farmer_phone
        FROM batches b
        JOIN farmers f ON b.farmer_id = f.id
        WHERE b.rfid_uid = ? AND b.status = 'stored'
        """
        row = self.fetchone(query, (rfid_uid,))
        return dict(row) if row else None
    
    def get_available_rfid(self) -> Optional[str]:
        """Get available RFID tag."""
        row = self.fetchone("SELECT uid FROM rfid_tags WHERE status = 'available' LIMIT 1")
        return row['uid'] if row else None
    
    def get_crop_stock(self, crop_type: str) -> float:
        """Get crop stock."""
        row = self.fetchone("SELECT current_stock_kg FROM crop_capacity WHERE crop_type = ?", (crop_type,))
        return row['current_stock_kg'] if row else 0.0
    
    def update_crop_stock(self, crop_type: str, delta_kg: float):
        """Update crop stock."""
        self.execute(
            "UPDATE crop_capacity SET current_stock_kg = current_stock_kg + ? WHERE crop_type = ?",
            (delta_kg, crop_type)
        )
    
    def log_event(self, session_id, event_type, entity_type, entity_id,
                  old_value, new_value, operator_id):
        """Log audit event."""
        self.insert('event_log', {
            'session_id': session_id,
            'event_type': event_type,
            'entity_type': entity_type,
            'entity_id': entity_id,
            'old_value': old_value,
            'new_value': new_value,
            'operator_id': operator_id
        })
    
    def get_open_sessions(self) -> List[Dict]:
        """Get open sessions."""
        rows = self.fetchall(
            """
            SELECT s.*, u.username, u.full_name
            FROM sessions s
            JOIN users u ON s.operator_id = u.id
            WHERE s.status = 'open'
            ORDER BY s.started_at DESC
            """
        )
        return [dict(row) for row in rows]
    
    def vacuum(self):
        """Vacuum database."""
        conn = self._get_connection()
        conn.execute("VACUUM")
        logger.info("Database vacuumed")


db = DatabaseManager()