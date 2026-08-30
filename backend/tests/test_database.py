import pytest
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from app.database import Base, engine, SessionLocal
from app.models.schema import MarketData, Signal, SignalEvent

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_market_data_unique_constraint():
    db = SessionLocal()
    now = datetime(2026, 8, 22, 12, 0, 0)
    
    candle1 = MarketData(
        symbol="XAUUSD",
        timeframe="5m",
        timestamp=now,
        open=2500.0,
        high=2505.0,
        low=2498.0,
        close=2502.0,
        volume=100.0,
        is_demo=False
    )
    db.add(candle1)
    db.commit()

    # Attempting to insert duplicate candle with same (symbol, timeframe, timestamp, is_demo) must fail
    candle_duplicate = MarketData(
        symbol="XAUUSD",
        timeframe="5m",
        timestamp=now,
        open=2500.0,
        high=2505.0,
        low=2498.0,
        close=2502.0,
        volume=100.0,
        is_demo=False
    )
    db.add(candle_duplicate)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    db.close()


def test_signal_idempotency_key():
    db = SessionLocal()
    now = datetime(2026, 8, 22, 14, 0, 0)
    signal_key = "XAUUSD:5m:2026-08-22T14:00:00:XAU-CONFLUENCE-V1.0:false"

    sig1 = Signal(
        signal_key=signal_key,
        symbol="XAUUSD",
        timeframe="5m",
        timestamp=now,
        direction="BUY",
        strategy_preset="INTRADAY",
        strategy_version="XAU-CONFLUENCE-V1.0",
        score=85,
        score_grade="A",
        entry_price=2500.0,
        stop_loss=2492.0,
        tp1=2508.0,
        tp2=2516.0,
        tp3=2524.0,
        risk_distance=8.0,
        reward_tp1=8.0,
        reward_tp2=16.0,
        reward_tp3=24.0,
        status="OPEN",
        is_demo=False
    )
    db.add(sig1)
    db.commit()

    # Attempting to add duplicate signal_key must fail due to unique constraint
    sig_dup = Signal(
        signal_key=signal_key,
        symbol="XAUUSD",
        timeframe="5m",
        timestamp=now,
        direction="BUY",
        strategy_preset="INTRADAY",
        strategy_version="XAU-CONFLUENCE-V1.0",
        score=85,
        score_grade="A",
        entry_price=2500.0,
        stop_loss=2492.0,
        tp1=2508.0,
        tp2=2516.0,
        tp3=2524.0,
        risk_distance=8.0,
        reward_tp1=8.0,
        reward_tp2=16.0,
        reward_tp3=24.0,
        status="OPEN",
        is_demo=False
    )
    db.add(sig_dup)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    db.close()


def test_is_demo_segregation():
    db = SessionLocal()
    now = datetime(2026, 8, 22, 14, 0, 0)
    
    real_sig = Signal(
        signal_key="real_sig_1",
        symbol="XAUUSD",
        timeframe="15m",
        timestamp=now,
        direction="BUY",
        score=92,
        score_grade="A+",
        entry_price=2500.0,
        stop_loss=2495.0,
        tp1=2505.0,
        tp2=2510.0,
        tp3=2515.0,
        risk_distance=5.0,
        reward_tp1=5.0,
        reward_tp2=10.0,
        reward_tp3=15.0,
        is_demo=False
    )
    demo_sig = Signal(
        signal_key="demo_sig_1",
        symbol="XAUUSD",
        timeframe="15m",
        timestamp=now,
        direction="SELL",
        score=88,
        score_grade="A",
        entry_price=2500.0,
        stop_loss=2505.0,
        tp1=2495.0,
        tp2=2490.0,
        tp3=2485.0,
        risk_distance=5.0,
        reward_tp1=5.0,
        reward_tp2=10.0,
        reward_tp3=15.0,
        is_demo=True
    )
    db.add_all([real_sig, demo_sig])
    db.commit()

    real_results = db.query(Signal).filter(Signal.is_demo == False).all()
    demo_results = db.query(Signal).filter(Signal.is_demo == True).all()

    assert len(real_results) == 1
    assert real_results[0].signal_key == "real_sig_1"
    assert len(demo_results) == 1
    assert demo_results[0].signal_key == "demo_sig_1"
    db.close()
