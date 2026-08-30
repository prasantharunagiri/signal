from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from app.database import get_db
from app.models.schema import Signal, SignalEvent

router = APIRouter(prefix="/api/signals", tags=["Signals"])

@router.get("/active")
def get_active_signals(
    symbol: str = "XAUUSD",
    strategy_preset: Optional[str] = None,
    is_demo: bool = False,
    db: Session = Depends(get_db)
):
    query = db.query(Signal).filter(
        Signal.symbol == symbol,
        Signal.status == "OPEN",
        Signal.is_demo == is_demo
    )
    if strategy_preset:
        query = query.filter(Signal.strategy_preset == strategy_preset)
    return query.order_by(Signal.timestamp.desc()).all()

@router.get("/recent")
def get_recent_signals(
    limit: int = Query(default=20, le=100),
    is_demo: bool = False,
    db: Session = Depends(get_db)
):
    return db.query(Signal).filter(
        Signal.is_demo == is_demo
    ).order_by(Signal.timestamp.desc()).limit(limit).all()

@router.get("/{signal_id}")
def get_signal_detail(signal_id: int, db: Session = Depends(get_db)):
    sig = db.query(Signal).filter(Signal.id == signal_id).first()
    if not sig:
        raise HTTPException(status_code=404, detail="Signal not found")
    events = db.query(SignalEvent).filter(SignalEvent.signal_id == signal_id).order_by(SignalEvent.timestamp.asc()).all()
    return {
        "signal": sig,
        "events": events
    }

@router.post("/{signal_id}/expire")
def manually_expire_signal(signal_id: int, db: Session = Depends(get_db)):
    sig = db.query(Signal).filter(Signal.id == signal_id).first()
    if not sig:
        raise HTTPException(status_code=404, detail="Signal not found")
    
    if sig.status not in ["OPEN", "TP1_HIT", "TP2_HIT"]:
        raise HTTPException(status_code=400, detail=f"Cannot expire signal with status {sig.status}")
        
    sig.status = "EXPIRED"
    
    event = SignalEvent(
        signal_id=sig.id,
        event_type="EXPIRED",
        price=sig.entry_price, # Using entry price as fallback
        timestamp=datetime.utcnow(),
        details="Signal was manually expired by user."
    )
    db.add(event)
    db.commit()
    
    return {"status": "success", "message": "Signal manually expired", "signal_id": signal_id}
