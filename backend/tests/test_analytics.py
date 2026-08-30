import pytest
from datetime import datetime
from app.models.schema import Signal
from app.analytics.performance import (
    analyze_performance_by_preset,
    analyze_performance_by_score,
    analyze_performance_by_session,
    analyze_performance_by_direction
)

def test_preset_performance_separation():
    now = datetime(2026, 8, 22, 10, 0)

    scalp_sig1 = Signal(signal_key="s1", symbol="XAUUSD", timeframe="1m", timestamp=now, direction="BUY", strategy_preset="SCALP", score=85, status="TP1_HIT", is_demo=False)
    scalp_sig2 = Signal(signal_key="s2", symbol="XAUUSD", timeframe="1m", timestamp=now, direction="BUY", strategy_preset="SCALP", score=85, status="TP2_HIT", is_demo=False)

    swing_sig1 = Signal(signal_key="w1", symbol="XAUUSD", timeframe="4h", timestamp=now, direction="SELL", strategy_preset="SWING", score=92, status="SL_HIT", is_demo=False)

    signals = [scalp_sig1, scalp_sig2, swing_sig1]

    preset_metrics = analyze_performance_by_preset(signals)

    # SCALP preset has 2 winning trades (TP1 = +1R, TP2 = +2R) -> total_r = +3R, win_rate = 100%
    assert preset_metrics["SCALP"].total_trades == 2
    assert preset_metrics["SCALP"].win_rate == 100.0
    assert preset_metrics["SCALP"].total_r == 3.0

    # SWING preset has 1 loss (SL = -1R) -> total_r = -1R, win_rate = 0%
    assert preset_metrics["SWING"].total_trades == 1
    assert preset_metrics["SWING"].win_rate == 0.0
    assert preset_metrics["SWING"].total_r == -1.0

    # INTRADAY preset has 0 trades
    assert preset_metrics["INTRADAY"].total_trades == 0
