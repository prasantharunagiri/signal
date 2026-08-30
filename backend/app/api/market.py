from fastapi import APIRouter, Query, HTTPException
from typing import List
from datetime import datetime
from app.providers.base import Candle
from app.providers.data_source_manager import data_source_manager

router = APIRouter(prefix="/api/market", tags=["Market Data"])

def get_provider():
    return data_source_manager.get_active_provider()

@router.get("/provider/status")
def get_provider_status():
    return data_source_manager.get_status()

@router.post("/provider/mode")
def set_provider_mode(mode: str = Query(..., description="AUTO, MT5, or TWELVEDATA")):
    try:
        data_source_manager.set_mode(mode)
        return {"status": "success", "mode": data_source_manager.mode}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/push")
def receive_ea_push(payload: dict):
    bid = payload.get("bid")
    ask = payload.get("ask")
    print(f"📡 [MT5-EA-PUSH] Live tick received from Exness MT5: Bid=${bid}, Ask=${ask}")
    data_source_manager.ea_push_instance.push_data(payload)
    return {"status": "ok", "message": "Market data updated from MT5 EA", "bid": bid, "ask": ask}

@router.get("/candles", response_model=List[Candle])
def get_candles(
    symbol: str = "XAUUSD",
    timeframe: str = "5m",
    limit: int = Query(default=500, le=5000),
):
    provider = get_provider()
    return provider.fetch_candles(symbol=symbol, timeframe=timeframe, limit=limit)

@router.get("/session")
def get_current_session():
    now = datetime.utcnow()
    h = now.hour
    sess = "Asian"
    if 7 <= h < 13:
        sess = "London"
    elif 13 <= h < 16:
        sess = "London / NY Overlap"
    elif 16 <= h < 21:
        sess = "New York"

    return {
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "current_session": sess,
        "market_status": "OPEN" if 0 <= h < 22 else "CLOSED"
    }
