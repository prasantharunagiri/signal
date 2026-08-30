import pytest
from datetime import datetime, timedelta
from app.providers.base import Candle
from app.strategies.liquidity import LiquidityReference
from app.strategies.mss import detect_mss
from app.strategies.displacement import detect_displacement

def test_bullish_mss_detection():
    swing_high = LiquidityReference(
        level_type="SWING_HIGH",
        price=2500.0,
        timestamp=datetime(2026, 8, 22, 10, 0),
        is_confirmed=True
    )
    break_candle = Candle(
        symbol="XAUUSD",
        timeframe="5m",
        timestamp=datetime(2026, 8, 22, 11, 0),
        open=2495.0,
        high=2508.0,
        low=2494.0,
        close=2506.0  # Closes above swing high 2500.0
    )

    mss = detect_mss([break_candle], [swing_high])
    assert mss is not None
    assert mss.direction == "BULLISH"
    assert mss.broken_level == 2500.0
    assert mss.break_price == 2506.0

def test_displacement_valid_and_invalid():
    now = datetime(2026, 8, 22, 12, 0)
    # 14 small historical candles with range ~ 2.0
    past = [
        Candle(symbol="XAUUSD", timeframe="5m", timestamp=now - timedelta(minutes=i*5), open=2500, high=2501, low=2499, close=2500)
        for i in range(15, 0, -1)
    ]
    # Strong displacement candle: open 2500, high 2510, low 2499.5, close 2509.5 (body=9.5, range=10.5, ratio=0.90)
    disp_candle = Candle(
        symbol="XAUUSD", timeframe="5m", timestamp=now, open=2500.0, high=2510.0, low=2499.5, close=2509.5
    )

    res_valid = detect_displacement(past + [disp_candle], min_body_ratio=0.60, min_atr_multiple=1.2)
    assert res_valid.is_displacement is True
    assert res_valid.direction == "BULLISH"

    # Doji / weak body candle (open 2500, high 2505, low 2495, close 2500.5) -> body=0.5, range=10 -> body_ratio = 0.05
    weak_candle = Candle(
        symbol="XAUUSD", timeframe="5m", timestamp=now, open=2500.0, high=2505.0, low=2495.0, close=2500.5
    )
    res_invalid = detect_displacement(past + [weak_candle], min_body_ratio=0.60, min_atr_multiple=1.2)
    assert res_invalid.is_displacement is False
