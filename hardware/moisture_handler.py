"""
Moisture Handler for 4x Soil Moisture Sensors via Arduino + HC-05 Bluetooth
Protocol: Arduino sends "MOISTURE:<s1>,<s2>,<s3>,<s4>" on request
"""

import serial
import logging
import time
from typing import Optional, List

logger = logging.getLogger(__name__)


class MoistureHandler:
    """Handle moisture sensor operations via Bluetooth serial."""
    
    def __init__(self, port: str = "/dev/rfcomm2", baud_rate: int = 9600,
                 timeout: int = 5, simulation: bool = False):
        self.port = port
        self.baud_rate = baud_rate
        self.timeout = timeout
        self.simulation = simulation
        self.serial: Optional[serial.Serial] = None
        self.num_sensors = 4
        
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
            logger.info(f"Moisture Handler connected to {self.port}")
        except Exception as e:
            logger.error(f"Failed to connect Moisture handler: {e}")
            raise
    
    def read_moisture(self) -> Optional[List[float]]:
        """
        Read moisture from all 4 sensors and return average.
        Returns list of [sensor1, sensor2, sensor3, sensor4, average]
        """
        if self.simulation:
            return self._simulate_read()
        
        try:
            self.serial.write(b"READ
")
            
            start = time.time()
            while time.time() - start < self.timeout:
                if self.serial.in_waiting > 0:
                    line = self.serial.readline().decode('utf-8').strip()
                    if line.startswith("MOISTURE:"):
                        data = line.split(":")[1]
                        readings = [float(x) for x in data.split(",")]
                        
                        if len(readings) == self.num_sensors:
                            avg = sum(readings) / len(readings)
                            result = readings + [round(avg, 2)]
                            logger.info(f"Moisture readings: {result}")
                            return result
                time.sleep(0.1)
            
            logger.error("Moisture read timeout")
            return None
        except Exception as e:
            logger.error(f"Moisture read error: {e}")
            return None
    
    def _simulate_read(self) -> List[float]:
        """Simulate moisture readings."""
        import random
        readings = [round(random.uniform(10, 15), 2) for _ in range(self.num_sensors)]
        avg = round(sum(readings) / len(readings), 2)
        result = readings + [avg]
        logger.info(f"[SIM] Moisture readings: {result}")
        return result
    
    def close(self):
        """Close serial connection."""
        if self.serial and self.serial.is_open:
            self.serial.close()
            logger.info("Moisture handler closed")


# Test function
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    handler = MoistureHandler(simulation=True)
    moisture = handler.read_moisture()
    print(f"Moisture: {moisture}")
    handler.close()