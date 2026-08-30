from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.schema import Signal
from app.analytics.performance import (
    analyze_performance_by_preset,
    analyze_performance_by_score,
    analyze_performance_by_session,
    analyze_performance_by_direction
)

router = APIRouter(prefix="/api/performance", tags=["Performance"])

@router.get("/summary")
def get_performance_summary(
    is_demo: bool = False,
    db: Session = Depends(get_db)
):
    signals = db.query(Signal).filter(Signal.is_demo == is_demo).all()

    return {
        "by_preset": analyze_performance_by_preset(signals),
        "by_score": analyze_performance_by_score(signals),
        "by_session": analyze_performance_by_session(signals),
        "by_direction": analyze_performance_by_direction(signals)
    }
