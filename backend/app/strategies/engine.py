from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel
from app.providers.base import Candle
from app.strategies.liquidity import detect_swings, detect_pdh_pdl, detect_equal_highs_lows, get_market_session
from app.strategies.sweeps import detect_sweeps
from app.strategies.divergence import detect_smt_divergence
from app.strategies.mss import detect_mss
from app.strategies.displacement import detect_displacement
from app.strategies.fvg import detect_fvgs
from app.strategies.scoring import calculate_confluence_score, ScoreBreakdown
from app.providers.quality import DataQualityChecker

class StrategySignalOutput(BaseModel):
    signal_key: str
    symbol: str
    timeframe: str
    timestamp: datetime
    direction: str
    strategy_preset: str
    strategy_version: str
    score: int
    score_grade: str
    entry_price: float
    stop_loss: float
    tp1: float
    tp2: float
    tp3: float
    risk_distance: float
    reward_tp1: float
    reward_tp2: float
    reward_tp3: float
    session: str
    liquidity_type: Optional[str] = None
    liquidity_level: Optional[float] = None
    smt_status: bool = False
    mss_status: bool = False
    displacement_status: bool = False
    fvg_status: bool = False
    news_status: str = "NORMAL"
    data_quality_status: str = "VALID"
    status: str = "OPEN"
    explanation: str = ""
    is_demo: bool = False

from abc import ABC, abstractmethod

class BaseStrategy(ABC):
    @abstractmethod
    def evaluate(self, primary_candles: List[Candle], **kwargs) -> Optional[StrategySignalOutput]:
        pass

