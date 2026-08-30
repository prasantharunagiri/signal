from datetime import datetime
from typing import List, Optional
from app.providers.base import MarketDataProvider, Candle
from app.config import settings

class MT5Provider(MarketDataProvider):
    """
    Server-side MetaTrader 5 MarketDataProvider adapter.
    Translates MT5 ticks/candles into normalized Candle data structures.
    MT5 credentials remain securely on the backend server.
    """
    def __init__(self):
        self.login = settings.MT5_LOGIN
        self.password = settings.MT5_PASSWORD
        self.server = settings.MT5_SERVER
        self.connected = False

    def initialize(self) -> bool:
        """Initializes server-side MT5 terminal connection if MetaTrader5 module is installed."""
        try:
            import MetaTrader5 as mt5
            if not mt5.initialize(login=self.login, password=self.password, server=self.server):
                print(f"MT5 initialize failed: {mt5.last_error()}")
                self.connected = False
                return False
            self.connected = True
            return True
        except ImportError:
            # Fallback if MetaTrader5 library is not present on host OS
            print("MetaTrader5 python module not installed. Operating in mock MT5 mode.")
            self.connected = False
            return False

    def fetch_candles(
        self,
        symbol: str,
        timeframe: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 500
    ) -> List[Candle]:
        try:
            import MetaTrader5 as mt5
            if not self.connected and not self.initialize():
                return []

            tf_map = {
                "1m": mt5.TIMEFRAME_M1,
                "5m": mt5.TIMEFRAME_M5,
                "15m": mt5.TIMEFRAME_M15,
                "1h": mt5.TIMEFRAME_H1,
                "4h": mt5.TIMEFRAME_H4,
                "1d": mt5.TIMEFRAME_D1
            }
            mt5_tf = tf_map.get(timeframe.lower(), mt5.TIMEFRAME_M5)

            rates = mt5.copy_rates_from_pos(symbol, mt5_tf, 0, limit)
            if rates is None or len(rates) == 0:
                return []

            candles = []
            for r in rates:
                candles.append(
                    Candle(
                        symbol=symbol.upper(),
                        timeframe=timeframe.lower(),
                        timestamp=datetime.utcfromtimestamp(r['time']),
                        open=float(r['open']),
                        high=float(r['high']),
                        low=float(r['low']),
                        close=float(r['close']),
                        volume=float(r['tick_volume']),
                        is_demo=False
                    )
                )
            return candles
        except Exception as e:
            print(f"MT5 fetch_candles error: {e}")
            return []

    def get_latest_candle(self, symbol: str, timeframe: str) -> Optional[Candle]:
        candles = self.fetch_candles(symbol, timeframe, limit=1)
        return candles[-1] if candles else None
