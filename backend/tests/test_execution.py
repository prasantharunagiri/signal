import pytest
from app.database import Base, engine, SessionLocal
from app.execution.paper_adapter import PaperExecutionAdapter
from app.execution.mt5_adapter import MT5ExecutionAdapter

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_paper_execution_order_placement():
    db = SessionLocal()
    adapter = PaperExecutionAdapter(db, spread_pips=0.20, account_balance=10000.0)

    order = adapter.place_order(
        symbol="XAUUSD",
        direction="BUY",
        entry_price=2500.0,
        stop_loss=2495.0,
        take_profit=2515.0,
        risk_percent=1.0
    )

    assert order.ticket_id.startswith("PAPER-")
    assert order.symbol == "XAUUSD"
    assert order.direction == "BUY"
    assert order.fill_price == 2500.20
    assert order.lot_size > 0.0

    closed = adapter.close_order(order.ticket_id, close_price=2510.0)
    assert closed is not None
    assert closed.status == "CLOSED"
    assert closed.pnl > 0.0
    db.close()

def test_mt5_execution_adapter_fallback():
    db = SessionLocal()
    adapter = MT5ExecutionAdapter(db)

    order = adapter.place_order(
        symbol="XAUUSD",
        direction="SELL",
        entry_price=2500.0,
        stop_loss=2505.0,
        take_profit=2490.0,
        risk_percent=1.0
    )

    assert order.ticket_id.startswith("MT5-")
    assert order.symbol == "XAUUSD"
    assert order.direction == "SELL"
    assert order.status == "FAILED"
    assert "MetaTrader5 package" in order.error_message or "failed" in order.error_message
    db.close()

def test_dynamic_lot_sizing():
    db = SessionLocal()
    adapter = MT5ExecutionAdapter(db)
    
    # 1% risk on $10k account = $100 risk.
    # $3 move = $300 per lot. Lots = 100 / 300 = 0.33
    lot_scalp = adapter.calculate_lot_size(risk_percent=1.0, account_balance=10000.0, entry_price=2500.0, stop_loss=2497.0)
    
    # $25 move = $2500 per lot. Lots = 100 / 2500 = 0.04
    lot_swing = adapter.calculate_lot_size(risk_percent=1.0, account_balance=10000.0, entry_price=2500.0, stop_loss=2475.0)
    
    assert lot_scalp > lot_swing
    assert lot_scalp == 0.33
    assert lot_swing == 0.04
    db.close()
