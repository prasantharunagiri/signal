import asyncio
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.config import settings
from app.api.market import get_provider
from app.strategies.engine import run_strategy_pipeline
from app.models.schema import Signal, SystemLog
from app.workers.notification_worker import NotificationDispatcher
from app.api.websocket import ws_manager
from app.api.execution import AUTO_TRADER_ENABLED, CURRENT_EXECUTION_MODE
from app.execution.paper_adapter import PaperExecutionAdapter
from app.execution.mt5_adapter import MT5ExecutionAdapter
from app.outcomes.tracker import OutcomeTracker

logger = logging.getLogger("signal_evaluator")

class LiveSignalEvaluator:
    def __init__(self):
        self.timeframes = ["5m", "15m", "1h", "4h"]
        self.dispatcher = NotificationDispatcher()
        self.outcome_tracker = OutcomeTracker()
        self.last_candle_timestamps = {}

    async def evaluate_once(self):
        db: Session = SessionLocal()
        try:
            provider = get_provider()
            sym = "XAUUSD"
            for tf in self.timeframes:
                candles = provider.fetch_candles(symbol=sym, timeframe=tf, limit=100)
                macro_candles = provider.fetch_candles(symbol=sym, timeframe="1h", limit=40)
                if not candles or len(candles) < 20:
                    continue

                latest_candle = candles[-1]
                
                # Check for new candle based on timestamp
                last_ts = self.last_candle_timestamps.get(f"{sym}:{tf}")
                if last_ts == latest_candle.timestamp:
                    continue
                    
                self.last_candle_timestamps[f"{sym}:{tf}"] = latest_candle.timestamp

                # Process open signal outcomes against latest candle
                new_events = self.outcome_tracker.process_open_signals(db, latest_candle)
                for ev in new_events:
                    await ws_manager.broadcast({
                        "event": "SIGNAL_UPDATED",
                        "signal_id": ev.signal_id,
                        "status": ev.event_type,
                        "price": ev.price
                    })

                # Broadcast live price tick event via WebSocket
                await ws_manager.broadcast({
                    "event": "PRICE_TICK",
                    "symbol": sym,
                    "timeframe": tf,
                    "close": latest_candle.close,
                    "high": latest_candle.high,
                    "low": latest_candle.low,
                    "open": latest_candle.open,
                    "timestamp": latest_candle.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                })

                for preset in ["SCALP", "INTRADAY", "SWING"]:
                    sig_output = run_strategy_pipeline(
                        primary_candles=candles[:-1],
                        macro_candles=macro_candles[:-1] if macro_candles else None,
                        strategy_preset=preset,
                        strategy_version="XAU-CONFLUENCE-V1.0",
                        min_score=settings.SCORE_THRESHOLD_B
                    )
                    if sig_output:
                        # Check duplicate
                        existing = db.query(Signal).filter(Signal.signal_key == sig_output.signal_key).first()
                        if not existing:
                            new_sig = Signal(
                                signal_key=sig_output.signal_key,
                                symbol=sig_output.symbol,
                                timeframe=sig_output.timeframe,
                                timestamp=sig_output.timestamp,
                                direction=sig_output.direction,
                                strategy_preset=sig_output.strategy_preset,
                                strategy_version=sig_output.strategy_version,
                                score=sig_output.score,
                                score_grade=sig_output.score_grade,
                                entry_price=sig_output.entry_price,
                                stop_loss=sig_output.stop_loss,
                                tp1=sig_output.tp1,
                                tp2=sig_output.tp2,
                                tp3=sig_output.tp3,
                                risk_distance=sig_output.risk_distance,
                                reward_tp1=sig_output.reward_tp1,
                                reward_tp2=sig_output.reward_tp2,
                                reward_tp3=sig_output.reward_tp3,
                                session=sig_output.session,
                                liquidity_type=sig_output.liquidity_type,
                                smt_status=sig_output.smt_status,
                                mss_status=sig_output.mss_status,
                                displacement_status=sig_output.displacement_status,
                                fvg_status=sig_output.fvg_status,
                                status="OPEN",
                                explanation=sig_output.explanation,
                                is_demo=False
                            )
                            db.add(new_sig)
                            db.commit()
                            db.refresh(new_sig)
                            
                            self.outcome_tracker.add_signal(new_sig)

                            # Broadcast NEW_SIGNAL event over WebSockets
                            await ws_manager.broadcast({
                                "event": "NEW_SIGNAL",
                                "signal": {
                                    "id": new_sig.id,
                                    "symbol": new_sig.symbol,
                                    "timeframe": new_sig.timeframe,
                                    "direction": new_sig.direction,
                                    "preset": new_sig.strategy_preset,
                                    "score": new_sig.score,
                                    "grade": new_sig.score_grade,
                                    "entry": new_sig.entry_price,
                                    "stop_loss": new_sig.stop_loss,
                                    "tp1": new_sig.tp1,
                                    "tp2": new_sig.tp2,
                                    "tp3": new_sig.tp3
                                }
                            })

                            # Dispatch notification asynchronously
                            def bg_dispatch(sig_id: int):
                                from app.database import SessionLocal
                                bg_db = SessionLocal()
                                try:
                                    bg_sig = bg_db.query(Signal).get(sig_id)
                                    if bg_sig:
                                        self.dispatcher.dispatch_signal_alert(bg_db, bg_sig)
                                finally:
                                    bg_db.close()

                            asyncio.create_task(asyncio.to_thread(bg_dispatch, new_sig.id))

                            # Log system event
                            log_msg = f"LIVE SIGNAL GENERATED: {new_sig.direction} {new_sig.symbol} {new_sig.timeframe} Score: {new_sig.score}/100"
                            db.add(SystemLog(level="INFO", component="SIGNAL_ENGINE", message=log_msg))
                            db.commit()

                            # Auto-Execution for Grade A+ signals (score >= 90) asynchronously
                            if AUTO_TRADER_ENABLED and new_sig.score >= settings.SCORE_THRESHOLD_A_PLUS:
                                def bg_execute(sig_id: int):
                                    from app.database import SessionLocal
                                    bg_db = SessionLocal()
                                    try:
                                        bg_sig = bg_db.query(Signal).get(sig_id)
                                        if bg_sig:
                                            if CURRENT_EXECUTION_MODE == "MT5":
                                                exec_adapter = MT5ExecutionAdapter(bg_db)
                                            else:
                                                exec_adapter = PaperExecutionAdapter(bg_db)

                                            order = exec_adapter.place_order(
                                                symbol=bg_sig.symbol,
                                                direction=bg_sig.direction,
                                                entry_price=bg_sig.entry_price,
                                                stop_loss=bg_sig.stop_loss,
                                                take_profit=bg_sig.tp3,
                                                risk_percent=1.0,
                                                signal_id=bg_sig.id
                                            )
                                            
                                            if order.status == "FAILED":
                                                logger.error(f"Auto-execution failed for signal {bg_sig.id}: {order.error_message}")
                                            else:
                                                logger.info(f"Auto-execution placed for signal {bg_sig.id}, ticket: {order.ticket_id}")
                                                
                                            # We need to broadcast the execution filled event inside the thread
                                            # Using asyncio.run is dangerous in a thread if it conflicts, but we can use asyncio.run_coroutine_threadsafe
                                            # Actually, simpler: just broadcast synchronously using httpx or create a new event loop
                                            # For now we'll just log it. The WebSocket client fetches recent executions on mount anyway.
                                    finally:
                                        bg_db.close()
                                        
                                asyncio.create_task(asyncio.to_thread(bg_execute, new_sig.id))

        except Exception as e:
            logger.error(f"Error during signal evaluation: {e}")
        finally:
            db.close()

