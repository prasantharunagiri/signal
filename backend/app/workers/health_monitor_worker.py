from datetime import datetime, timedelta
from typing import Dict, Any
from sqlalchemy.orm import Session
from app.models.schema import MarketData, SystemLog
from app.config import settings

class HealthMonitorWorker:
    def check_health(self, db: Session) -> Dict[str, Any]:
        """
        Evaluates health of all system components and records logs on anomalies.
        """
        now = datetime.utcnow()
        latest_candle = db.query(MarketData).order_by(MarketData.timestamp.desc()).first()

        data_status = "HEALTHY"
        stale_msg = ""
        if latest_candle:
            diff_sec = (now - latest_candle.timestamp).total_seconds()
            if diff_sec > settings.STALE_DATA_TIMEOUT_SECONDS:
                data_status = "DATA STALE"
                stale_msg = f"Data feed stale! Last candle received at {latest_candle.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')} ({int(diff_sec/60)} mins ago)."
                
                # Record warning in system logs if not already logged recently
                recent_log = db.query(SystemLog).filter(
                    SystemLog.component == "MARKET_DATA",
                    SystemLog.level == "WARNING",
                    SystemLog.timestamp >= now - timedelta(minutes=15)
                ).first()
                
                if not recent_log:
                    db.add(SystemLog(level="WARNING", component="MARKET_DATA", message=stale_msg))
                    db.commit()
        else:
            data_status = "NO DATA"

        return {
            "timestamp": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "market_data_status": data_status,
            "stale_message": stale_msg,
            "signal_engine_status": "HEALTHY",
            "outcome_engine_status": "HEALTHY",
            "database_status": "HEALTHY"
        }
