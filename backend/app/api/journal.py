import csv
import io
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session
from typing import Optional, List
from app.database import get_db
from app.models.schema import Signal

router = APIRouter(prefix="/api/journal", tags=["Signal Journal"])

@router.get("")
def get_journal_entries(
    symbol: Optional[str] = None,
    direction: Optional[str] = None,
    strategy_preset: Optional[str] = None,
    status: Optional[str] = None,
    min_score: Optional[int] = None,
    is_demo: bool = False,
    db: Session = Depends(get_db)
):
    query = db.query(Signal).filter(Signal.is_demo == is_demo)
    if symbol:
        query = query.filter(Signal.symbol == symbol)
    if direction:
        query = query.filter(Signal.direction == direction)
    if strategy_preset:
        query = query.filter(Signal.strategy_preset == strategy_preset)
    if status:
        query = query.filter(Signal.status == status)
    if min_score:
        query = query.filter(Signal.score >= min_score)

    return query.order_by(Signal.timestamp.desc()).all()

@router.get("/export/csv")
def export_journal_csv(is_demo: bool = False, db: Session = Depends(get_db)):
    signals = db.query(Signal).filter(Signal.is_demo == is_demo).order_by(Signal.timestamp.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Signal ID", "Key", "Symbol", "Timeframe", "Timestamp UTC", "Direction", "Preset",
        "Version", "Score", "Grade", "Entry", "SL", "TP1", "TP2", "TP3", "Risk",
        "Session", "Status", "Is Demo", "Explanation"
    ])

    for s in signals:
        writer.writerow([
            s.id, s.signal_key, s.symbol, s.timeframe, s.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            s.direction, s.strategy_preset, s.strategy_version, s.score, s.score_grade,
            s.entry_price, s.stop_loss, s.tp1, s.tp2, s.tp3, s.risk_distance,
            s.session, s.status, s.is_demo, s.explanation
        ])

    response = Response(content=output.getvalue(), media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=xauusd_signal_journal.csv"
    return response
