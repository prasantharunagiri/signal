import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from app.execution.base import ExecutionAdapter, ExecutionOrder
from app.models.schema import TradeExecution
from app.config import settings

class MT5ExecutionAdapter(ExecutionAdapter):
    def __init__(self, db: Session):
        self.db = db

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
        ticket_id = f"MT5-{uuid.uuid4().hex[:8].upper()}"
        now = datetime.utcnow()
        fill_price = entry_price
        
        status = "FILLED"
        error_msg = None
        account_balance = 10000.0  # fallback
        lot_size = 0.1 # default fallback

        try:
            import MetaTrader5 as mt5
            
            # Attempt MetaTrader5 Python package initialization
            if not mt5.initialize(login=settings.MT5_LOGIN, password=settings.MT5_PASSWORD, server=settings.MT5_SERVER):
                raise Exception(f"MT5 initialization failed: {mt5.last_error()}")
            
            account_info = mt5.account_info()
            if account_info is not None:
                account_balance = account_info.balance
                
            lot_size = self.calculate_lot_size(risk_percent, account_balance, entry_price, stop_loss)

            order_type = mt5.ORDER_TYPE_BUY if direction == "BUY" else mt5.ORDER_TYPE_SELL
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": lot_size,
                "type": order_type,
                "price": entry_price,
                "sl": stop_loss,
                "tp": take_profit,
                "deviation": 20,
                "magic": 234000,
                "comment": "XAUUSD Auto Engine",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            res = mt5.order_send(request)
            
            if res is None:
                raise Exception(f"mt5.order_send() failed, error: {mt5.last_error()}")
            elif res.retcode != mt5.TRADE_RETCODE_DONE:
                raise Exception(f"Broker rejected order, retcode={res.retcode}, comment={getattr(res, 'comment', '')}")
            else:
                ticket_id = str(res.order)
                fill_price = res.price
                
        except ImportError:
            status = "FAILED"
            error_msg = "MetaTrader5 package is unavailable."
            lot_size = self.calculate_lot_size(risk_percent, account_balance, entry_price, stop_loss)
        except Exception as e:
            status = "FAILED"
            error_msg = str(e)
            lot_size = self.calculate_lot_size(risk_percent, account_balance, entry_price, stop_loss)
            
        if status == "FAILED":
            from app.models.schema import SystemLog, Signal
            from app.workers.notification_worker import NotificationDispatcher
            sys_log = SystemLog(level="ERROR", component="EXECUTION", message=f"MT5 execution failed: {error_msg}")
            self.db.add(sys_log)
            
            signal = self.db.query(Signal).filter(Signal.id == signal_id).first() if signal_id else None
            dispatcher = NotificationDispatcher()
            dispatcher.dispatch_execution_failure(self.db, error_message=error_msg, signal=signal)

        execution_record = TradeExecution(
            ticket_id=ticket_id,
            signal_id=signal_id,
            symbol=symbol.upper(),
            direction=direction.upper(),
            order_type="MARKET",
            execution_mode="MT5",
            lot_size=lot_size,
            entry_price=round(entry_price, 2),
            fill_price=round(fill_price, 2),
            stop_loss=round(stop_loss, 2),
            take_profit=round(take_profit, 2),
            status=status,
            error_message=error_msg,
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
            execution_mode="MT5",
            status=status,
            error_message=error_msg,
            pnl=0.0,
            executed_at=now
        )

    def close_order(self, ticket_id: str, close_price: float) -> Optional[ExecutionOrder]:
        record = self.db.query(TradeExecution).filter(TradeExecution.ticket_id == ticket_id).first()
        if not record or record.status == "CLOSED":
            return None

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
            execution_mode="MT5",
            status="CLOSED",
            pnl=pnl,
            executed_at=record.executed_at
        )
