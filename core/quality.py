"""
Quality Control System
Moisture validation, quality grading, and acceptance criteria.
"""

import logging
from typing import Tuple, Dict, Optional
import yaml
from pathlib import Path

logger = logging.getLogger(__name__)


class QualityControl:
    """Quality validation and grading system."""
    
    def __init__(self, config_path: str = "config/crop_profiles.yaml"):
        self.profiles = self._load_profiles(config_path)
        logger.info(f"Quality control initialized with {len(self.profiles)} crop profiles")
    
    def _load_profiles(self, path: str) -> Dict:
        """Load crop quality profiles."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                return data.get('crops', {})
        except Exception as e:
            logger.error(f"Failed to load crop profiles: {e}")
            return {}
    
    def validate_moisture(self, crop_type: str, moisture_percent: float) -> Tuple[bool, str, str]:
        """
        Validate moisture level.
        Returns (accepted: bool, grade: str, message: str)
        Grades: A (excellent), B (good), C (acceptable), REJECT
        """
        profile = self.profiles.get(crop_type, {})
        moisture_max = profile.get('moisture_max', 14.0)
        moisture_reject = profile.get('moisture_reject', 18.0)
        
        if moisture_percent > moisture_reject:
            return False, 'REJECT', f"Moisture {moisture_percent}% exceeds rejection threshold {moisture_reject}%"
        
        # Grading logic
        if moisture_percent <= moisture_max:
            grade = 'A'
            message = f"Excellent quality (moisture: {moisture_percent}%)"
        elif moisture_percent <= moisture_max + 1:
            grade = 'B'
            message = f"Good quality (moisture: {moisture_percent}%)"
        else:
            grade = 'C'
            message = f"Acceptable quality (moisture: {moisture_percent}%)"
        
        return True, grade, message
    
    def get_quality_multiplier(self, grade: str) -> float:
        """Get price multiplier based on quality grade."""
        multipliers = {
            'A': 1.1,   # 10% premium
            'B': 1.0,   # Base price
            'C': 0.95,  # 5% penalty
            'REJECT': 0.0
        }
        return multipliers.get(grade, 1.0)
    
    def calculate_expiry_date(self, crop_type: str, storage_date) -> str:
        """Calculate expiry date based on crop profile."""
        from datetime import datetime, timedelta
        
        profile = self.profiles.get(crop_type, {})
        expiry_days = profile.get('expiry_days', 180)
        
        if isinstance(storage_date, str):
            storage_date = datetime.fromisoformat(storage_date).date()
        
        expiry = storage_date + timedelta(days=expiry_days)
        return expiry.isoformat()
    
    def get_crop_name(self, crop_type: str, language: str = 'en') -> str:
        """Get localized crop name."""
        profile = self.profiles.get(crop_type, {})
        key = f'name_{language}'
        return profile.get(key, crop_type.title())
    
    def validate_weight(self, weight_kg: float, min_weight: float = 10.0, 
                       max_weight: float = 10000.0) -> Tuple[bool, str]:
        """Validate weight is within acceptable range."""
        if weight_kg < min_weight:
            return False, f"Weight {weight_kg} kg below minimum {min_weight} kg"
        if weight_kg > max_weight:
            return False, f"Weight {weight_kg} kg exceeds maximum {max_weight} kg"
        return True, "Weight OK"
    
    def get_quality_report(self, crop_type: str, weight_kg: float, 
                          moisture_percent: float, sensor_readings: list) -> Dict:
        """Generate comprehensive quality report."""
        accepted, grade, message = self.validate_moisture(crop_type, moisture_percent)
        weight_ok, weight_msg = self.validate_weight(weight_kg)
        
        return {
            'crop_type': crop_type,
            'weight_kg': weight_kg,
            'moisture_percent': moisture_percent,
            'sensor_readings': sensor_readings,
            'accepted': accepted and weight_ok,
            'grade': grade if accepted else 'REJECT',
            'quality_message': message,
            'weight_message': weight_msg,
            'quality_multiplier': self.get_quality_multiplier(grade) if accepted else 0.0
        }