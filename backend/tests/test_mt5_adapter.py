import sys
import pytest
from unittest.mock import MagicMock
from app.database import Base, engine, SessionLocal
from app.providers.mt5_provider import MT5Provider
from app.execution.mt5_adapter import MT5ExecutionAdapter

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_mt5_provider_initialization():
    provider = MT5Provider()
    assert provider.connected is False

    # Calling fetch_candles without MT5 module should return empty list gracefully without throwing an unhandled exception
    candles = provider.fetch_candles("XAUUSD", "5m", limit=10)
    assert isinstance(candles, list)

def test_mt5_unavailable():
    # Ensure MetaTrader5 is not in sys.modules
    if 'MetaTrader5' in sys.modules:
        del sys.modules['MetaTrader5']
    
    db = SessionLocal()
    adapter = MT5ExecutionAdapter(db)
    order = adapter.place_order("XAUUSD", "BUY", 2500.0, 2490.0, 2520.0, 1.0)
    
    assert order.status == "FAILED"
    assert "unavailable" in order.error_message
    db.close()

def test_mt5_initialize_fails():
    mock_mt5 = MagicMock()
    mock_mt5.initialize.return_value = False
    mock_mt5.last_error.return_value = "Init failed"
    sys.modules['MetaTrader5'] = mock_mt5
    
    db = SessionLocal()
    adapter = MT5ExecutionAdapter(db)
    order = adapter.place_order("XAUUSD", "BUY", 2500.0, 2490.0, 2520.0, 1.0)
    
    assert order.status == "FAILED"
    assert "Init failed" in order.error_message
    
    db.close()
    if 'MetaTrader5' in sys.modules:
        del sys.modules['MetaTrader5']

def test_mt5_order_send_fails():
    mock_mt5 = MagicMock()
    mock_mt5.initialize.return_value = True
    
    class MockAccountInfo:
        balance = 10000.0
    mock_mt5.account_info.return_value = MockAccountInfo()
    
    class MockResult:
        retcode = 10013 # TRADE_RETCODE_INVALID
        comment = "Invalid volume"
    mock_mt5.order_send.return_value = MockResult()
    mock_mt5.TRADE_RETCODE_DONE = 10009
    
    sys.modules['MetaTrader5'] = mock_mt5
    
    db = SessionLocal()
    adapter = MT5ExecutionAdapter(db)
    order = adapter.place_order("XAUUSD", "BUY", 2500.0, 2490.0, 2520.0, 1.0)
    
    assert order.status == "FAILED"
    assert "10013" in order.error_message
    assert "Invalid volume" in order.error_message
    
    db.close()
    if 'MetaTrader5' in sys.modules:
        del sys.modules['MetaTrader5']
