import pytest
from datetime import datetime
from app.providers.csv_provider import CSVProvider
from app.backtesting.engine import ChronologicalBacktester

def test_chronological_backtester_csv_run():
    provider = CSVProvider(data_dir="data/csv")
    backtester = ChronologicalBacktester(provider)

    start_date = datetime(2026, 8, 1, 0, 0)
    end_date = datetime(2026, 8, 22, 12, 0)

    summary = backtester.run_backtest(
        symbol="XAUUSD",
        timeframe="5m",
        start_date=start_date,
        end_date=end_date,
        strategy_preset="INTRADAY",
        min_score=70,
        comparison_symbol="DXY"
    )

    assert summary.symbol == "XAUUSD"
    assert summary.timeframe == "5m"
    assert summary.total_signals >= 0
    assert summary.win_rate >= 0.0
    assert summary.max_drawdown >= 0.0

    for trade in summary.trades:
        assert trade.outcome in ["TP1_HIT", "TP2_HIT", "TP3_HIT", "SL_HIT", "EXPIRED", "AMBIGUOUS"]
        assert trade.signal.is_demo is False
        assert trade.signal.strategy_preset == "INTRADAY"
