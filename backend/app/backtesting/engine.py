from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel
from app.providers.base import Candle, MarketDataProvider
from app.strategies.engine import run_strategy_pipeline, StrategySignalOutput

class BacktestTradeRecord(BaseModel):
    signal: StrategySignalOutput
    outcome: str  # OPEN, TP1_HIT, TP2_HIT, TP3_HIT, SL_HIT, EXPIRED, AMBIGUOUS
    realized_r: float
    exit_price: float
    exit_time: datetime
    duration_mins: float

class BacktestSummary(BaseModel):
    symbol: str
    timeframe: str
    strategy_preset: str
    strategy_version: str
    start_date: datetime
    end_date: datetime
    total_signals: int
    wins: int
    losses: int
    ambiguous: int
    expired: int
    win_rate: float
    avg_r: float
    total_r: float
    expectancy: float
    max_drawdown: float
    max_consecutive_losses: int
    profit_factor: float
    avg_duration_mins: float
    trades: List[BacktestTradeRecord]

class ChronologicalBacktester:
    def __init__(self, data_provider: MarketDataProvider):
        self.data_provider = data_provider

    def run_backtest(
        self,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
        strategy_preset: str = "INTRADAY",
        strategy_version: str = "XAU-CONFLUENCE-V1.0",
        min_score: int = 70,
        comparison_symbol: Optional[str] = "DXY",
        lower_timeframe: Optional[str] = "1m"
    ) -> BacktestSummary:
        """
        Executes strict chronological backtest candle by candle with ZERO look-ahead bias.
        """
        primary_candles = self.data_provider.fetch_candles(
            symbol=symbol, timeframe=timeframe, start_time=start_date, end_time=end_date, limit=50000
        )
        comparison_candles = None
        if comparison_symbol:
            comparison_candles = self.data_provider.fetch_candles(
                symbol=comparison_symbol, timeframe=timeframe, start_time=start_date, end_time=end_date, limit=50000
            )

        if not primary_candles or len(primary_candles) < 20:
            return BacktestSummary(
                symbol=symbol, timeframe=timeframe, strategy_preset=strategy_preset,
                strategy_version=strategy_version, start_date=start_date, end_date=end_date,
                total_signals=0, wins=0, losses=0, ambiguous=0, expired=0, win_rate=0.0,
                avg_r=0.0, total_r=0.0, expectancy=0.0, max_drawdown=0.0, max_consecutive_losses=0,
                profit_factor=0.0, avg_duration_mins=0.0, trades=[]
            )

        ltf_candles_map = {}
        if lower_timeframe:
            ltf_list = self.data_provider.fetch_candles(
                symbol=symbol, timeframe=lower_timeframe, start_time=start_date, end_time=end_date, limit=100000
            )
            for c in ltf_list:
                ltf_candles_map[c.timestamp] = c

        trades: List[BacktestTradeRecord] = []
        open_signals: List[StrategySignalOutput] = []

        # Chronological step-by-step iteration
        for idx in range(15, len(primary_candles)):
            curr_candle = primary_candles[idx]

            # 1. Evaluate open trades against current candle
            still_open = []
            for sig in open_signals:
                outcome, exit_p, exit_t, duration, realized_r = self._evaluate_candle_outcome(
                    sig, curr_candle, ltf_candles_map
                )

                if outcome in ["TP3_HIT", "SL_HIT", "SL_AFTER_TP", "AMBIGUOUS"]:
                    trades.append(
                        BacktestTradeRecord(
                            signal=sig,
                            outcome=outcome,
                            realized_r=realized_r,
                            exit_price=exit_p,
                            exit_time=exit_t,
                            duration_mins=duration
                        )
                    )
                else:
                    if outcome in ["TP1_HIT", "TP2_HIT"]:
                        sig.status = outcome
                    still_open.append(sig)

            open_signals = still_open

            # 2. Evaluate strategy engine at current timestamp
            sig_candidate = run_strategy_pipeline(
                primary_candles=primary_candles,
                comparison_candles=comparison_candles,
                current_idx=idx,
                strategy_preset=strategy_preset,
                strategy_version=strategy_version,
                min_score=min_score
            )

            if sig_candidate:
                # Idempotency / duplicate check against open trades
                if not any(s.signal_key == sig_candidate.signal_key for s in open_signals):
                    open_signals.append(sig_candidate)

        # Record remaining open signals at backtest end
        for sig in open_signals:
            final_outcome = sig.status if sig.status != "OPEN" else "EXPIRED"
            r_val = 3.0 if sig.status == "TP3_HIT" else (2.0 if sig.status == "TP2_HIT" else (1.0 if sig.status in ["TP1_HIT", "SL_AFTER_TP"] else 0.0))
            trades.append(
                BacktestTradeRecord(
                    signal=sig,
                    outcome=final_outcome,
                    realized_r=r_val,
                    exit_price=primary_candles[-1].close,
                    exit_time=primary_candles[-1].timestamp,
                    duration_mins=(primary_candles[-1].timestamp - sig.timestamp).total_seconds() / 60.0
                )
            )

        return self._compile_summary(symbol, timeframe, strategy_preset, strategy_version, start_date, end_date, trades)

    def _evaluate_candle_outcome(
        self,
        sig: StrategySignalOutput,
        candle: Candle,
        ltf_map: Dict[datetime, Candle]
    ) -> tuple:
        """
        Evaluates whether a candle hits SL, TP1, TP2, or TP3.
        Returns: (outcome_status, exit_price, exit_time, duration_mins, realized_r)
        """
        duration = (candle.timestamp - sig.timestamp).total_seconds() / 60.0

        # --- EXPIRY LOGIC ---
        is_expired = False
        
        # 1. Max Duration Fallback
        max_durations_mins = {
            "SCALP": 4 * 60,
            "INTRADAY": 24 * 60,
            "SWING": 72 * 60
        }
        max_dur = max_durations_mins.get(sig.strategy_preset, 24 * 60)
        if duration >= max_dur:
            is_expired = True
            
        # 2. Session Expiry
        if not is_expired and sig.session:
            current_hour = candle.timestamp.hour
            if sig.session.upper() == "ASIAN":
                if 7 <= current_hour < 21:
                    is_expired = True
            elif sig.session.upper() in ["LONDON", "NEW YORK"]:
                if current_hour >= 21 or current_hour < 7:
                    is_expired = True

        if is_expired:
            return "EXPIRED", candle.close, candle.timestamp, duration, 0.0

        if sig.direction == "BUY":
            hit_sl = candle.low <= sig.stop_loss
            hit_tp3 = candle.high >= sig.tp3
            hit_tp2 = candle.high >= sig.tp2
            hit_tp1 = candle.high >= sig.tp1

            if hit_sl and (hit_tp1 or hit_tp2 or hit_tp3) and sig.status == "OPEN":
                # Same candle ambiguity check
                return "AMBIGUOUS", candle.close, candle.timestamp, duration, 0.0

            if hit_tp3:
                return "TP3_HIT", sig.tp3, candle.timestamp, duration, 3.0
            elif hit_tp2 and sig.status in ["OPEN", "TP1_HIT"]:
                return "TP2_HIT", sig.tp2, candle.timestamp, duration, 2.0
            elif hit_tp1 and sig.status == "OPEN":
                return "TP1_HIT", sig.tp1, candle.timestamp, duration, 1.0
            elif hit_sl:
                if sig.status in ["TP1_HIT", "TP2_HIT"]:
                    return "SL_AFTER_TP", sig.stop_loss, candle.timestamp, duration, 1.0
                return "SL_HIT", sig.stop_loss, candle.timestamp, duration, -1.0

        else:  # SELL
            hit_sl = candle.high >= sig.stop_loss
            hit_tp3 = candle.low <= sig.tp3
            hit_tp2 = candle.low <= sig.tp2
            hit_tp1 = candle.low <= sig.tp1

            if hit_sl and (hit_tp1 or hit_tp2 or hit_tp3) and sig.status == "OPEN":
                return "AMBIGUOUS", candle.close, candle.timestamp, duration, 0.0

            if hit_tp3:
                return "TP3_HIT", sig.tp3, candle.timestamp, duration, 3.0
            elif hit_tp2 and sig.status in ["OPEN", "TP1_HIT"]:
                return "TP2_HIT", sig.tp2, candle.timestamp, duration, 2.0
            elif hit_tp1 and sig.status == "OPEN":
                return "TP1_HIT", sig.tp1, candle.timestamp, duration, 1.0
            elif hit_sl:
                if sig.status in ["TP1_HIT", "TP2_HIT"]:
                    return "SL_AFTER_TP", sig.stop_loss, candle.timestamp, duration, 1.0
                return "SL_HIT", sig.stop_loss, candle.timestamp, duration, -1.0

        return "OPEN", 0.0, candle.timestamp, duration, 0.0

    def _compile_summary(
        self, symbol: str, timeframe: str, preset: str, version: str,
        start_date: datetime, end_date: datetime, trades: List[BacktestTradeRecord]
    ) -> BacktestSummary:
        if not trades:
            return BacktestSummary(
                symbol=symbol, timeframe=timeframe, strategy_preset=preset, strategy_version=version,
                start_date=start_date, end_date=end_date, total_signals=0, wins=0, losses=0,
                ambiguous=0, expired=0, win_rate=0.0, avg_r=0.0, total_r=0.0, expectancy=0.0,
                max_drawdown=0.0, max_consecutive_losses=0, profit_factor=0.0, avg_duration_mins=0.0, trades=[]
            )

        wins = sum(1 for t in trades if t.outcome in ["TP1_HIT", "TP2_HIT", "TP3_HIT"])
        losses = sum(1 for t in trades if t.outcome == "SL_HIT")
        ambiguous = sum(1 for t in trades if t.outcome == "AMBIGUOUS")
        expired = sum(1 for t in trades if t.outcome == "EXPIRED")

        win_rate = (wins / len(trades)) * 100.0 if trades else 0.0
        r_values = [t.realized_r for t in trades]
        total_r = sum(r_values)
        avg_r = total_r / len(trades) if trades else 0.0

        win_r_sum = sum(t.realized_r for t in trades if t.realized_r > 0)
        loss_r_sum = abs(sum(t.realized_r for t in trades if t.realized_r < 0))
        profit_factor = round(win_r_sum / loss_r_sum, 2) if loss_r_sum > 0 else (win_r_sum if win_r_sum > 0 else 0.0)

        # Drawdown calculation in R
        cum_r = 0.0
        peak = 0.0
        max_dd = 0.0
        curr_loss_streak = 0
        max_loss_streak = 0

        for t in trades:
            cum_r += t.realized_r
            if cum_r > peak:
                peak = cum_r
            dd = peak - cum_r
            if dd > max_dd:
                max_dd = dd

            if t.outcome == "SL_HIT":
                curr_loss_streak += 1
                if curr_loss_streak > max_loss_streak:
                    max_loss_streak = curr_loss_streak
            else:
                curr_loss_streak = 0

        avg_dur = sum(t.duration_mins for t in trades) / len(trades) if trades else 0.0

        return BacktestSummary(
            symbol=symbol,
            timeframe=timeframe,
            strategy_preset=preset,
            strategy_version=version,
            start_date=start_date,
            end_date=end_date,
            total_signals=len(trades),
            wins=wins,
            losses=losses,
            ambiguous=ambiguous,
            expired=expired,
            win_rate=round(win_rate, 2),
            avg_r=round(avg_r, 2),
            total_r=round(total_r, 2),
            expectancy=round(avg_r, 2),
            max_drawdown=round(max_dd, 2),
            max_consecutive_losses=max_loss_streak,
            profit_factor=profit_factor,
            avg_duration_mins=round(avg_dur, 1),
            trades=trades
        )
