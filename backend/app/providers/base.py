from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict

class Candle(BaseModel):
    symbol: str
    timeframe: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
    is_demo: bool = False

    model_config = ConfigDict(frozen=True)

class MarketDataProvider(ABC):
    @abstractmethod
    def fetch_candles(
        self,
        symbol: str,
        timeframe: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[Candle]:
        """Fetch historical candles in normalized format."""
        pass

    @abstractmethod
    def get_latest_candle(self, symbol: str, timeframe: str) -> Optional[Candle]:
        """Get the latest confirmed closed candle."""
        pass
