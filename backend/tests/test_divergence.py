import pytest
from datetime import datetime, timedelta
from app.providers.base import Candle
from app.strategies.divergence import detect_smt_divergence

def test_bullish_smt_divergence():
    now = datetime(2026, 8, 22, 10, 0)
    # XAUUSD forms lower low: candle 0 low=2500, candle 1 low=2490
    xau_candles = [
        Candle(symbol="XAUUSD", timeframe="5m", timestamp=now, open=2505, high=2510, low=2500, close=2502),
        Candle(symbol="XAUUSD", timeframe="5m", timestamp=now + timedelta(minutes=5), open=2502, high=2504, low=2490, close=2495)
    ]
    # DXY forms lower high: candle 0 high=104.5, candle 1 high=104.2
    dxy_candles = [
        Candle(symbol="DXY", timeframe="5m", timestamp=now, open=104.0, high=104.5, low=103.8, close=104.2),
        Candle(symbol="DXY", timeframe="5m", timestamp=now + timedelta(minutes=5), open=104.1, high=104.2, low=103.9, close=104.0)
    ]

    res = detect_smt_divergence(xau_candles, dxy_candles, window=2)
    assert res.divergence_type == "BULLISH"
    assert res.comparison_symbol == "DXY"

def test_bearish_smt_divergence():
    now = datetime(2026, 8, 22, 14, 0)
    # XAUUSD forms higher high: candle 0 high=2510, candle 1 high=2525
    xau_candles = [
        Candle(symbol="XAUUSD", timeframe="5m", timestamp=now, open=2500, high=2510, low=2498, close=2508),
        Candle(symbol="XAUUSD", timeframe="5m", timestamp=now + timedelta(minutes=5), open=2508, high=2525, low=2505, close=2520)
    ]
    # DXY forms higher low: candle 0 low=103.5, candle 1 low=103.8
    dxy_candles = [
        Candle(symbol="DXY", timeframe="5m", timestamp=now, open=104.0, high=104.2, low=103.5, close=103.7),
        Candle(symbol="DXY", timeframe="5m", timestamp=now + timedelta(minutes=5), open=103.7, high=104.1, low=103.8, close=104.0)
    ]

    res = detect_smt_divergence(xau_candles, dxy_candles, window=2)
    assert res.divergence_type == "BEARISH"
