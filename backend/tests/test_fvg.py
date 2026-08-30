import pytest
from datetime import datetime, timedelta
from app.providers.base import Candle
from app.strategies.fvg import detect_fvgs

def test_bullish_fvg_and_mitigation():
    now = datetime(2026, 8, 22, 10, 0)
    # Candle 1: High = 2500.0
    c1 = Candle(symbol="XAUUSD", timeframe="5m", timestamp=now, open=2495, high=2500.0, low=2490, close=2498)
    # Candle 2: Big expansion
    c2 = Candle(symbol="XAUUSD", timeframe="5m", timestamp=now + timedelta(minutes=5), open=2498, high=2508, low=2497, close=2507)
    # Candle 3: Low = 2503.0 (> Candle 1 High 2500.0). Gap = 3.0 pips
    c3 = Candle(symbol="XAUUSD", timeframe="5m", timestamp=now + timedelta(minutes=10), open=2507, high=2515, low=2503.0, close=2512)

    fvgs = detect_fvgs([c1, c2, c3], min_fvg_size_pips=0.3)
    assert len(fvgs) == 1
    assert fvgs[0].fvg_type == "BULLISH"
    assert fvgs[0].fvg_low == 2500.0
    assert fvgs[0].fvg_high == 2503.0
    assert fvgs[0].fvg_size == 3.0
    assert fvgs[0].filled is False

    # Candle 4: Retraces down to 2499.0 (fills the FVG)
    c4 = Candle(symbol="XAUUSD", timeframe="5m", timestamp=now + timedelta(minutes=15), open=2512, high=2513, low=2499.0, close=2504)
    fvgs_after_fill = detect_fvgs([c1, c2, c3, c4], min_fvg_size_pips=0.3)
    assert fvgs_after_fill[0].filled is True

def test_bearish_fvg():
    now = datetime(2026, 8, 22, 14, 0)
    # Candle 1: Low = 2520.0
    c1 = Candle(symbol="XAUUSD", timeframe="5m", timestamp=now, open=2525, high=2528, low=2520.0, close=2522)
    # Candle 2: Big downward expansion
    c2 = Candle(symbol="XAUUSD", timeframe="5m", timestamp=now + timedelta(minutes=5), open=2522, high=2523, low=2508, close=2510)
    # Candle 3: High = 2515.0 (< Candle 1 Low 2520.0). Gap = 5.0 pips
    c3 = Candle(symbol="XAUUSD", timeframe="5m", timestamp=now + timedelta(minutes=10), open=2510, high=2515.0, low=2505, close=2508)

    fvgs = detect_fvgs([c1, c2, c3], min_fvg_size_pips=0.3)
    assert len(fvgs) == 1
    assert fvgs[0].fvg_type == "BEARISH"
    assert fvgs[0].fvg_high == 2520.0
    assert fvgs[0].fvg_low == 2515.0
    assert fvgs[0].fvg_size == 5.0
