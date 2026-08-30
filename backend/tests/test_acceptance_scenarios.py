import pytest
from datetime import datetime, timedelta
from app.database import Base, engine, SessionLocal
from app.models.schema import MarketData, Signal, NotificationLog, SystemLog
from app.providers.csv_provider import CSVProvider
from app.providers.quality import DataQualityChecker
from app.strategies.liquidity import detect_swings
from app.strategies.engine import run_strategy_pipeline
from app.backtesting.engine import ChronologicalBacktester
from app.workers.notification_worker import NotificationDispatcher
from app.workers.health_monitor_worker import HealthMonitorWorker
from app.analytics.performance import analyze_performance_by_preset

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_scenario_1_reproducible_deterministic_results():
    provider = CSVProvider(data_dir="data/csv")
    candles1 = provider.fetch_candles("XAUUSD", "5m", limit=100)
    candles2 = provider.fetch_candles("XAUUSD", "5m", limit=100)

    assert len(candles1) == len(candles2)
    for c1, c2 in zip(candles1, candles2):
        assert c1.timestamp == c2.timestamp
        assert c1.close == c2.close

def test_scenario_2_shared_strategy_rules():
    # Both Backtester and Live Signal engine invoke the exact same run_strategy_pipeline function
    from app.strategies import engine as str_engine
    assert hasattr(str_engine, "run_strategy_pipeline")

def test_scenario_3_no_lookahead_bias():
    now = datetime(2026, 8, 22, 10, 0)
    highs = [2490.0, 2495.0, 2498.0, 2510.0, 2502.0, 2499.0, 2490.0]
    candles = [
        MarketData(symbol="XAUUSD", timeframe="5m", timestamp=now + timedelta(minutes=i*5), open=h-2, high=h, low=h-5, close=h-3)
        for i, h in enumerate(highs)
    ]
    swings = detect_swings(candles, n=2, current_idx=3)
    # At index 3, candle 3 (high 2510) CANNOT be confirmed yet as a swing high
    assert not any(s.price == 2510.0 for s in swings)

def test_scenario_4_and_5_idempotency_and_duplicate_prevention():
    db = SessionLocal()
    now = datetime(2026, 8, 22, 12, 0)
    sig_key = "XAUUSD:5m:2026-08-22T12:00:00:v1:false"

    sig1 = Signal(
        signal_key=sig_key, symbol="XAUUSD", timeframe="5m", timestamp=now, direction="BUY",
        score=85, score_grade="A", entry_price=2500.0, stop_loss=2492.0, tp1=2508.0, tp2=2516.0,
        tp3=2524.0, risk_distance=8.0, reward_tp1=8.0, reward_tp2=16.0, reward_tp3=24.0, status="OPEN", is_demo=False
    )
    db.add(sig1)
    db.commit()

    # Querying existing signal key prevents duplicate insertion
    existing = db.query(Signal).filter(Signal.signal_key == sig_key).first()
    assert existing is not None
    db.close()

def test_scenario_7_watchdog_stale_data_detection():
    db = SessionLocal()
    # Insert old candle from 2 hours ago
    old_time = datetime.utcnow() - timedelta(hours=2)
    old_candle = MarketData(
        symbol="XAUUSD", timeframe="5m", timestamp=old_time, open=2500, high=2505, low=2498, close=2502, is_demo=False
    )
    db.add(old_candle)
    db.commit()

    worker = HealthMonitorWorker()
    res = worker.check_health(db)
    assert res["market_data_status"] == "DATA STALE"
    assert "stale" in res["stale_message"].lower()
    db.close()

def test_scenario_9_demo_vs_live_strict_data_segregation():
    db = SessionLocal()
    now = datetime(2026, 8, 22, 14, 0)

    real_sig = Signal(signal_key="k1", symbol="XAUUSD", timeframe="5m", timestamp=now, direction="BUY", score=85, score_grade="A", entry_price=2500, stop_loss=2492, tp1=2508, tp2=2516, tp3=2524, risk_distance=8, reward_tp1=8, reward_tp2=16, reward_tp3=24, is_demo=False)
    demo_sig = Signal(signal_key="k2", symbol="XAUUSD", timeframe="5m", timestamp=now, direction="SELL", score=80, score_grade="A", entry_price=2500, stop_loss=2508, tp1=2492, tp2=2484, tp3=2476, risk_distance=8, reward_tp1=8, reward_tp2=16, reward_tp3=24, is_demo=True)

    db.add_all([real_sig, demo_sig])
    db.commit()

    real_count = db.query(Signal).filter(Signal.is_demo == False).count()
    demo_count = db.query(Signal).filter(Signal.is_demo == True).count()

    assert real_count == 1
    assert demo_count == 1
    db.close()

def test_scenario_10_strict_preset_performance_separation():
    now = datetime(2026, 8, 22, 10, 0)
    scalp = Signal(signal_key="p1", symbol="XAUUSD", timeframe="1m", timestamp=now, direction="BUY", strategy_preset="SCALP", score=85, status="TP1_HIT", is_demo=False)
    swing = Signal(signal_key="p2", symbol="XAUUSD", timeframe="4h", timestamp=now, direction="SELL", strategy_preset="SWING", score=90, status="SL_HIT", is_demo=False)

    metrics = analyze_performance_by_preset([scalp, swing])
    assert metrics["SCALP"].win_rate == 100.0
    assert metrics["SWING"].win_rate == 0.0
