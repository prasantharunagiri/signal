from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.schema import Signal, SignalEvent
from app.providers.base import Candle

class OutcomeTracker:
    def __init__(self):
        self._cache_initialized = False
        self._active_signals = {}  # signal_id -> Signal

    def initialize_cache(self, db: Session):
        if self._cache_initialized:
            return
        # Load all open signals into memory
        open_signals = db.query(Signal).filter(
            Signal.status.in_(["OPEN", "TP1_HIT", "TP2_HIT"])
        ).all()
        for sig in open_signals:
            self._active_signals[sig.id] = sig
        self._cache_initialized = True

    def add_signal(self, signal: Signal):
        self._active_signals[signal.id] = signal

    def process_open_signals(self, db: Session, latest_candle: Candle) -> List[SignalEvent]:
        """
        Evaluates all active (OPEN, TP1_HIT, TP2_HIT) signals for a symbol/timeframe against the latest confirmed candle.
        Returns list of new SignalEvent audit records created.
        """
        self.initialize_cache(db)
        
        # Filter cache in memory
        open_signals = [
            sig for sig in self._active_signals.values()
            if sig.symbol == latest_candle.symbol 
            and sig.timeframe == latest_candle.timeframe
            and sig.is_demo == latest_candle.is_demo
        ]

        new_events = []

        for sig in open_signals:
            if latest_candle.timestamp < sig.timestamp:
                continue

            duration = (latest_candle.timestamp - sig.timestamp).total_seconds() / 60.0

            # --- EXPIRY LOGIC ---
            is_expired = False
            expiry_reason = ""
            
            # 1. Max Duration Fallback
            max_durations_mins = {
                "SCALP": 4 * 60,
                "INTRADAY": 24 * 60,
                "SWING": 72 * 60
            }
            max_dur = max_durations_mins.get(sig.strategy_preset, 24 * 60)
            if duration >= max_dur:
                is_expired = True
                expiry_reason = f"Max duration exceeded ({max_dur} mins)"
                
            # 2. Session Expiry
            # Use UTC hours: London Open ~07:00, NY Close ~21:00
            if not is_expired and sig.session:
                current_hour = latest_candle.timestamp.hour
                
                # If generated in Asian session, expire when London opens
                if sig.session.upper() == "ASIAN":
                    # If the latest candle crosses into 07:00 or later (but not next day Asian which starts at 00:00)
                    if 7 <= current_hour < 21:
                        is_expired = True
                        expiry_reason = "Session expired (London Open)"
                # If generated in London/NY, expire when NY closes
                elif sig.session.upper() in ["LONDON", "NEW YORK"]:
                    if current_hour >= 21 or current_hour < 7:  # End of NY / Start of next day
                        is_expired = True
                        expiry_reason = "Session expired (NY Close)"

            hit_sl = False
            hit_tp1 = False
            hit_tp2 = False
            hit_tp3 = False

            if not is_expired:
                if sig.direction == "BUY":
                    hit_sl = latest_candle.low <= sig.stop_loss
                    hit_tp3 = latest_candle.high >= sig.tp3
                    hit_tp2 = latest_candle.high >= sig.tp2
                    hit_tp1 = latest_candle.high >= sig.tp1
                else:  # SELL
                    hit_sl = latest_candle.high >= sig.stop_loss
                    hit_tp3 = latest_candle.low <= sig.tp3
                    hit_tp2 = latest_candle.low <= sig.tp2
                    hit_tp1 = latest_candle.low <= sig.tp1

            new_status = None
            exit_price = None

            if is_expired:
                new_status = "EXPIRED"
                exit_price = latest_candle.close
            elif hit_sl and (hit_tp1 or hit_tp2 or hit_tp3) and sig.status == "OPEN":
                new_status = "AMBIGUOUS"
                exit_price = latest_candle.close
            elif hit_tp3:
                new_status = "TP3_HIT"
                exit_price = sig.tp3
            elif hit_tp2 and sig.status in ["OPEN", "TP1_HIT"]:
                new_status = "TP2_HIT"
                exit_price = sig.tp2
            elif hit_tp1 and sig.status == "OPEN":
                new_status = "TP1_HIT"
                exit_price = sig.tp1
            elif hit_sl:
                new_status = "SL_AFTER_TP" if sig.status in ["TP1_HIT", "TP2_HIT"] else "SL_HIT"
                exit_price = sig.stop_loss

            if new_status and new_status != sig.status:
                sig.status = new_status
                details_msg = f"Signal status transitioned to {new_status} at price {exit_price} after {duration:.1f} minutes."
                if new_status == "EXPIRED" and expiry_reason:
                    details_msg += f" Reason: {expiry_reason}"
                    
                event = SignalEvent(
                    signal_id=sig.id,
                    event_type=new_status,
                    price=exit_price,
                    timestamp=latest_candle.timestamp,
                    details=details_msg
                )
                db.add(event)
                new_events.append(event)
                
                # Remove from cache if fully closed
                if new_status in ["TP3_HIT", "SL_HIT", "SL_AFTER_TP", "AMBIGUOUS", "EXPIRED"]:
                    self._active_signals.pop(sig.id, None)

        if new_events:
            db.commit()

        return new_events

