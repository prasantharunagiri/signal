from typing import List, Optional
import numpy as np
from pydantic import BaseModel
from app.providers.base import Candle

class DisplacementResult(BaseModel):
    is_displacement: bool
    body_ratio: float
    range_atr_ratio: float
    direction: str  # BULLISH, BEARISH, NEUTRAL

def detect_displacement(
    candles: List[Candle],
    min_body_ratio: float = 0.60,
    min_atr_multiple: float = 1.2,
    atr_period: int = 14
) -> DisplacementResult:
    """
    Evaluates whether the latest candle exhibits institutional displacement.
    """
    if len(candles) < (atr_period + 1):
        return DisplacementResult(
            is_displacement=False,
            body_ratio=0.0,
            range_atr_ratio=0.0,
            direction="NEUTRAL"
        )

    current_candle = candles[-1]
    candle_range = current_candle.high - current_candle.low
    body_size = abs(current_candle.close - current_candle.open)

    if candle_range <= 0:
        return DisplacementResult(
            is_displacement=False,
            body_ratio=0.0,
            range_atr_ratio=0.0,
            direction="NEUTRAL"
        )

    body_ratio = body_size / candle_range

    # Calculate ATR over previous atr_period candles
    past_candles = candles[-(atr_period + 1):-1]
    ranges = [c.high - c.low for c in past_candles]
    atr = float(np.mean(ranges)) if ranges else 1.0

    range_atr_ratio = candle_range / atr if atr > 0 else 1.0

    direction = "NEUTRAL"
    if current_candle.close > current_candle.open:
        direction = "BULLISH"
    elif current_candle.close < current_candle.open:
        direction = "BEARISH"

    is_valid = (body_ratio >= min_body_ratio) and (range_atr_ratio >= min_atr_multiple)

    return DisplacementResult(
        is_displacement=is_valid,
        body_ratio=round(body_ratio, 2),
        range_atr_ratio=round(range_atr_ratio, 2),
        direction=direction
    )
