from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
from app.providers.base import Candle

class DetectedFVG(BaseModel):
    fvg_type: str  # BULLISH, BEARISH
    fvg_high: float
    fvg_low: float
    fvg_size: float
    timestamp: datetime
    filled: bool = False
    filled_at: Optional[datetime] = None

def detect_fvgs(
    candles: List[Candle],
    min_fvg_size_pips: float = 0.3,
    lookback: int = 20,
    include_filled: bool = True
) -> List[DetectedFVG]:
    """
    Detects 3-candle Fair Value Gaps (FVG) and evaluates their fill/mitigation status.
    - Bullish FVG: Candle 1 High < Candle 3 Low (Gap = Candle 3 Low - Candle 1 High)
    - Bearish FVG: Candle 1 Low > Candle 3 High (Gap = Candle 1 Low - Candle 3 High)
    """
    if len(candles) < 3:
        return []

    recent = candles[-lookback:] if len(candles) > lookback else candles
    fvgs = []

    for i in range(len(recent) - 2):
        c1 = recent[i]
        c2 = recent[i + 1]
        c3 = recent[i + 2]

        # Bullish FVG
        if c1.high < c3.low:
            gap_size = c3.low - c1.high
            if gap_size >= min_fvg_size_pips:
                # Check if filled by subsequent candles in the window
                filled = False
                filled_time = None
                for sub in recent[i + 3:]:
                    if sub.low <= c1.high:
                        filled = True
                        filled_time = sub.timestamp
                        break

                fvgs.append(
                    DetectedFVG(
                        fvg_type="BULLISH",
                        fvg_high=c3.low,
                        fvg_low=c1.high,
                        fvg_size=round(gap_size, 2),
                        timestamp=c2.timestamp,
                        filled=filled,
                        filled_at=filled_time
                    )
                )

        # Bearish FVG
        elif c1.low > c3.high:
            gap_size = c1.low - c3.high
            if gap_size >= min_fvg_size_pips:
                filled = False
                filled_time = None
                for sub in recent[i + 3:]:
                    if sub.high >= c1.low:
                        filled = True
                        filled_time = sub.timestamp
                        break

                fvgs.append(
                    DetectedFVG(
                        fvg_type="BEARISH",
                        fvg_high=c1.low,
                        fvg_low=c3.high,
                        fvg_size=round(gap_size, 2),
                        timestamp=c2.timestamp,
                        filled=filled,
                        filled_at=filled_time
                    )
                )

    if not include_filled:
        return [f for f in fvgs if not f.filled]

    return fvgs

