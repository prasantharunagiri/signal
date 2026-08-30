from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
from app.providers.base import Candle
from app.strategies.liquidity import LiquidityReference

class DetectedMSS(BaseModel):
    direction: str  # BULLISH, BEARISH
    broken_level: float
    break_price: float
    break_time: datetime
    previous_structure: str

def detect_mss(
    candles: List[Candle],
    swings: List[LiquidityReference],
    lookback: int = 10
) -> Optional[DetectedMSS]:
    """
    Detects Market Structure Shifts (MSS).
    - Bullish MSS: Price closes above recent confirmed Swing High.
    - Bearish MSS: Price closes below recent confirmed Swing Low.
    """
    if not candles or not swings:
        return None

    current_candle = candles[-1]
    recent_swings = [s for s in swings if s.is_confirmed]

    # Define the time horizon for valid recent structural swings
    horizon_time = candles[-lookback].timestamp if len(candles) >= lookback else candles[0].timestamp

    # Check Bullish MSS against recent Swing Highs
    swing_highs = [s for s in recent_swings if s.level_type == "SWING_HIGH" and s.timestamp >= horizon_time]
    if swing_highs:
        latest_sh = swing_highs[-1]
        if current_candle.close > latest_sh.price and candles[-2].close <= latest_sh.price:
            return DetectedMSS(
                direction="BULLISH",
                broken_level=latest_sh.price,
                break_price=current_candle.close,
                break_time=current_candle.timestamp,
                previous_structure="BEARISH"
            )

    # Check Bearish MSS against recent Swing Lows
    swing_lows = [s for s in recent_swings if s.level_type == "SWING_LOW" and s.timestamp >= horizon_time]
    if swing_lows:
        latest_sl = swing_lows[-1]
        if current_candle.close < latest_sl.price and candles[-2].close >= latest_sl.price:
            return DetectedMSS(
                direction="BEARISH",
                broken_level=latest_sl.price,
                break_price=current_candle.close,
                break_time=current_candle.timestamp,
                previous_structure="BULLISH"
            )

    return None
