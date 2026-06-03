"""
Weight Handler for HX711 Load Cell via Arduino + HC-05 Bluetooth
Protocol: Arduino continuously sends "WEIGHT:<value_kg>" every 500ms
"""

import serial
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)


class WeightHandler:
    """Handle weight scale operations via Bluetooth serial."""
    
    def __init__(self, port: str = "/dev/rfcomm1", baud_rate: int = 9600,
                 timeout: int = 5, simulation: bool = False):
        self.port = port
        self.baud_rate = baud_rate
        self.timeout = timeout
        self.simulation = simulation
        self.serial: Optional[serial.Serial] = None
        
        if not simulation:
            self._connect()
    
    def _connect(self):
        """Connect to Arduino via Bluetooth."""
        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baud_rate,
                timeout=self.timeout
            )
            time.sleep(2)
            logger.info(f"Weight Handler connected to {self.port}")
        except Exception as e:
            logger.error(f"Failed to connect Weight handler: {e}")
            raise
    
    def tare(self) -> bool:
        """Send tare command to zero the scale."""
        if self.simulation:
            logger.info("[SIM] Weight scale tared")
            return True
        
        try:
            self.serial.write(b"TARE
")
            
            start = time.time()
            while time.time() - start < self.timeout:
                if self.serial.in_waiting > 0:
                    response = self.serial.readline().decode('utf-8').strip()
                    if response == "TARE_OK":
                        logger.info("Weight scale tared")
                        return True
                time.sleep(0.1)
            
            logger.error("Tare timeout")
            return False
        except Exception as e:
            logger.error(f"Tare error: {e}")
            return False
    
    def read_weight(self, samples: int = 5) -> Optional[float]:
        """
        Read weight with averaging over multiple samples.
        In simulation, prompts for manual input.
        """
        if self.simulation:
            return self._simulate_read()
        
        try:
            weights = []
            self.serial.flushInput()
            
            while len(weights) < samples:
                if self.serial.in_waiting > 0:
                    line = self.serial.readline().decode('utf-8').strip()
                    if line.startswith("WEIGHT:"):
                        try:
                            weight = float(line.split(":")[1])
                            weights.append(weight)
                        except ValueError:
                            continue
                time.sleep(0.1)
            
            avg_weight = sum(weights) / len(weights)
            logger.info(f"Weight reading: {avg_weight:.2f} kg (avg of {samples} samples)")
            return round(avg_weight, 2)
        except Exception as e:
            logger.error(f"Weight read error: {e}")
            return None
    
    def _simulate_read(self) -> float:
        """Simulate weight reading."""
        # In real UI, this would be an input popup
        # For testing, return a random weight
        import random
        weight = round(random.uniform(50, 500), 2)
        logger.info(f"[SIM] Weight reading: {weight} kg")
        return weight
    
    def close(self):
        """Close serial connection."""
        if self.serial and self.serial.is_open:
            self.serial.close()
            logger.info("Weight handler closed")


# Test function
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    handler = WeightHandler(simulation=True)
    handler.tare()
    weight = handler.read_weight()
    print(f"Weight: {weight} kg")
    handler.close()