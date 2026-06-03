"""
Database Migrations
Version tracking and schema upgrades.
"""

import logging
from .db_manager import db

logger = logging.getLogger(__name__)

CURRENT_VERSION = 1


def get_db_version() -> int:
    """Get current database version."""
    try:
        # Create version table if not exists
        db.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        row = db.fetchone("SELECT MAX(version) as version FROM schema_version")
        return row['version'] if row and row['version'] else 0
    except Exception as e:
        logger.error(f"Error getting database version: {e}")
        return 0


def apply_migrations():
    """Apply pending migrations."""
    current = get_db_version()
    
    if current >= CURRENT_VERSION:
        logger.info(f"Database is up to date (version {current})")
        return
    
    logger.info(f"Applying migrations from version {current} to {CURRENT_VERSION}")
    
    # Migration v1: Initial schema (already applied via schema.sql)
    if current < 1:
        logger.info("Migration v1 already applied via schema.sql")
        db.insert('schema_version', {'version': 1})
        current = 1
    
    # Future migrations go here
    # if current < 2:
    #     apply_migration_v2()
    #     db.insert('schema_version', {'version': 2})
    #     current = 2
    
    logger.info(f"Migrations complete. Database version: {current}")


def apply_migration_v2():
    """Example future migration."""
    # Add new column, table, index, etc.
    pass