async def start_signal_evaluator_loop(interval_seconds: int = 60):
    evaluator = LiveSignalEvaluator()
    while True:
        try:
            await evaluator.evaluate_once()
        except Exception as e:
            logger.error(f"Signal evaluator loop error: {e}")
        await asyncio.sleep(interval_seconds)

async def start_live_price_ticker_loop(interval_seconds: int = 1):
    import random
    last_close = 2500.00
    while True:
        try:
            provider = get_provider()
            latest = provider.get_latest_candle(symbol="XAUUSD", timeframe="5m")
            if latest:
                last_close = latest.close

            # Sub-second tick animation
            tick_price = round(last_close + random.uniform(-0.12, 0.12), 2)
            now = datetime.utcnow()

            await ws_manager.broadcast({
                "event": "PRICE_TICK",
                "symbol": "XAUUSD",
                "timeframe": "5m",
                "close": tick_price,
                "high": round(max(last_close, tick_price) + 0.05, 2),
                "low": round(min(last_close, tick_price) - 0.05, 2),
                "open": round(last_close, 2),
                "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
                "time_unix": int(now.timestamp())
            })
            
            # Broadcast state updates every 5 seconds
            if int(now.timestamp()) % 5 == 0:
                from app.api.market import get_current_session
                from app.providers.data_source_manager import data_source_manager
                await ws_manager.broadcast({
                    "event": "SESSION_CHANGED",
                    "data": get_current_session()
                })
                await ws_manager.broadcast({
                    "event": "PROVIDER_STATUS_CHANGED",
                    "data": data_source_manager.get_status()
                })
        except Exception as e:
            logger.error(f"Live ticker loop error: {e}")
        await asyncio.sleep(interval_seconds)
