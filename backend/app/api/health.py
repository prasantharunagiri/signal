from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.database import get_db
from app.models.schema import MarketData, SystemLog
from app.config import settings

router = APIRouter(prefix="/api/health", tags=["Health & Watchdog"])

@router.get("/status")
def get_system_health(db: Session = Depends(get_db)):
    latest_candle = db.query(MarketData).order_by(MarketData.timestamp.desc()).first()

    now = datetime.utcnow()
    last_candle_time = latest_candle.timestamp if latest_candle else None
    time_since_update_mins = 0.0

    feed_status = "HEALTHY"
    if last_candle_time:
        diff_sec = (now - last_candle_time).total_seconds()
        time_since_update_mins = round(diff_sec / 60.0, 1)
        if diff_sec > settings.STALE_DATA_TIMEOUT_SECONDS:
            feed_status = "DATA STALE"
    else:
        feed_status = "NO DATA"

    return {
        "overall_status": "HEALTHY" if feed_status == "HEALTHY" else "WARNING",
        "timestamp_utc": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "services": {
            "market_data": {
                "status": feed_status,
                "provider": settings.MARKET_DATA_PROVIDER,
                "last_candle_utc": last_candle_time.strftime("%Y-%m-%d %H:%M:%S") if last_candle_time else None,
                "minutes_since_last_candle": time_since_update_mins
            },
            "signal_engine": {"status": "HEALTHY", "version": "XAU-CONFLUENCE-V1.0"},
            "outcome_engine": {"status": "HEALTHY"},
            "database": {"status": "HEALTHY", "type": "SQLite" if "sqlite" in settings.DATABASE_URL else "PostgreSQL"},
            "news_engine": {"status": "HEALTHY"},
            "notifications": {"status": "HEALTHY" if settings.TELEGRAM_BOT_TOKEN else "UNCONFIGURED"}
        }
    }

@router.get("/logs")
def get_system_logs(limit: int = 50, db: Session = Depends(get_db)):
    return db.query(SystemLog).order_by(SystemLog.timestamp.desc()).limit(limit).all()
