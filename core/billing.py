"""
Billing and Payment Calculation
Storage fees, market rates, deductions, and invoicing.
"""

import logging
from typing import Dict, Tuple
from datetime import datetime, date
import yaml
from pathlib import Path

logger = logging.getLogger(__name__)


class BillingEngine:
    """Calculate fees, rates, and generate invoices."""
    
    def __init__(self, config: Dict, market_rates_path: str = "config/market_rates.yaml"):
        self.config = config
        self.billing_config = config.get('billing', {})
        self.market_rates = self._load_market_rates(market_rates_path)
        logger.info("Billing engine initialized")
    
    def _load_market_rates(self, path: str) -> Dict:
        """Load current market rates."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                return data.get('rates', {})
        except Exception as e:
            logger.error(f"Failed to load market rates: {e}")
            return {}
    
    def calculate_storage_fee(self, weight_kg: float, duration_months: float,
                             quality_grade: str = 'B') -> Tuple[float, Dict]:
        """
        Calculate storage fee.
        Returns (total_fee, breakdown_dict)
        """
        base_rate = self.billing_config.get('storage_rate_per_kg_per_month', 2.0)
        min_charge = self.billing_config.get('min_storage_charge', 50.0)
        
        # Base calculation
        base_fee = weight_kg * base_rate * duration_months
        
        # Apply minimum charge
        if base_fee < min_charge:
            base_fee = min_charge
        
        # Quality premium/penalty
        quality_premium_rate = self.billing_config.get('quality_premium_rate', 0.1)
        quality_adjustment = 0.0
        
        if quality_grade == 'A':
            quality_adjustment = base_fee * quality_premium_rate
        elif quality_grade == 'C':
            quality_adjustment = -base_fee * (quality_premium_rate / 2)
        
        total_fee = base_fee + quality_adjustment
        
        breakdown = {
            'base_fee': round(base_fee, 2),
            'quality_adjustment': round(quality_adjustment, 2),
            'total_fee': round(total_fee, 2),
            'weight_kg': weight_kg,
            'duration_months': duration_months,
            'rate_per_kg_per_month': base_rate,
            'quality_grade': quality_grade
        }
        
        return round(total_fee, 2), breakdown
    
    def calculate_selling_amount(self, crop_type: str, weight_kg: float,
                                 quality_grade: str = 'B') -> Tuple[float, Dict]:
        """
        Calculate amount farmer receives when selling.
        Returns (amount, breakdown_dict)
        """
        # Get market rate
        crop_rates = self.market_rates.get(crop_type, {})
        base_rate = crop_rates.get('base_rate', 0.0)
        
        if base_rate == 0:
            logger.warning(f"No market rate found for {crop_type}")
            return 0.0, {}
        
        # Base amount
        base_amount = weight_kg * base_rate
        
        # Quality adjustment
        from core.quality import QualityControl
        qc = QualityControl()
        quality_multiplier = qc.get_quality_multiplier(quality_grade)
        
        adjusted_amount = base_amount * quality_multiplier
        
        # Deductions (storage fees, if any unpaid)
        # This would be fetched from transactions table in real scenario
        deductions = 0.0
        
        final_amount = adjusted_amount - deductions
        
        breakdown = {
            'base_rate': base_rate,
            'weight_kg': weight_kg,
            'base_amount': round(base_amount, 2),
            'quality_grade': quality_grade,
            'quality_multiplier': quality_multiplier,
            'adjusted_amount': round(adjusted_amount, 2),
            'deductions': round(deductions, 2),
            'final_amount': round(final_amount, 2)
        }
        
        return round(final_amount, 2), breakdown
    
    def calculate_buying_amount(self, crop_type: str, weight_kg: float,
                               quality_grade: str = 'B') -> Tuple[float, Dict]:
        """
        Calculate amount to pay farmer when buying crop.
        Uses MSP or market rate, whichever is higher.
        """
        # Get market rate
        crop_rates = self.market_rates.get(crop_type, {})
        market_rate = crop_rates.get('base_rate', 0.0)
        
        # Get MSP (fallback)
        msp_rates = self._load_msp_rates()
        msp_rate = msp_rates.get(crop_type, market_rate)
        
        # Use higher rate
        rate = max(market_rate, msp_rate)
        
        # Base amount
        base_amount = weight_kg * rate
        
        # Quality adjustment
        from core.quality import QualityControl
        qc = QualityControl()
        quality_multiplier = qc.get_quality_multiplier(quality_grade)
        
        final_amount = base_amount * quality_multiplier
        
        breakdown = {
            'market_rate': market_rate,
            'msp_rate': msp_rate,
            'applied_rate': rate,
            'weight_kg': weight_kg,
            'quality_grade': quality_grade,
            'quality_multiplier': quality_multiplier,
            'final_amount': round(final_amount, 2)
        }
        
        return round(final_amount, 2), breakdown
    
    def _load_msp_rates(self) -> Dict:
        """Load MSP rates from config."""
        try:
            with open("config/market_rates.yaml", 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                return data.get('msp', {})
        except Exception as e:
            logger.error(f"Failed to load MSP rates: {e}")
            return {}
    
    def calculate_late_penalty(self, original_amount: float, days_late: int) -> float:
        """Calculate late payment penalty."""
        if days_late <= 0:
            return 0.0
        
        penalty_percent = self.billing_config.get('late_payment_penalty_percent', 5.0)
        penalty = original_amount * (penalty_percent / 100.0)
        
        return round(penalty, 2)