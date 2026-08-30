from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
from app.providers.base import Candle
from app.strategies.liquidity import LiquidityReference

class DetectedSweep(BaseModel):
    direction: str  # BULLISH, BEARISH
    liquidity_type: str  # PDH, PDL, PSH, PSL, EQUAL_HIGH, EQUAL_LOW, SWING_HIGH, SWING_LOW
    liquidity_level_price: float
    sweep_price: float
    sweep_time: datetime
    reclaim_price: float
    reclaim_time: datetime
    sweep_distance: float

def detect_sweeps(
    candles: List[Candle],
    liquidity_levels: List[LiquidityReference],
    lookback_candles: int = 15
) -> List[DetectedSweep]:
    """
    Detects bullish & bearish sweeps and reclaims over the recent candle window.
    """
    if not candles or not liquidity_levels:
        return []

    recent_candles = candles[-lookback_candles:]
    sweeps = []

    for ref in liquidity_levels:
        # Bullish Sweep: Price trades BELOW liquidity level, but eventually closes ABOVE it
        if "LOW" in ref.level_type or ref.level_type == "PDL" or ref.level_type == "PSL":
            is_sweeping = False
            sweep_lowest = None
            sweep_start_time = None
            for candle in recent_candles:
                if not is_sweeping:
                    if candle.low < ref.price:
                        is_sweeping = True
                        sweep_lowest = candle.low
                        sweep_start_time = candle.timestamp
                        
                        if candle.close > ref.price:
                            sweeps.append(
                                DetectedSweep(
                                    direction="BULLISH",
                                    liquidity_type=ref.level_type,
                                    liquidity_level_price=ref.price,
                                    sweep_price=sweep_lowest,
                                    sweep_time=sweep_start_time,
                                    reclaim_price=candle.close,
                                    reclaim_time=candle.timestamp,
                                    sweep_distance=round(ref.price - sweep_lowest, 2)
                                )
                            )
                            is_sweeping = False
                else:
                    if candle.low < sweep_lowest:
                        sweep_lowest = candle.low
                        sweep_start_time = candle.timestamp
                        
                    if candle.close > ref.price:
                        sweeps.append(
                            DetectedSweep(
                                direction="BULLISH",
                                liquidity_type=ref.level_type,
                                liquidity_level_price=ref.price,
                                sweep_price=sweep_lowest,
                                sweep_time=sweep_start_time,
                                reclaim_price=candle.close,
                                reclaim_time=candle.timestamp,
                                sweep_distance=round(ref.price - sweep_lowest, 2)
                            )
                        )
                        is_sweeping = False

        # Bearish Sweep: Price trades ABOVE liquidity level, but eventually closes BELOW it
        if "HIGH" in ref.level_type or ref.level_type == "PDH" or ref.level_type == "PSH":
            is_sweeping = False
            sweep_highest = None
            sweep_start_time = None
            for candle in recent_candles:
                if not is_sweeping:
                    if candle.high > ref.price:
                        is_sweeping = True
                        sweep_highest = candle.high
                        sweep_start_time = candle.timestamp
                        
                        if candle.close < ref.price:
                            sweeps.append(
                                DetectedSweep(
                                    direction="BEARISH",
                                    liquidity_type=ref.level_type,
                                    liquidity_level_price=ref.price,
                                    sweep_price=sweep_highest,
                                    sweep_time=sweep_start_time,
                                    reclaim_price=candle.close,
                                    reclaim_time=candle.timestamp,
                                    sweep_distance=round(sweep_highest - ref.price, 2)
                                )
                            )
                            is_sweeping = False
                else:
                    if candle.high > sweep_highest:
                        sweep_highest = candle.high
                        sweep_start_time = candle.timestamp
                        
                    if candle.close < ref.price:
                        sweeps.append(
                            DetectedSweep(
                                direction="BEARISH",
                                liquidity_type=ref.level_type,
                                liquidity_level_price=ref.price,
                                sweep_price=sweep_highest,
                                sweep_time=sweep_start_time,
                                reclaim_price=candle.close,
                                reclaim_time=candle.timestamp,
                                sweep_distance=round(sweep_highest - ref.price, 2)
                            )
                        )
                        is_sweeping = False

    return sweeps
