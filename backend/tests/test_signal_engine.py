import pytest
from datetime import datetime, timedelta
from app.providers.base import Candle
from app.strategies.liquidity import LiquidityReference
from app.strategies.scoring import calculate_confluence_score
from app.strategies.engine import run_strategy_pipeline

def test_confluence_scoring():
    score_full = calculate_confluence_score(
        has_sweep=True, has_smt=True, has_mss=True, has_displacement=True, has_fvg=True, session="London"
    )
    assert score_full.total_score == 100
    assert score_full.grade == "A+"

    score_partial = calculate_confluence_score(
        has_sweep=True, has_smt=False, has_mss=True, has_displacement=True, has_fvg=False, session="London"
    )
    # Sweep(20) + MSS(20) + Disp(15) + Session(10) = 65
    assert score_partial.total_score == 65
    assert score_partial.grade == "NO_SIGNAL"

def test_pipeline_valid_buy_signal():
    now = datetime(2026, 8, 22, 10, 0)
    candles = []
    # Prepend 10 historical candles to satisfy ATR(14) period
    for i in range(10):
        candles.append(Candle(symbol="XAUUSD", timeframe="5m", timestamp=now + timedelta(minutes=i * 5), open=2500, high=2501, low=2499, close=2500))

    base_time = now + timedelta(minutes=50)
    # Create a confirmed Swing Low at 2495.0 (index 12: low=2495.0)
    candles.append(Candle(symbol="XAUUSD", timeframe="5m", timestamp=base_time, open=2500, high=2502, low=2498, close=2501))
    candles.append(Candle(symbol="XAUUSD", timeframe="5m", timestamp=base_time + timedelta(minutes=5), open=2501, high=2503, low=2497, close=2499))
    candles.append(Candle(symbol="XAUUSD", timeframe="5m", timestamp=base_time + timedelta(minutes=10), open=2499, high=2500, low=2495.0, close=2498)) # Swing Low
    candles.append(Candle(symbol="XAUUSD", timeframe="5m", timestamp=base_time + timedelta(minutes=15), open=2498, high=2502, low=2497, close=2500))
    candles.append(Candle(symbol="XAUUSD", timeframe="5m", timestamp=base_time + timedelta(minutes=20), open=2500, high=2505, low=2499, close=2503))

    # Sweep candle down to 2488.0 (< 2495.0) and reclaim back to 2498.0
    candles.append(Candle(symbol="XAUUSD", timeframe="5m", timestamp=base_time + timedelta(minutes=25), open=2503, high=2504, low=2488.0, close=2498.0))
    # Displacement + Bullish MSS candle closing at 2515.0 (> 2505.0)
    candles.append(Candle(symbol="XAUUSD", timeframe="5m", timestamp=base_time + timedelta(minutes=30), open=2498, high=2516, low=2497, close=2515.0))
    # FVG candle (open=2508, high=2525, low=2507, close=2522) -> body=14, range=18, ratio=0.77 >= 0.60
    candles.append(Candle(symbol="XAUUSD", timeframe="5m", timestamp=base_time + timedelta(minutes=35), open=2508.0, high=2525, low=2507.0, close=2522.0))

    # Run pipeline
    sig = run_strategy_pipeline(candles, min_score=70, strategy_preset="INTRADAY")
    assert sig is not None
    assert sig.direction == "BUY"
    assert sig.score >= 70
    assert sig.tp1 > sig.entry_price
    assert sig.tp2 > sig.tp1
    assert sig.tp3 > sig.tp2
    assert sig.stop_loss < sig.entry_price
    assert sig.signal_key.startswith("XAUUSD:5m:")
