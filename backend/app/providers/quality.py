from typing import List, Tuple, Optional
import numpy as np
from app.providers.base import Candle

class DataQualityChecker:
    def __init__(self, spike_atr_multiple: float = 5.0):
        self.spike_atr_multiple = spike_atr_multiple

    def validate_candle(self, candle: Candle, recent_candles: Optional[List[Candle]] = None) -> Tuple[bool, Optional[str]]:
        """
        Validates a single candle.
        Returns: (is_valid: bool, rejection_reason: Optional[str])
        """
        # 1. Structural Checks
        if candle.open <= 0 or candle.high <= 0 or candle.low <= 0 or candle.close <= 0:
            return False, "INVALID_PRICE_NON_POSITIVE"

        if candle.high < candle.low:
            return False, "INVALID_HIGH_LESS_THAN_LOW"

        if candle.high < max(candle.open, candle.close):
            return False, "INVALID_HIGH_LESS_THAN_BODY"

        if candle.low > min(candle.open, candle.close):
            return False, "INVALID_LOW_GREATER_THAN_BODY"

        # 2. Spike / Anomaly Detection vs Recent Range
        if recent_candles and len(recent_candles) >= 5:
            ranges = [c.high - c.low for c in recent_candles[-20:]]
            avg_range = float(np.mean(ranges)) if ranges else 0.0
            
            curr_range = candle.high - candle.low
            if avg_range > 0 and curr_range > (avg_range * self.spike_atr_multiple):
                return False, f"EXTREME_SPIKE_RANGE ({curr_range:.2f} > {self.spike_atr_multiple}x avg {avg_range:.2f})"

        return True, None
