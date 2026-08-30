import pytest
from datetime import datetime
from app.providers.base import Candle
from app.strategies.liquidity import LiquidityReference
from app.strategies.sweeps import detect_sweeps

def test_bullish_sweep_detection():
    pdl_level = LiquidityReference(level_type="PDL", price=2490.0, timestamp=datetime(2026, 8, 21, 23, 0))
    sweep_candle = Candle(
        symbol="XAUUSD",
        timeframe="5m",
        timestamp=datetime(2026, 8, 22, 10, 0),
        open=2492.0,
        high=2495.0,
        low=2486.0,  # Swept down to 2486.0 (< 2490.0)
        close=2493.0 # Reclaimed and closed back above 2490.0
    )

    sweeps = detect_sweeps([sweep_candle], [pdl_level])
    assert len(sweeps) == 1
    assert sweeps[0].direction == "BULLISH"
    assert sweeps[0].liquidity_type == "PDL"
    assert sweeps[0].sweep_price == 2486.0
    assert sweeps[0].sweep_distance == 4.0

def test_bearish_sweep_detection():
    pdh_level = LiquidityReference(level_type="PDH", price=2520.0, timestamp=datetime(2026, 8, 21, 23, 0))
    sweep_candle = Candle(
        symbol="XAUUSD",
        timeframe="5m",
        timestamp=datetime(2026, 8, 22, 14, 0),
        open=2518.0,
        high=2526.0,  # Swept up to 2526.0 (> 2520.0)
        low=2515.0,
        close=2517.0 # Closed back below 2520.0
    )

    sweeps = detect_sweeps([sweep_candle], [pdh_level])
    assert len(sweeps) == 1
    assert sweeps[0].direction == "BEARISH"
    assert sweeps[0].liquidity_type == "PDH"
    assert sweeps[0].sweep_price == 2526.0
    assert sweeps[0].sweep_distance == 6.0
