import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from app.execution.base import ExecutionAdapter, ExecutionOrder
from app.models.schema import TradeExecution

class PaperExecutionAdapter(ExecutionAdapter):
    def __init__(self, db: Session, spread_pips: float = 0.20, account_balance: float = 10000.0):
        self.db = db
        self.spread_pips = spread_pips
        self.account_balance = account_balance

    def place_order(
        self,
        symbol: str,
        direction: str,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        risk_percent: float = 1.0,
        signal_id: Optional[int] = None
    ) -> ExecutionOrder:
        ticket_id = f"PAPER-{uuid.uuid4().hex[:8].upper()}"
        lot_size = self.calculate_lot_size(risk_percent, self.account_balance, entry_price, stop_loss)
        
        # Apply simulated spread
        fill_price = entry_price + self.spread_pips if direction == "BUY" else entry_price - self.spread_pips
        now = datetime.utcnow()

        execution_record = TradeExecution(
            ticket_id=ticket_id,
            signal_id=signal_id,
            symbol=symbol.upper(),
            direction=direction.upper(),
            order_type="MARKET",
            execution_mode="PAPER",
            lot_size=lot_size,
            entry_price=round(entry_price, 2),
            fill_price=round(fill_price, 2),
            stop_loss=round(stop_loss, 2),
            take_profit=round(take_profit, 2),
            status="FILLED",
            pnl=0.0,
            executed_at=now
        )

        self.db.add(execution_record)
        self.db.commit()
        self.db.refresh(execution_record)

        return ExecutionOrder(
            ticket_id=ticket_id,
            symbol=symbol.upper(),
            direction=direction.upper(),
            lot_size=lot_size,
            entry_price=round(entry_price, 2),
            fill_price=round(fill_price, 2),
            stop_loss=round(stop_loss, 2),
            take_profit=round(take_profit, 2),
            execution_mode="PAPER",
            status="FILLED",
            pnl=0.0,
            executed_at=now
        )

    def close_order(self, ticket_id: str, close_price: float) -> Optional[ExecutionOrder]:
        record = self.db.query(TradeExecution).filter(TradeExecution.ticket_id == ticket_id).first()
        if not record or record.status == "CLOSED":
            return None

        # Calculate PnL = (close_price - fill_price) * lot_size * 100
        direction_mult = 1.0 if record.direction == "BUY" else -1.0
        pnl = round((close_price - record.fill_price) * direction_mult * record.lot_size * 100.0, 2)
        now = datetime.utcnow()

        record.status = "CLOSED"
        record.close_price = round(close_price, 2)
        record.pnl = pnl
        record.closed_at = now
        self.db.commit()

        return ExecutionOrder(
            ticket_id=record.ticket_id,
            symbol=record.symbol,
            direction=record.direction,
            lot_size=record.lot_size,
            entry_price=record.entry_price,
            fill_price=record.fill_price,
            stop_loss=record.stop_loss,
            take_profit=record.take_profit,
            execution_mode=record.execution_mode,
            status="CLOSED",
            pnl=pnl,
            executed_at=record.executed_at
        )
