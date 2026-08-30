from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
from app.providers.base import Candle

class DivergenceResult(BaseModel):
    divergence_type: str  # BULLISH, BEARISH, NONE
    comparison_symbol: str
    primary_price_point: float
    comparison_price_point: float
    timestamp: datetime

def detect_smt_divergence(
    primary_candles: List[Candle],
    comparison_candles: List[Candle],
    comparison_symbol: str = "DXY",
    window: int = 5
) -> DivergenceResult:
    """
    Detects SMT Divergence between XAUUSD and DXY (or XAGUSD / US10Y).
    XAUUSD and DXY have inverse correlation:
    - Bullish SMT: XAUUSD forms a lower low, but DXY fails to form a higher high (forms a lower high).
    - Bearish SMT: XAUUSD forms a higher high, but DXY fails to form a lower low (forms a higher low).
    """
    if len(primary_candles) < window or len(comparison_candles) < window:
        return DivergenceResult(
            divergence_type="NONE",
            comparison_symbol=comparison_symbol,
            primary_price_point=primary_candles[-1].close if primary_candles else 0.0,
            comparison_price_point=comparison_candles[-1].close if comparison_candles else 0.0,
            timestamp=primary_candles[-1].timestamp if primary_candles else datetime.utcnow()
        )

    p_recent = primary_candles[-window:]
    c_recent = comparison_candles[-window:]

    p_last = p_recent[-1]
    c_last = c_recent[-1]

    # Check Bullish SMT (Primary lower low vs Comparison lower high)
    p_prev_low = min(c.low for c in p_recent[:-1])
    c_prev_high = max(c.high for c in c_recent[:-1])

    if p_last.low < p_prev_low and c_last.high < c_prev_high:
        return DivergenceResult(
            divergence_type="BULLISH",
            comparison_symbol=comparison_symbol,
            primary_price_point=p_last.low,
            comparison_price_point=c_last.high,
            timestamp=p_last.timestamp
        )

    # Check Bearish SMT (Primary higher high vs Comparison higher low)
    p_prev_high = max(c.high for c in p_recent[:-1])
    c_prev_low = min(c.low for c in c_recent[:-1])

    if p_last.high > p_prev_high and c_last.low > c_prev_low:
        return DivergenceResult(
            divergence_type="BEARISH",
            comparison_symbol=comparison_symbol,
            primary_price_point=p_last.high,
            comparison_price_point=c_last.low,
            timestamp=p_last.timestamp
        )

    return DivergenceResult(
        divergence_type="NONE",
        comparison_symbol=comparison_symbol,
        primary_price_point=p_last.close,
        comparison_price_point=c_last.close,
        timestamp=p_last.timestamp
    )
