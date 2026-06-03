"""
Stack Allocation and Space Optimization
FIFO, expiry-based allocation for efficient storage.
"""

import logging
from typing import List, Dict, Optional
from database.db_manager import db

logger = logging.getLogger(__name__)


class StackAllocator:
    """Allocate and manage physical stack locations."""
    
    def __init__(self):
        pass
    
    def find_best_stack(self, crop_type: str, weight_kg: float,
                       strategy: str = 'first_fit') -> Optional[str]:
        """
        Find best stack location for storage.
        Strategies: first_fit, best_fit, worst_fit
        """
        available_stacks = db.fetchall(
            """
            SELECT location_code, capacity_kg, current_weight_kg,
                   (capacity_kg - current_weight_kg) as available_kg
            FROM stack_locations
            WHERE crop_type = ? AND status = 'available'
              AND (capacity_kg - current_weight_kg) >= ?
            ORDER BY 
                CASE ?
                    WHEN 'first_fit' THEN location_code
                    WHEN 'best_fit' THEN (capacity_kg - current_weight_kg)
                    WHEN 'worst_fit' THEN (capacity_kg - current_weight_kg) * -1
                END
            """,
            (crop_type, weight_kg, strategy)
        )
        
        if not available_stacks:
            logger.warning(f"No available stack for {crop_type}, {weight_kg} kg")
            return None
        
        selected = available_stacks[0]
        logger.info(f"Allocated stack {selected['location_code']} for {weight_kg} kg of {crop_type}")
        return selected['location_code']
    
    def get_stack_utilization(self) -> List[Dict]:
        """Get utilization stats for all stacks."""
        rows = db.fetchall(
            """
            SELECT 
                location_code,
                crop_type,
                capacity_kg,
                current_weight_kg,
                ROUND((current_weight_kg * 100.0 / capacity_kg), 2) as utilization_percent,
                status
            FROM stack_locations
            ORDER BY crop_type, location_code
            """
        )
        return [dict(row) for row in rows]
    
    def optimize_stacks(self) -> int:
        """
        Optimize stack allocation by consolidating sparse stacks.
        Returns number of optimizations made.
        (Placeholder for future implementation)
        """
        # Future: Implement stack consolidation logic
        logger.info("Stack optimization not yet implemented")
        return 0
    
    def reserve_stack(self, location_code: str) -> bool:
        """Reserve a stack for maintenance."""
        try:
            db.update(
                'stack_locations',
                {'status': 'maintenance'},
                'location_code = ?',
                (location_code,)
            )
            logger.info(f"Stack {location_code} reserved for maintenance")
            return True
        except Exception as e:
            logger.error(f"Failed to reserve stack: {e}")
            return False
    
    def release_stack(self, location_code: str) -> bool:
        """Release a stack from maintenance."""
        try:
            # Determine new status based on weight
            row = db.fetchone(
                "SELECT capacity_kg, current_weight_kg FROM stack_locations WHERE location_code = ?",
                (location_code,)
            )
            
            if row:
                new_status = 'full' if row['current_weight_kg'] >= row['capacity_kg'] else 'available'
                db.update(
                    'stack_locations',
                    {'status': new_status},
                    'location_code = ?',
                    (location_code,)
                )
                logger.info(f"Stack {location_code} released, status: {new_status}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to release stack: {e}")
            return False