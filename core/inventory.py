"""
Inventory Management
Handles stock tracking, capacity checks, and FIFO allocation.
"""

import logging
from typing import Optional, List, Dict, Tuple
from datetime import datetime, timedelta
from database.db_manager import db

logger = logging.getLogger(__name__)


class InventoryManager:
    """Manage godown inventory with capacity checks and FIFO."""
    
    def __init__(self, config: Dict):
        self.config = config
        self.total_capacity = config.get('capacity', {}).get('total', 100000)
        self.crop_capacities = config.get('capacity', {}).get('per_crop', {})
    
    def check_capacity(self, crop_type: str, weight_kg: float) -> Tuple[bool, str]:
        """
        Check if adding weight is within capacity.
        Returns (ok: bool, message: str)
        """
        # Check total capacity
        total_stock = self.get_total_stock()
        if total_stock + weight_kg > self.total_capacity:
            return False, f"Total capacity exceeded. Available: {self.total_capacity - total_stock:.2f} kg"
        
        # Check crop-specific capacity
        crop_capacity = self.crop_capacities.get(crop_type, 0)
        crop_stock = db.get_crop_stock(crop_type)
        
        if crop_stock + weight_kg > crop_capacity:
            return False, f"{crop_type.title()} capacity exceeded. Available: {crop_capacity - crop_stock:.2f} kg"
        
        return True, "Capacity OK"
    
    def get_total_stock(self) -> float:
        """Get total current stock across all crops."""
        row = db.fetchone(
            "SELECT SUM(current_stock_kg) as total FROM crop_capacity"
        )
        return row['total'] if row and row['total'] else 0.0
    
    def get_crop_stock(self, crop_type: str) -> float:
        """Get current stock for a crop."""
        return db.get_crop_stock(crop_type)
    
    def get_stock_summary(self) -> List[Dict]:
        """Get stock summary for all crops."""
        rows = db.fetchall(
            """
            SELECT 
                crop_type,
                allocated_capacity_kg,
                current_stock_kg,
                (allocated_capacity_kg - current_stock_kg) as available_kg,
                ROUND((current_stock_kg * 100.0 / allocated_capacity_kg), 2) as utilization_percent
            FROM crop_capacity
            ORDER BY crop_type
            """
        )
        return [dict(row) for row in rows]
    
    def allocate_stack(self, crop_type: str, weight_kg: float) -> Optional[str]:
        """
        Allocate a stack location for storage.
        Returns stack_location code or None if full.
        """
        row = db.fetchone(
            """
            SELECT location_code, capacity_kg, current_weight_kg
            FROM stack_locations
            WHERE crop_type = ? AND status = 'available'
              AND (capacity_kg - current_weight_kg) >= ?
            ORDER BY current_weight_kg ASC
            LIMIT 1
            """,
            (crop_type, weight_kg)
        )
        
        if not row:
            logger.warning(f"No available stack for {crop_type}, {weight_kg} kg")
            return None
        
        return row['location_code']
    
    def update_stack_weight(self, location_code: str, delta_kg: float):
        """Update stack weight (positive = add, negative = remove)."""
        db.execute(
            """
            UPDATE stack_locations
            SET current_weight_kg = current_weight_kg + ?,
                status = CASE 
                    WHEN (current_weight_kg + ?) >= capacity_kg THEN 'full'
                    ELSE 'available'
                END
            WHERE location_code = ?
            """,
            (delta_kg, delta_kg, location_code)
        )
    
    def find_batches_for_withdrawal(self, crop_type: str, required_kg: float,
                                    farmer_id: Optional[int] = None) -> List[Dict]:
        """
        Find batches for withdrawal/selling using FIFO + expiry priority.
        If farmer_id given, only return that farmer's batches.
        """
        query = """
        SELECT *
        FROM batches
        WHERE crop_type = ? AND status = 'stored'
        """
        params = [crop_type]
        
        if farmer_id:
            query += " AND farmer_id = ?"
            params.append(farmer_id)
        
        query += " ORDER BY expiry_date ASC, storage_date ASC"
        
        rows = db.fetchall(query, tuple(params))
        batches = [dict(row) for row in rows]
        
        # Select batches until we have enough weight
        selected = []
        total_weight = 0.0
        
        for batch in batches:
            selected.append(batch)
            total_weight += batch['weight_kg']
            if total_weight >= required_kg:
                break
        
        return selected
    
    def get_expiring_batches(self, days_threshold: int = 7) -> List[Dict]:
        """Get batches expiring within threshold days."""
        threshold_date = (datetime.now() + timedelta(days=days_threshold)).date()
        
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
        
        return [dict(row) for row in rows]
    
    def confiscate_expired(self) -> int:
        """
        Confiscate all expired batches.
        Returns number of batches confiscated.
        """
        today = datetime.now().date()
        
        expired = db.fetchall(
            """
            SELECT id, weight_kg, crop_type, stack_location
            FROM batches
            WHERE status = 'stored' AND expiry_date < ?
            """,
            (today.isoformat(),)
        )
        
        count = 0
        for batch in expired:
            db.update(
                'batches',
                {
                    'status': 'confiscated',
                    'confiscation_reason': 'Expired',
                    'confiscation_date': today.isoformat()
                },
                'id = ?',
                (batch['id'],)
            )
            
            # Update stock
            db.update_crop_stock(batch['crop_type'], -batch['weight_kg'])
            
            # Update stack
            if batch['stack_location']:
                self.update_stack_weight(batch['stack_location'], -batch['weight_kg'])
            
            count += 1
        
        logger.info(f"Confiscated {count} expired batches")
        return count