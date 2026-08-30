from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.schema import TradeExecution, Signal
from app.execution.paper_adapter import PaperExecutionAdapter
from app.execution.mt5_adapter import MT5ExecutionAdapter

router = APIRouter(prefix="/api/execution", tags=["Trade Execution Engine"])

AUTO_TRADER_ENABLED = True
CURRENT_EXECUTION_MODE = "PAPER"  # PAPER or MT5

class ManualTradeRequest(BaseModel):
    symbol: str = "XAUUSD"
    direction: str = "BUY"  # BUY or SELL
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_percent: float = 1.0
    signal_id: Optional[int] = None
    execution_mode: Optional[str] = "PAPER"

@router.get("/status")
def get_auto_trader_status():
    return {
        "auto_trader_enabled": AUTO_TRADER_ENABLED,
        "execution_mode": CURRENT_EXECUTION_MODE,
        "supported_modes": ["PAPER", "MT5"]
    }

@router.post("/toggle-auto")
def toggle_auto_trader(enabled: Optional[bool] = None, mode: Optional[str] = None):
    global AUTO_TRADER_ENABLED, CURRENT_EXECUTION_MODE
    if enabled is not None:
        AUTO_TRADER_ENABLED = enabled
    if mode in ["PAPER", "MT5"]:
        CURRENT_EXECUTION_MODE = mode
    return get_auto_trader_status()

@router.get("/orders")
def get_executed_orders(limit: int = 50, db: Session = Depends(get_db)):
    return db.query(TradeExecution).order_by(TradeExecution.executed_at.desc()).limit(limit).all()

@router.post("/execute")
def execute_trade_manual(req: ManualTradeRequest, db: Session = Depends(get_db)):
    mode = req.execution_mode.upper() if req.execution_mode else CURRENT_EXECUTION_MODE
    if mode == "MT5":
        adapter = MT5ExecutionAdapter(db)
    else:
        adapter = PaperExecutionAdapter(db)

    order = adapter.place_order(
        symbol=req.symbol,
        direction=req.direction,
        entry_price=req.entry_price,
        stop_loss=req.stop_loss,
        take_profit=req.take_profit,
        risk_percent=req.risk_percent,
        signal_id=req.signal_id
    )
    return order

@router.post("/close/{ticket_id}")
def close_trade_order(ticket_id: str, close_price: float, db: Session = Depends(get_db)):
    order_rec = db.query(TradeExecution).filter(TradeExecution.ticket_id == ticket_id).first()
    if not order_rec:
        raise HTTPException(status_code=404, detail="Execution order ticket not found")

    if order_rec.execution_mode == "MT5":
        adapter = MT5ExecutionAdapter(db)
    else:
        adapter = PaperExecutionAdapter(db)

    closed = adapter.close_order(ticket_id, close_price)
    return closed
