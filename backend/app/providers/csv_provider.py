import os
import pandas as pd
from datetime import datetime
from typing import List, Optional
from app.providers.base import MarketDataProvider, Candle

class CSVProvider(MarketDataProvider):
    def __init__(self, data_dir: str = "data/csv"):
        self.data_dir = data_dir

    def _get_file_path(self, symbol: str, timeframe: str) -> str:
        filename = f"{symbol.upper()}_{timeframe.lower()}.csv"
        primary_path = os.path.join(self.data_dir, filename)
        if os.path.exists(primary_path):
            return primary_path
        genuine_path = os.path.join("data/csv_genuine", filename)
        if os.path.exists(genuine_path):
            return genuine_path
        return primary_path

    def load_dataframe(self, symbol: str, timeframe: str) -> pd.DataFrame:
        file_path = self._get_file_path(symbol, timeframe)
        if not os.path.exists(file_path):
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])
        
        df = pd.read_csv(file_path)
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        df = df.sort_values("timestamp").reset_index(drop=True)
        return df

    def fetch_candles(
        self,
        symbol: str,
        timeframe: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[Candle]:
        df = self.load_dataframe(symbol, timeframe)
        if df.empty:
            return []

        if start_time:
            start_ts = pd.to_datetime(start_time, utc=True)
            df = df[df["timestamp"] >= start_ts]

        if end_time:
            end_ts = pd.to_datetime(end_time, utc=True)
            df = df[df["timestamp"] <= end_ts]

        if limit and len(df) > limit:
            df = df.tail(limit)

        candles = []
        for _, row in df.iterrows():
            candles.append(
                Candle(
                    symbol=symbol.upper(),
                    timeframe=timeframe.lower(),
                    timestamp=row["timestamp"].to_pydatetime(),
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row.get("volume", 0.0)),
                    is_demo=False
                )
            )
        return candles

    def get_latest_candle(self, symbol: str, timeframe: str) -> Optional[Candle]:
        candles = self.fetch_candles(symbol, timeframe, limit=1)
        return candles[0] if candles else None
