"""
Hardware Manager - Unified interface for all hardware components
"""

import logging
from typing import Optional, List, Dict
from .rfid_handler import RFIDHandler
from .weight_handler import WeightHandler
from .moisture_handler import MoistureHandler

logger = logging.getLogger(__name__)


class HardwareManager:
    """Centralized hardware management with health monitoring."""
    
    def __init__(self, config: Dict, simulation: bool = False):
        self.config = config
        self.simulation = simulation
        self.health = {}
        
        # Initialize handlers
        try:
            bt_config = config.get('bluetooth', {})
            
            self.rfid = RFIDHandler(
                port=bt_config.get('rfid_port', '/dev/rfcomm0'),
                baud_rate=bt_config.get('baud_rate', 9600),
                timeout=bt_config.get('timeout', 5),
                simulation=simulation
            )
            self.health['rfid'] = 'ok'
        except Exception as e:
            logger.error(f"Failed to initialize RFID: {e}")
            self.rfid = None
            self.health['rfid'] = 'error'
        
        try:
            self.weight = WeightHandler(
                port=bt_config.get('weight_port', '/dev/rfcomm1'),
                baud_rate=bt_config.get('baud_rate', 9600),
                timeout=bt_config.get('timeout', 5),
                simulation=simulation
            )
            self.health['weight'] = 'ok'
        except Exception as e:
            logger.error(f"Failed to initialize Weight: {e}")
            self.weight = None
            self.health['weight'] = 'error'
        
        try:
            self.moisture = MoistureHandler(
                port=bt_config.get('moisture_port', '/dev/rfcomm2'),
                baud_rate=bt_config.get('baud_rate', 9600),
                timeout=bt_config.get('timeout', 5),
                simulation=simulation
            )
            self.health['moisture'] = 'ok'
        except Exception as e:
            logger.error(f"Failed to initialize Moisture: {e}")
            self.moisture = None
            self.health['moisture'] = 'error'
        
        logger.info(f"HardwareManager initialized. Health: {self.health}")
    
    def get_health_status(self) -> Dict[str, str]:
        """Get health status of all hardware components."""
        return self.health.copy()
    
    def check_all_systems(self) -> bool:
        """Quick health check on all systems."""
        all_ok = all(status == 'ok' for status in self.health.values())
        if not all_ok:
            logger.warning(f"Hardware health check failed: {self.health}")
        return all_ok
    
    def close_all(self):
        """Close all hardware connections."""
        if self.rfid:
            self.rfid.close()
        if self.weight:
            self.weight.close()
        if self.moisture:
            self.moisture.close()
        logger.info("All hardware connections closed")


# Global singleton (initialized in app.py)
hardware_manager: Optional[HardwareManager] = None


def init_hardware(config: Dict, simulation: bool = False):
    """Initialize global hardware manager."""
    global hardware_manager
    hardware_manager = HardwareManager(config, simulation)
    return hardware_manager


def get_hardware() -> HardwareManager:
    """Get global hardware manager instance."""
    if hardware_manager is None:
        raise RuntimeError("Hardware manager not initialized. Call init_hardware() first.")
    return hardware_manager