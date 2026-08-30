import pytest
from datetime import datetime
from app.database import Base, engine, SessionLocal
from app.models.schema import Signal
from app.workers.notification_worker import NotificationDispatcher

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_notification_formatting_and_idempotency():
    dispatcher = NotificationDispatcher()
    now = datetime(2026, 8, 22, 14, 0)

    sig = Signal(
        id=1,
        signal_key="XAUUSD:5m:2026-08-22T14:00:00:v1:false",
        symbol="XAUUSD",
        timeframe="5m",
        timestamp=now,
        direction="BUY",
        strategy_preset="SWING",
        strategy_version="XAU-CONFLUENCE-V1.0",
        score=87,
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
        session="London",
        explanation="Liquidity sweep + SMT divergence + bullish MSS + FVG",
        status="OPEN",
        is_demo=False
    )

    msg = dispatcher.format_signal_message(sig)
    assert "🟡 XAUUSD SIGNAL — SWING" in msg
    assert "Direction: LONG" in msg
    assert "Entry: 2500.00" in msg
    assert "Score: 87/100" in msg
    assert "2026-08-22 14:00:00 UTC" in msg
