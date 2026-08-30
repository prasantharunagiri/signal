import time
from datetime import datetime
from typing import List, Optional, Dict
from app.providers.base import MarketDataProvider, Candle

class EAPushProvider(MarketDataProvider):
    """
    Receives real-time ticks and candles directly pushed from the MT5 EA via HTTP POST.
    No bridge server or Windows port opening required!
    """
    _latest_candles: Dict[str, Dict[str, List[Candle]]] = {}
    _latest_ticks: Dict[str, Dict] = {}
    _last_push_time: float = 0.0

    def push_data(self, payload: dict):
        symbol = payload.get("symbol", "XAUUSD").upper()
        # Normalize broker suffixes (Exness uses XAUUSDM, XAUUSDc etc)
        if symbol.startswith("XAUUSD"):
            symbol = "XAUUSD"
            
        if symbol not in EAPushProvider._latest_candles:
            EAPushProvider._latest_candles[symbol] = {}
            
        bid = float(payload.get("bid", 0.0))
        ask = float(payload.get("ask", 0.0))
        
        if bid > 0:
            EAPushProvider._latest_ticks[symbol] = {
                "symbol": symbol,
                "bid": bid,
                "ask": ask if ask > 0 else round(bid + 0.18, 2),
                "last": bid,
                "spread": round(ask - bid, 2) if ask > bid else 0.18,
                "timestamp": datetime.utcnow()
            }

        def parse_candles(raw_candles, tf):
            if not raw_candles:
                return []
            candles = []
            for c in raw_candles:
                try:
                    ts_val = c.get("timestamp")
                    if isinstance(ts_val, str):
                        ts = datetime.fromisoformat(ts_val.replace("Z", ""))
                    elif isinstance(ts_val, (int, float)):
                        ts = datetime.utcfromtimestamp(ts_val)
                    else:
                        ts = datetime.utcnow()

                    candles.append(
                        Candle(
                            symbol=symbol,
                            timeframe=tf,
                            timestamp=ts,
                            open=float(c.get("open", 0.0)),
                            high=float(c.get("high", 0.0)),
                            low=float(c.get("low", 0.0)),
                            close=float(c.get("close", 0.0)),
                            volume=float(c.get("volume", 0.0)),
                            is_demo=False
                        )
                    )
                except Exception:
                    pass
            # Sort chronologically just in case
            candles.sort(key=lambda x: x.timestamp)
            return candles

        # Check for MTF payload
        if "candles_5m" in payload and "candles_1h" in payload:
            EAPushProvider._latest_candles[symbol]["5m"] = parse_candles(payload["candles_5m"], "5m")
            EAPushProvider._latest_candles[symbol]["1h"] = parse_candles(payload["candles_1h"], "1h")
        elif "candles" in payload:
            # Legacy payload format (single timeframe)
            tf = payload.get("timeframe", "5m").lower()
            EAPushProvider._latest_candles[symbol][tf] = parse_candles(payload["candles"], tf)

        EAPushProvider._last_push_time = time.time()

    def fetch_candles(
        self,
        symbol: str,
        timeframe: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 500
    ) -> List[Candle]:
        sym = symbol.upper()
        tf = timeframe.lower()
        live_candles = []
        if sym in EAPushProvider._latest_candles and tf in EAPushProvider._latest_candles[sym]:
            live_candles = EAPushProvider._latest_candles[sym][tf]
        
        # Merge with CSV history if we don't have enough live candles
        if len(live_candles) < limit:
            try:
                from app.providers.csv_provider import CSVProvider
                csv_provider = CSVProvider()
                hist_candles = csv_provider.fetch_candles(symbol, timeframe, limit=limit)
                
                # Merge historical and live, overriding history with live data for matching timestamps
                merged = {c.timestamp: c for c in hist_candles}
                for lc in live_candles:
                    merged[lc.timestamp] = lc
                    
                all_candles = sorted(merged.values(), key=lambda x: x.timestamp)
                if limit and len(all_candles) > limit:
                    return all_candles[-limit:]
                return all_candles
            except Exception as e:
                print(f"[EAPushProvider] Fallback to CSV error: {e}")

        if limit and len(live_candles) > limit:
            return live_candles[-limit:]
        return live_candles

    def get_latest_candle(self, symbol: str, timeframe: str) -> Optional[Candle]:
        candles = self.fetch_candles(symbol, timeframe, limit=1)
        return candles[-1] if candles else None

    def get_live_tick(self, symbol: str = "XAUUSD") -> Optional[dict]:
        return EAPushProvider._latest_ticks.get(symbol.upper())

    def is_active(self) -> bool:
        return (time.time() - EAPushProvider._last_push_time) < 20

    def get_last_push_time(self) -> float:
        return EAPushProvider._last_push_time
