"""
MT5 Bridge Provider (mac-side)
================================
On macOS the MetaTrader5 Python package does NOT exist.
This provider instead HTTP-polls the mt5_bridge_server.py
that runs on a Windows VPS / Windows VM.

Set in .env:
    MARKET_DATA_PROVIDER=mt5_bridge
    MT5_BRIDGE_URL=http://<YOUR_VPS_IP>:9000
"""
import httpx
from datetime import datetime
from typing import List, Optional
from app.providers.base import MarketDataProvider, Candle
from app.providers.twelvedata_provider import TwelveDataProvider
from app.config import settings


class MT5BridgeProvider(MarketDataProvider):
    """
    Fetches candles and ticks from the Windows-side mt5_bridge_server.py via HTTP.
    Falls back instantly to TwelveDataProvider & SQLite cache when MT5 bridge is offline.
    """

    def __init__(self):
        self.bridge_url = getattr(settings, "MT5_BRIDGE_URL", "http://localhost:9000")
        self._fallback = TwelveDataProvider()

    def is_connected(self) -> bool:
        try:
            with httpx.Client(timeout=0.3) as client:
                r = client.get(f"{self.bridge_url}/health")
                return r.status_code == 200 and r.json().get("connected", False)
        except Exception:
            return False

    def get_live_tick(self, symbol: str = "XAUUSD") -> Optional[dict]:
        if self.is_connected():
            try:
                with httpx.Client(timeout=1.0) as client:
                    r = client.get(f"{self.bridge_url}/tick", params={"symbol": symbol})
                    r.raise_for_status()
                    return r.json()
            except Exception:
                pass

        latest = self._fallback.get_latest_candle(symbol, "5m")
        if latest:
            return {
                "symbol": symbol,
                "bid": latest.close,
                "ask": round(latest.close + 0.18, 2),
                "last": latest.close,
                "spread": 0.18,
                "time": latest.timestamp.isoformat()
            }
        return None

    def fetch_candles(
        self,
        symbol: str,
        timeframe: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 500,
    ) -> List[Candle]:
        if self.is_connected():
            try:
                params = {"symbol": symbol, "timeframe": timeframe, "limit": limit}
                with httpx.Client(timeout=1.5) as client:
                    r = client.get(f"{self.bridge_url}/candles", params=params)
                    r.raise_for_status()
                    raw = r.json().get("candles", [])
                    if raw:
                        candles = []
                        for c in raw:
                            ts = datetime.fromisoformat(c["timestamp"])
                            if ts.tzinfo is not None:
                                ts = ts.replace(tzinfo=None)
                            candles.append(
                                Candle(
                                    symbol=symbol.upper(),
                                    timeframe=timeframe.lower(),
                                    timestamp=ts,
                                    open=float(c["open"]),
                                    high=float(c["high"]),
                                    low=float(c["low"]),
                                    close=float(c["close"]),
                                    volume=float(c.get("volume", 0.0)),
                                    is_demo=False,
                                )
                            )
                        return candles
            except Exception:
                pass

        # Fallback to TwelveData / SQLite Cache if MT5 bridge is offline
        return self._fallback.fetch_candles(symbol, timeframe, start_time, end_time, limit)

    def get_latest_candle(self, symbol: str, timeframe: str) -> Optional[Candle]:
        candles = self.fetch_candles(symbol, timeframe, limit=2)
        if len(candles) >= 2:
            return candles[-2]
        return candles[-1] if candles else None
