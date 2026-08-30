import urllib.request
import json
import time
from datetime import datetime
from typing import List, Optional, Dict
from app.providers.base import MarketDataProvider, Candle
from app.config import settings
from app.database import SessionLocal, init_db
from app.models.schema import MarketData

TIMEFRAME_MAP = {
    "1m":  "1min",
    "5m":  "5min",
    "15m": "15min",
    "30m": "30min",
    "1h":  "1h",
    "4h":  "4h",
    "1d":  "1day",
}

class TwelveDataProvider(MarketDataProvider):
    """
    Live market data provider using the Twelve Data REST API with local SQLite fallback & caching.
    Prevents API rate limit (429) failures by caching results and serving DB candles when credits expire.
    """
    BASE_URL = "https://api.twelvedata.com/time_series"
    _cache: Dict[str, Dict] = {}  # In-memory response cache
    _quota_exceeded_until: float = 0.0

    def __init__(self):
        self.api_key = settings.TWELVEDATA_API_KEY
        if not self.api_key:
            print("[TwelveDataProvider] WARNING: TWELVEDATA_API_KEY is not set in .env. Live REST API fallback will not work.")

    def is_quota_exceeded(self) -> bool:
        return time.time() < self._quota_exceeded_until

    def _symbol_for_api(self, symbol: str) -> str:
        s = symbol.upper()
        if s == "XAUUSD":
            return "XAU/USD"
        if "/" not in s and len(s) == 6:
            return f"{s[:3]}/{s[3:]}"
        return s

    def _save_to_db(self, candles: List[Candle]):
        if not candles:
            return
        init_db()
        db = SessionLocal()
        try:
            for c in candles:
                existing = db.query(MarketData).filter(
                    MarketData.symbol == c.symbol,
                    MarketData.timeframe == c.timeframe,
                    MarketData.timestamp == c.timestamp,
                    MarketData.is_demo == False
                ).first()
                if not existing:
                    db.add(MarketData(
                        symbol=c.symbol,
                        timeframe=c.timeframe,
                        timestamp=c.timestamp,
                        open=c.open,
                        high=c.high,
                        low=c.low,
                        close=c.close,
                        volume=c.volume,
                        is_demo=False
                    ))
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

    def _get_from_db(self, symbol: str, timeframe: str, limit: int) -> List[Candle]:
        init_db()
        db = SessionLocal()
        try:
            records = db.query(MarketData).filter(
                MarketData.symbol == symbol.upper(),
                MarketData.timeframe == timeframe.lower(),
                MarketData.is_demo == False
            ).order_by(MarketData.timestamp.desc()).limit(limit).all()

            records.reverse()

            return [
                Candle(
                    symbol=r.symbol,
                    timeframe=r.timeframe,
                    timestamp=r.timestamp,
                    open=r.open,
                    high=r.high,
                    low=r.low,
                    close=r.close,
                    volume=r.volume,
                    is_demo=False
                ) for r in records
            ]
        finally:
            db.close()

    def fetch_candles(
        self,
        symbol: str,
        timeframe: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 500,
    ) -> List[Candle]:
        cache_key = f"{symbol}:{timeframe}:{limit}"
        now_ts = time.time()

        # Serve from 35-second in-memory cache if fresh to prevent 8-credit/min limit hit
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if now_ts - cached["ts"] < 35:
                return cached["candles"]

        tf = TIMEFRAME_MAP.get(timeframe.lower(), "5min")
        api_symbol = self._symbol_for_api(symbol)
        output_size = min(limit, 5000)

        url = (
            f"{self.BASE_URL}"
            f"?symbol={api_symbol}"
            f"&interval={tf}"
            f"&outputsize={output_size}"
            f"&apikey={self.api_key}"
            f"&format=JSON"
            f"&timezone=UTC"
        )

        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                data = json.loads(resp.read().decode())

            if data.get("status") == "ok":
                values = data.get("values", [])
                candles: List[Candle] = []
                for v in reversed(values):
                    try:
                        candles.append(Candle(
                            symbol=symbol.upper(),
                            timeframe=timeframe.lower(),
                            timestamp=datetime.strptime(v["datetime"], "%Y-%m-%d %H:%M:%S"),
                            open=float(v["open"]),
                            high=float(v["high"]),
                            low=float(v["low"]),
                            close=float(v["close"]),
                            volume=float(v.get("volume", 0.0)),
                            is_demo=False,
                        ))
                    except Exception:
                        pass

                if candles:
                    self._save_to_db(candles)
                    self._cache[cache_key] = {"ts": now_ts, "candles": candles}
                    return candles
            elif data.get("code") == 429:
                print(f"[TwelveDataProvider] Rate limit exceeded (429). Cooling down.")
                self._quota_exceeded_until = time.time() + 60

        except Exception as e:
            print(f"[TwelveDataProvider] HTTP fetch notice: {e}")

        # Fallback to local DB cache if API rate limit (429) hit or offline
        db_candles = self._get_from_db(symbol, timeframe, limit)
        if db_candles:
            self._cache[cache_key] = {"ts": now_ts, "candles": db_candles}
            return db_candles

        return []

    def get_latest_candle(self, symbol: str, timeframe: str) -> Optional[Candle]:
        candles = self.fetch_candles(symbol, timeframe, limit=1)
        return candles[-1] if candles else None
