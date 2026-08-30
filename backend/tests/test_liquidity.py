import pytest
from datetime import datetime, timedelta
from app.providers.base import Candle
from app.strategies.liquidity import detect_swings, detect_pdh_pdl, detect_equal_highs_lows

def test_swing_detection_no_lookahead():
    # Build synthetic 7-candle sequence where candle index 3 is a swing high (2490, 2495, 2498, 2510, 2502, 2499, 2490)
    highs = [2490.0, 2495.0, 2498.0, 2510.0, 2502.0, 2499.0, 2490.0]
    candles = [
        Candle(
            symbol="XAUUSD",
            timeframe="5m",
            timestamp=datetime(2026, 8, 22, 10, 0) + timedelta(minutes=i * 5),
            open=h - 2,
            high=h,
            low=h - 5,
            close=h - 3
        )
        for i, h in enumerate(highs)
    ]

    # At current_idx = 3 (when candle 3 closes), candle 3 CANNOT be confirmed as a swing high yet because candles 4 & 5 haven't closed!
    swings_at_idx3 = detect_swings(candles, n=2, current_idx=3)
    assert not any(s.price == 2510.0 for s in swings_at_idx3)

    # At current_idx = 5 (after candles 4 & 5 close), candle 3 IS confirmed as a swing high!
    swings_at_idx5 = detect_swings(candles, n=2, current_idx=5)
    sh_2510 = [s for s in swings_at_idx5 if s.price == 2510.0 and s.level_type == "SWING_HIGH"]
    assert len(sh_2510) == 1

def test_pdh_pdl_detection():
    day1_ts = datetime(2026, 8, 21, 10, 0)
    day2_ts = datetime(2026, 8, 22, 10, 0)

    candles = [
        Candle(symbol="XAUUSD", timeframe="1h", timestamp=day1_ts, open=2500, high=2520, low=2480, close=2510),
        Candle(symbol="XAUUSD", timeframe="1h", timestamp=day1_ts + timedelta(hours=2), open=2510, high=2535, low=2490, close=2500),
        Candle(symbol="XAUUSD", timeframe="1h", timestamp=day2_ts, open=2500, high=2505, low=2495, close=2502)
    ]

    pdh_pdl = detect_pdh_pdl(candles, current_time=day2_ts)
    assert pdh_pdl["PDH"].price == 2535.0
    assert pdh_pdl["PDL"].price == 2480.0
