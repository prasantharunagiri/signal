import os
import pandas as pd
import httpx
from datetime import datetime, timedelta

GENUINE_DATA_DIR = "data/csv_genuine"

def download_yahoo_historical(symbol="GC=F", target_symbol="XAUUSD", timeframe="5m"):
    """
    Downloads genuine historical candles for Gold (GC=F) or Dollar Index (DX-Y.NY).
    """
    os.makedirs(GENUINE_DATA_DIR, exist_ok=True)
    tf_map = {"1m": "1m", "5m": "5m", "15m": "15m", "1h": "60m", "1d": "1d"}
    interval = tf_map.get(timeframe.lower(), "5m")

    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=7d&interval={interval}"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        res = httpx.get(url, headers=headers, timeout=10.0)
        if res.status_code == 200:
            data = res.json()["chart"]["result"][0]
            timestamps = data["timestamp"]
            quote = data["indicators"]["quote"][0]
            
            df = pd.DataFrame({
                "timestamp": [datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S") for ts in timestamps],
                "open": quote["open"],
                "high": quote["high"],
                "low": quote["low"],
                "close": quote["close"],
                "volume": quote["volume"]
            }).dropna()

            filepath = os.path.join(GENUINE_DATA_DIR, f"{target_symbol.upper()}_{timeframe.lower()}.csv")
            df.to_csv(filepath, index=False)
            print(f"Successfully downloaded {len(df)} GENUINE candles for {target_symbol} {timeframe} -> {filepath}")
            return filepath
        else:
            print(f"Yahoo API returned HTTP {res.status_code}")
            return None
    except Exception as e:
        print(f"Failed to download genuine market data: {e}")
        return None

if __name__ == "__main__":
    download_yahoo_historical("GC=F", "XAUUSD", "5m")
    download_yahoo_historical("DX-Y.NY", "DXY", "5m")
