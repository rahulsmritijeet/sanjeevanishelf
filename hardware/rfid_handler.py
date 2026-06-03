"""
RFID Handler for RC522 via Arduino + HC-05 Bluetooth
Protocol: Arduino sends "RFID:<UID>" on scan, responds to "WRITE:<UID>:<DATA>"
"""

import serial
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)


class RFIDHandler:
    """Handle RFID operations via Bluetooth serial."""
    
    def __init__(self, port: str = "/dev/rfcomm0", baud_rate: int = 9600, 
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
            time.sleep(2)  # Arduino reset delay
            logger.info(f"RFID Handler connected to {self.port}")
        except Exception as e:
            logger.error(f"Failed to connect RFID handler: {e}")
            raise
    
    def read_uid(self, timeout: int = 10) -> Optional[str]:
        """
        Wait for RFID scan and return UID.
        In simulation, prompts for manual input.
        """
        if self.simulation:
            return self._simulate_read()
        
        try:
            start = time.time()
            self.serial.flushInput()
            
            while time.time() - start < timeout:
                if self.serial.in_waiting > 0:
                    line = self.serial.readline().decode('utf-8').strip()
                    if line.startswith("RFID:"):
                        uid = line.split(":")[1]
                        logger.info(f"RFID scanned: {uid}")
                        return uid
                time.sleep(0.1)
            
            logger.warning("RFID scan timeout")
            return None
        except Exception as e:
            logger.error(f"RFID read error: {e}")
            return None
    
    def write_data(self, uid: str, data: str) -> bool:
        """
        Write data to RFID tag.
        In simulation, always succeeds.
        """
        if self.simulation:
            logger.info(f"[SIM] RFID write to {uid}: {data}")
            return True
        
        try:
            command = f"WRITE:{uid}:{data}
"
            self.serial.write(command.encode('utf-8'))
            
            # Wait for ACK
            start = time.time()
            while time.time() - start < self.timeout:
                if self.serial.in_waiting > 0:
                    response = self.serial.readline().decode('utf-8').strip()
                    if response == "WRITE_OK":
                        logger.info(f"RFID write successful: {uid}")
                        return True
                    elif response == "WRITE_FAIL":
                        logger.error(f"RFID write failed: {uid}")
                        return False
                time.sleep(0.1)
            
            logger.error("RFID write timeout")
            return False
        except Exception as e:
            logger.error(f"RFID write error: {e}")
            return False
    
    def _simulate_read(self) -> str:
        """Simulate RFID read with auto-generated UID."""
        # In real UI, this would be a popup input
        # For now, return a test UID
        import random
        uid = f"{random.randint(0, 255):02X}{random.randint(0, 255):02X}{random.randint(0, 255):02X}{random.randint(0, 255):02X}"
        logger.info(f"[SIM] RFID scanned: {uid}")
        return uid
    
    def close(self):
        """Close serial connection."""
        if self.serial and self.serial.is_open:
            self.serial.close()
            logger.info("RFID handler closed")


# Test function
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Test in simulation mode
    handler = RFIDHandler(simulation=True)
    uid = handler.read_uid()
    print(f"Read UID: {uid}")
    handler.write_data(uid, "BATCH123")
    handler.close()