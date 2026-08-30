from typing import List, Dict, Any
from pydantic import BaseModel
from app.models.schema import Signal

class MetricSummary(BaseModel):
    category: str
    total_trades: int
    wins: int
    losses: int
    win_rate: float
    avg_r: float
    total_r: float
    expectancy: float
    max_drawdown: float
    max_consecutive_losses: int
    profit_factor: float

def compute_r_from_status(sig: Signal) -> float:
    if sig.status == "TP3_HIT":
        return 3.0
    elif sig.status == "TP2_HIT":
        return 2.0
    elif sig.status in ["TP1_HIT", "SL_AFTER_TP"]:
        return 1.0
    elif sig.status == "SL_HIT":
        return -1.0
    return 0.0

def compute_metrics(category_name: str, signals: List[Signal]) -> MetricSummary:
    closed_signals = [s for s in signals if s.status in ["TP1_HIT", "TP2_HIT", "TP3_HIT", "SL_HIT", "SL_AFTER_TP", "AMBIGUOUS"]]
    if not closed_signals:
        return MetricSummary(
            category=category_name, total_trades=0, wins=0, losses=0,
            win_rate=0.0, avg_r=0.0, total_r=0.0, expectancy=0.0,
            max_drawdown=0.0, max_consecutive_losses=0, profit_factor=0.0
        )

    r_vals = [compute_r_from_status(s) for s in closed_signals]
    wins = sum(1 for r in r_vals if r > 0)
    losses = sum(1 for r in r_vals if r < 0)

    total_trades = len(closed_signals)
    win_rate = (wins / total_trades) * 100.0 if total_trades > 0 else 0.0
    total_r = sum(r_vals)
    avg_r = total_r / total_trades if total_trades > 0 else 0.0

    win_sum = sum(r for r in r_vals if r > 0)
    loss_sum = abs(sum(r for r in r_vals if r < 0))
    profit_factor = round(win_sum / loss_sum, 2) if loss_sum > 0 else (win_sum if win_sum > 0 else 0.0)

    # Max Drawdown & Consecutive Losses
    cum_r = 0.0
    peak = 0.0
    max_dd = 0.0
    curr_streak = 0
    max_streak = 0

    for r in r_vals:
        cum_r += r
        if cum_r > peak:
            peak = cum_r
        dd = peak - cum_r
        if dd > max_dd:
            max_dd = dd

        if r < 0:
            curr_streak += 1
            if curr_streak > max_streak:
                max_streak = curr_streak
        else:
            curr_streak = 0

    return MetricSummary(
        category=category_name,
        total_trades=total_trades,
        wins=wins,
        losses=losses,
        win_rate=round(win_rate, 2),
        avg_r=round(avg_r, 2),
        total_r=round(total_r, 2),
        expectancy=round(avg_r, 2),
        max_drawdown=round(max_dd, 2),
        max_consecutive_losses=max_streak,
        profit_factor=profit_factor
    )

def analyze_performance_by_preset(signals: List[Signal]) -> Dict[str, MetricSummary]:
    presets = ["SCALP", "INTRADAY", "SWING"]
    result = {}
    for p in presets:
        p_sigs = [s for s in signals if s.strategy_preset == p]
        result[p] = compute_metrics(f"Preset: {p}", p_sigs)
    return result

def analyze_performance_by_score(signals: List[Signal]) -> Dict[str, MetricSummary]:
    ranges = {
        "70-79": [s for s in signals if 70 <= s.score < 80],
        "80-89": [s for s in signals if 80 <= s.score < 90],
        "90-100": [s for s in signals if 90 <= s.score <= 100]
    }
    return {k: compute_metrics(f"Score {k}", sigs) for k, sigs in ranges.items()}

def analyze_performance_by_session(signals: List[Signal]) -> Dict[str, MetricSummary]:
    sessions = ["Asian", "London", "New York", "London / NY Overlap"]
    result = {}
    for sess in sessions:
        s_sigs = [s for s in signals if s.session == sess]
        result[sess] = compute_metrics(f"Session: {sess}", s_sigs)
    return result

def analyze_performance_by_direction(signals: List[Signal]) -> Dict[str, MetricSummary]:
    buy_sigs = [s for s in signals if s.direction == "BUY"]
    sell_sigs = [s for s in signals if s.direction == "SELL"]
    return {
        "BUY": compute_metrics("Direction: BUY", buy_sigs),
        "SELL": compute_metrics("Direction: SELL", sell_sigs)
    }
