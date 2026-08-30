from pydantic import BaseModel
from typing import Dict, Any

class ScoreBreakdown(BaseModel):
    liquidity_sweep: int = 0
    smt_divergence: int = 0
    mss: int = 0
    displacement: int = 0
    fvg: int = 0
    session_quality: int = 0
    total_score: int = 0
    grade: str = "NO_SIGNAL"

def calculate_confluence_score(
    has_sweep: bool,
    has_smt: bool,
    has_mss: bool,
    has_displacement: bool,
    has_fvg: bool,
    session: str,
    weights: Dict[str, int] = None,
    threshold_a_plus: int = 90,
    threshold_a: int = 80,
    threshold_b: int = 70
) -> ScoreBreakdown:
    if weights is None:
        weights = {
            "liquidity_sweep": 20,
            "smt_divergence": 20,
            "mss": 20,
            "displacement": 15,
            "fvg": 15,
            "session_quality": 10
        }

    sweep_pts = weights["liquidity_sweep"] if has_sweep else 0
    smt_pts = weights["smt_divergence"] if has_smt else 0
    mss_pts = weights["mss"] if has_mss else 0
    disp_pts = weights["displacement"] if has_displacement else 0
    fvg_pts = weights["fvg"] if has_fvg else 0

    session_pts = 0
    if session in ["London", "New York", "London / NY Overlap"]:
        session_pts = weights["session_quality"]
    elif session == "Asian":
        session_pts = weights["session_quality"] // 2

    total = sweep_pts + smt_pts + mss_pts + disp_pts + fvg_pts + session_pts

    grade = "NO_SIGNAL"
    if total >= threshold_a_plus:
        grade = "A+"
    elif total >= threshold_a:
        grade = "A"
    elif total >= threshold_b:
        grade = "B"

    return ScoreBreakdown(
        liquidity_sweep=sweep_pts,
        smt_divergence=smt_pts,
        mss=mss_pts,
        displacement=disp_pts,
        fvg=fvg_pts,
        session_quality=session_pts,
        total_score=total,
        grade=grade
    )
