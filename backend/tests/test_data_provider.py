import pytest
from datetime import datetime, timedelta
from app.providers.csv_provider import CSVProvider

def test_csv_provider_fetch_candles():
    provider = CSVProvider(data_dir="data/csv")
    candles = provider.fetch_candles(symbol="XAUUSD", timeframe="5m", limit=100)

    if not candles:
        pytest.skip("CSV data not present")
    assert len(candles) > 0
    for c in candles:
        assert c.is_demo is False
        assert c.symbol == "XAUUSD"
        assert c.timeframe == "5m"
        assert c.open > 0
        assert c.high >= c.low

def test_csv_provider_date_filtering():
    provider = CSVProvider(data_dir="data/csv")
    all_candles = provider.fetch_candles(symbol="XAUUSD", timeframe="15m", limit=1000)

    if not all_candles:
        pytest.skip("CSV data not generated yet")

    mid_idx = len(all_candles) // 2
    start_time = all_candles[mid_idx].timestamp
    filtered = provider.fetch_candles(symbol="XAUUSD", timeframe="15m", start_time=start_time)

    assert len(filtered) <= len(all_candles)
    for c in filtered:
        assert c.timestamp >= start_time
