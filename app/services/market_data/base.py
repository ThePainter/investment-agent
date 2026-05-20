from abc import ABC, abstractmethod

import pandas as pd


TIMEFRAME_MAP = {
    "5m": {"interval": "5m", "period": "5d"},
    "15m": {"interval": "15m", "period": "30d"},
    "1h": {"interval": "60m", "period": "90d"},
    "1d": {"interval": "1d", "period": "2y"},
}


class MarketDataProvider(ABC):
    @abstractmethod
    def fetch_ohlcv(self, ticker: str, timeframe: str) -> pd.DataFrame:
        raise NotImplementedError

