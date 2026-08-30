from typing import List, Dict, Optional
from datetime import datetime, time
from pydantic import BaseModel
from app.providers.base import Candle

class LiquidityReference(BaseModel):
    level_type: str  # PDH, PDL, PSH, PSL, ASIAN_HIGH, ASIAN_LOW, LONDON_HIGH, LONDON_LOW, NY_HIGH, NY_LOW, EQUAL_HIGH, EQUAL_LOW, SWING_HIGH, SWING_LOW
    price: float
    timestamp: datetime
    session: Optional[str] = None
    is_confirmed: bool = True

def get_market_session(dt: datetime) -> str:
    """Returns the market session name in UTC."""
    h = dt.hour
    if 0 <= h < 7:
        return "Asian"
    elif 7 <= h < 13:
        return "London"
    elif 13 <= h < 16:
        return "London / NY Overlap"
    elif 16 <= h < 21:
        return "New York"
    else:
        return "Asian Pre-Market"

def detect_swings(candles: List[Candle], n: int = 2, current_idx: Optional[int] = None) -> List[LiquidityReference]:
    """
    Detects deterministic swing highs and lows with N-candle lookback.
    CRITICAL: For historical chronological processing at index `current_idx`,
    only swings where i + n <= current_idx are confirmed!
    """
    if len(candles) < (2 * n + 1):
        return []

    max_eval_idx = current_idx if current_idx is not None else (len(candles) - 1)
    swings = []

    # A candidate swing at index i requires candles from i - n to i + n
    for i in range(n, max_eval_idx - n + 1):
        c = candles[i]
        
        # Check Swing High
        is_swing_high = all(c.high > candles[i - k].high and c.high > candles[i + k].high for k in range(1, n + 1))
        if is_swing_high:
            swings.append(
                LiquidityReference(
                    level_type="SWING_HIGH",
                    price=c.high,
                    timestamp=c.timestamp,
                    session=get_market_session(c.timestamp),
                    is_confirmed=True
                )
            )

        # Check Swing Low
        is_swing_low = all(c.low < candles[i - k].low and c.low < candles[i + k].low for k in range(1, n + 1))
        if is_swing_low:
            swings.append(
                LiquidityReference(
                    level_type="SWING_LOW",
                    price=c.low,
                    timestamp=c.timestamp,
                    session=get_market_session(c.timestamp),
                    is_confirmed=True
                )
            )

    return swings

def detect_pdh_pdl(candles: List[Candle], current_time: datetime) -> Dict[str, Optional[LiquidityReference]]:
    """Detects Previous Day High and Previous Day Low relative to current_time."""
    current_date = current_time.date()
    prev_day_candles = [c for c in candles if c.timestamp.date() < current_date]

    if not prev_day_candles:
        return {"PDH": None, "PDL": None}

    # Get candles for the immediately preceding calendar day
    last_prev_date = prev_day_candles[-1].timestamp.date()
    target_day_candles = [c for c in prev_day_candles if c.timestamp.date() == last_prev_date]

    pdh_candle = max(target_day_candles, key=lambda c: c.high)
    pdl_candle = min(target_day_candles, key=lambda c: c.low)

    return {
        "PDH": LiquidityReference(level_type="PDH", price=pdh_candle.high, timestamp=pdh_candle.timestamp),
        "PDL": LiquidityReference(level_type="PDL", price=pdl_candle.low, timestamp=pdl_candle.timestamp),
    }

def detect_equal_highs_lows(candles: List[Candle], tolerance_pips: float = 0.5) -> List[LiquidityReference]:
    """Detects clusters of equal highs and equal lows within tolerance."""
    if len(candles) < 10:
        return []

    results = []
    highs = [(c.high, c.timestamp) for c in candles[-50:]]
    lows = [(c.low, c.timestamp) for c in candles[-50:]]

    seen_eq_highs = []
    for i in range(len(highs)):
        for j in range(i + 3, len(highs)):
            if abs(highs[i][0] - highs[j][0]) <= tolerance_pips:
                eq_price = round(max(highs[i][0], highs[j][0]), 2)
                if not any(abs(eq_price - p) <= tolerance_pips for p in seen_eq_highs):
                    seen_eq_highs.append(eq_price)
                    results.append(
                        LiquidityReference(
                            level_type="EQUAL_HIGH",
                            price=eq_price,
                            timestamp=highs[j][1]
                        )
                    )

    seen_eq_lows = []
    for i in range(len(lows)):
        for j in range(i + 3, len(lows)):
            if abs(lows[i][0] - lows[j][0]) <= tolerance_pips:
                eq_price = round(min(lows[i][0], lows[j][0]), 2)
                if not any(abs(eq_price - p) <= tolerance_pips for p in seen_eq_lows):
                    seen_eq_lows.append(eq_price)
                    results.append(
                        LiquidityReference(
                            level_type="EQUAL_LOW",
                            price=eq_price,
                            timestamp=lows[j][1]
                        )
                    )

    return results