class ConfluenceStrategy(BaseStrategy):
    def evaluate(
        self,
        primary_candles: List[Candle],
        macro_candles: Optional[List[Candle]] = None,
        comparison_candles: Optional[List[Candle]] = None,
        current_idx: Optional[int] = None,
        strategy_preset: str = "INTRADAY",
        strategy_version: str = "XAU-CONFLUENCE-V1.0",
        min_score: int = 70,
        entry_model: str = "MARKET",  # MARKET or FVG
        sl_buffer_pips: float = 1.0,
        news_events: Optional[List[Dict[str, Any]]] = None
    ) -> Optional[StrategySignalOutput]:
        """
        Unified strategy engine pipeline executing deterministic rules:
        Data Quality -> Session -> Macro Bias -> Liquidity -> Sweep -> SMT -> MSS -> Displacement -> FVG -> Score -> Signal
        """
        if not primary_candles:
            return None

        eval_idx = current_idx if current_idx is not None else (len(primary_candles) - 1)
        candles_to_eval = primary_candles[:eval_idx + 1]
        current_candle = candles_to_eval[-1]
        
        # Determine Macro Bias if macro_candles are provided
        macro_bias = "NEUTRAL"
        if macro_candles and len(macro_candles) > 10:
            macro_swings = detect_swings(macro_candles, n=2)
            macro_mss = detect_mss(macro_candles, macro_swings, lookback=10)
            if macro_mss:
                macro_bias = macro_mss.direction

        # 1. Data Quality Check
        quality_checker = DataQualityChecker()
        is_valid_data, quality_reason = quality_checker.validate_candle(
            current_candle, candles_to_eval[:-1] if len(candles_to_eval) > 1 else None
        )
        if not is_valid_data:
            return None

        session = get_market_session(current_candle.timestamp)

        # 2. Liquidity & Swings
        swings = detect_swings(candles_to_eval, n=2, current_idx=eval_idx)
        pdh_pdl = detect_pdh_pdl(candles_to_eval, current_candle.timestamp)
        equals = detect_equal_highs_lows(candles_to_eval)

        all_liquidity = swings + equals
        if pdh_pdl["PDH"]:
            all_liquidity.append(pdh_pdl["PDH"])
        if pdh_pdl["PDL"]:
            all_liquidity.append(pdh_pdl["PDL"])

        # 3. Initial Detection
        sweeps = detect_sweeps(candles_to_eval, all_liquidity, lookback_candles=10)
        mss_res = detect_mss(candles_to_eval, swings, lookback=10)
        disp_res = detect_displacement(candles_to_eval, min_body_ratio=0.60, min_atr_multiple=1.2)
        all_fvgs = detect_fvgs(candles_to_eval, min_fvg_size_pips=0.3, lookback=10)
        fvgs = [f for f in all_fvgs if not f.filled]

        # Determine Direction (BUY / SELL): Prioritize MSS structure break, then Displacement
        raw_dir = "NEUTRAL"
        if mss_res:
            raw_dir = mss_res.direction
        elif disp_res.is_displacement and disp_res.direction != "NEUTRAL":
            raw_dir = disp_res.direction
        elif sweeps:
            raw_dir = sweeps[-1].direction

        if raw_dir == "NEUTRAL":
            return None
            
        direction = "BUY" if raw_dir == "BULLISH" else "SELL"

        # 4. Filter Flags by Direction
        aligned_sweeps = [s for s in sweeps if s.direction == raw_dir]
        has_sweep = len(aligned_sweeps) > 0
        latest_sweep = aligned_sweeps[-1] if aligned_sweeps else None

        has_mss = (mss_res is not None) and (mss_res.direction == raw_dir)
        has_disp = disp_res.is_displacement and (disp_res.direction == raw_dir)

        aligned_fvgs = [f for f in fvgs if f.fvg_type == raw_dir]
        has_fvg = len(aligned_fvgs) > 0

        # 5. SMT / Divergence
        has_smt = False
        if comparison_candles:
            comp_to_eval = comparison_candles[:eval_idx + 1] if len(comparison_candles) > eval_idx else comparison_candles
            smt_res = detect_smt_divergence(candles_to_eval, comp_to_eval, window=5)
            has_smt = smt_res.divergence_type == raw_dir

        # 6. Ensure fresh trigger (Spam Prevention)
        # To avoid firing 10 identical signals while price lingers, we require
        # the trigger event (MSS or Displacement) to happen on the current candle.
        if not (has_mss or has_disp):
            if entry_model == "MARKET":
                return None
            elif entry_model == "FVG" and has_fvg:
                # Need fresh tap for FVG entry
                tapped = False
                for f in aligned_fvgs:
                    if raw_dir == "BULLISH" and current_candle.low <= f.fvg_high:
                        tapped = True
                    elif raw_dir == "BEARISH" and current_candle.high >= f.fvg_low:
                        tapped = True
                if not tapped:
                    return None
            else:
                return None

        # 7. Score Calculation
        score_breakdown = calculate_confluence_score(
            has_sweep=has_sweep,
            has_smt=has_smt,
            has_mss=has_mss,
            has_displacement=has_disp,
            has_fvg=has_fvg,
            session=session,
            threshold_b=min_score
        )

        if score_breakdown.total_score < min_score:
            return None

        # MTF Filter: Reject trades that oppose the 1H macro bias
        if macro_bias != "NEUTRAL":
            expected_macro = "BULLISH" if direction == "BUY" else "BEARISH"
            if macro_bias != expected_macro:
                return None

        # Entry, Stop Loss, Take Profit
        entry = current_candle.close
        if entry_model == "FVG" and fvgs:
            matching_fvg = [f for f in fvgs if f.fvg_type == (
                "BULLISH" if direction == "BUY" else "BEARISH"
            )]
            if matching_fvg:
                entry = matching_fvg[-1].fvg_low if direction == "BUY" else matching_fvg[-1].fvg_high

        # Determine Max Risk based on preset
        max_risk = 25.0  # SWING
        if strategy_preset == "SCALP":
            max_risk = 3.0
        elif strategy_preset == "INTRADAY":
            max_risk = 8.0

        if direction == "BUY":
            sl_base = current_candle.low
            if latest_sweep:
                sl_base = latest_sweep.sweep_price
            else:
                recent_swing_lows = [s for s in swings if s.level_type == "SWING_LOW" and s.is_confirmed]
                if recent_swing_lows:
                    sl_base = recent_swing_lows[-1].price
                    
            sl = round(sl_base - sl_buffer_pips, 2)
            risk = round(entry - sl, 2)

            if risk <= 0:
                risk = 2.0
                sl = round(entry - risk, 2)

            if risk > max_risk:
                risk = max_risk
                sl = round(entry - risk, 2)

            tp1 = round(entry + 1.0 * risk, 2)
            tp2 = round(entry + 2.0 * risk, 2)
            tp3 = round(entry + 3.0 * risk, 2)

        else:  # SELL
            sl_base = current_candle.high
            if latest_sweep:
                sl_base = latest_sweep.sweep_price
            else:
                recent_swing_highs = [s for s in swings if s.level_type == "SWING_HIGH" and s.is_confirmed]
                if recent_swing_highs:
                    sl_base = recent_swing_highs[-1].price
                    
            sl = round(sl_base + sl_buffer_pips, 2)
            risk = round(sl - entry, 2)

            if risk <= 0:
                risk = 2.0
                sl = round(entry + risk, 2)

            if risk > max_risk:
                risk = max_risk
                sl = round(entry + risk, 2)

            tp1 = round(entry - 1.0 * risk, 2)
            tp2 = round(entry - 2.0 * risk, 2)
            tp3 = round(entry - 3.0 * risk, 2)

        # Deterministic signal key
        ts_str = current_candle.timestamp.strftime("%Y-%m-%dT%H:%M:%S")
        is_demo_str = "true" if current_candle.is_demo else "false"
        signal_key = f"{current_candle.symbol}:{current_candle.timeframe}:{ts_str}:{strategy_preset}:{strategy_version}:{is_demo_str}"

        explanation = (
            f"{current_candle.symbol} {direction} setup on {current_candle.timeframe} during {session} session. "
            f"Confluence Score: {score_breakdown.total_score}/100 ({score_breakdown.grade}). "
            f"Liquidity Sweep: {'PASS' if has_sweep else 'FAIL'}, SMT: {'PASS' if has_smt else 'FAIL'}, "
            f"MSS: {'PASS' if has_mss else 'FAIL'}, Displacement: {'PASS' if has_disp else 'FAIL'}, FVG: {'PASS' if has_fvg else 'FAIL'}."
        )

        return StrategySignalOutput(
            signal_key=signal_key,
            symbol=current_candle.symbol,
            timeframe=current_candle.timeframe,
            timestamp=current_candle.timestamp,
            direction=direction,
            strategy_preset=strategy_preset,
            strategy_version=strategy_version,
            score=score_breakdown.total_score,
            score_grade=score_breakdown.grade,
            entry_price=round(entry, 2),
            stop_loss=sl,
            tp1=tp1,
            tp2=tp2,
            tp3=tp3,
            risk_distance=risk,
            reward_tp1=round(abs(tp1 - entry), 2),
            reward_tp2=round(abs(tp2 - entry), 2),
            reward_tp3=round(abs(tp3 - entry), 2),
            session=session,
            liquidity_type=latest_sweep.liquidity_type if latest_sweep else None,
            liquidity_level=latest_sweep.liquidity_level_price if latest_sweep else None,
            smt_status=has_smt,
            mss_status=has_mss,
            displacement_status=has_disp,
            fvg_status=has_fvg,
            news_status="NORMAL",
            data_quality_status="VALID",
            status="OPEN",
            explanation=explanation,
            is_demo=current_candle.is_demo
        )

def run_strategy_pipeline(*args, **kwargs) -> Optional[StrategySignalOutput]:
    strategy = ConfluenceStrategy()
    return strategy.evaluate(*args, **kwargs)
