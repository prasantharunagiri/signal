from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime

class ExecutionOrder(BaseModel):
    ticket_id: str
    symbol: str
    direction: str
    lot_size: float
    entry_price: float
    fill_price: float
    stop_loss: float
    take_profit: float
    execution_mode: str
    status: str
    error_message: Optional[str] = None
    pnl: float = 0.0
    executed_at: datetime

class ExecutionAdapter(ABC):
    def calculate_lot_size(self, risk_percent: float, account_balance: float, entry_price: float, stop_loss: float) -> float:
        risk_amount = (risk_percent / 100.0) * account_balance
        sl_distance = abs(entry_price - stop_loss)
        if sl_distance <= 0:
            sl_distance = 2.0
        # 1 lot XAUUSD = 100 oz ($100 per $1 price move)
        lots = round(risk_amount / (sl_distance * 100.0), 2)
        return max(0.01, min(lots, 10.0))

    @abstractmethod
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
        """Executes a trade order."""
        pass

    @abstractmethod
    def close_order(self, ticket_id: str, close_price: float) -> Optional[ExecutionOrder]:
        """Closes an active position."""
        pass
