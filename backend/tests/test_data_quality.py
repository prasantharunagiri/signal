import pytest
from datetime import datetime
from app.providers.base import Candle
from app.providers.quality import DataQualityChecker

def test_valid_candle():
    checker = DataQualityChecker()
    candle = Candle(
        symbol="XAUUSD",
        timeframe="5m",
        timestamp=datetime.utcnow(),
        open=2500.0,
        high=2505.0,
        low=2498.0,
        close=2503.0,
        volume=100.0
    )
    is_valid, reason = checker.validate_candle(candle)
    assert is_valid is True
    assert reason is None

def test_invalid_high_low():
    checker = DataQualityChecker()
    candle = Candle(
        symbol="XAUUSD",
        timeframe="5m",
        timestamp=datetime.utcnow(),
        open=2500.0,
        high=2490.0,  # High less than low
        low=2505.0,
        close=2495.0,
        volume=100.0
    )
    is_valid, reason = checker.validate_candle(candle)
    assert is_valid is False
    assert reason == "INVALID_HIGH_LESS_THAN_LOW"

def test_extreme_spike_detection():
    checker = DataQualityChecker(spike_atr_multiple=5.0)
    recent = [
        Candle(symbol="XAUUSD", timeframe="5m", timestamp=datetime.utcnow(), open=2500.0, high=2502.0, low=2498.0, close=2500.0)
        for _ in range(10)
    ]
    # Normal range ~ 4.0. Spike range = 50.0 (2550 - 2500)
    spike_candle = Candle(
        symbol="XAUUSD",
        timeframe="5m",
        timestamp=datetime.utcnow(),
        open=2500.0,
        high=2550.0,
        low=2500.0,
        close=2545.0
    )
    is_valid, reason = checker.validate_candle(spike_candle, recent)
    assert is_valid is False
    assert "EXTREME_SPIKE_RANGE" in reason
