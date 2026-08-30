import pytest
from datetime import datetime
from app.database import Base, engine, SessionLocal
from app.models.schema import Signal, SignalEvent
from app.providers.base import Candle
from app.outcomes.tracker import OutcomeTracker

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_outcome_tracker_tp1_hit():
    db = SessionLocal()
    now = datetime(2026, 8, 22, 10, 0)

    sig = Signal(
        signal_key="XAUUSD:5m:2026-08-22T10:00:00:v1:false",
        symbol="XAUUSD",
        timeframe="5m",
        timestamp=now,
        direction="BUY",
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
    db.add(sig)
    db.commit()

    tracker = OutcomeTracker()
    candle_tp1 = Candle(
        symbol="XAUUSD", timeframe="5m", timestamp=datetime(2026, 8, 22, 10, 15),
        open=2502.0, high=2510.0, low=2501.0, close=2509.0, is_demo=False
    )

    events = tracker.process_open_signals(db, candle_tp1)
    assert len(events) == 1
    assert events[0].event_type == "TP1_HIT"

    updated_sig = db.query(Signal).filter(Signal.id == sig.id).first()
    assert updated_sig.status == "TP1_HIT"
    db.close()
