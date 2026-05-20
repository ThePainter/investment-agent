import logging
import time

import pandas as pd
import yfinance as yf

from app.services.market_data.base import TIMEFRAME_MAP, MarketDataProvider

logger = logging.getLogger(__name__)


class YahooFinanceProvider(MarketDataProvider):
    def __init__(self, retries: int = 3, retry_delay_seconds: float = 1.5, min_call_gap: float = 0.25):
        self.retries = retries
        self.retry_delay_seconds = retry_delay_seconds
        self.min_call_gap = min_call_gap
        self._last_call = 0.0

    def fetch_ohlcv(self, ticker: str, timeframe: str) -> pd.DataFrame:
        if timeframe not in TIMEFRAME_MAP:
            raise ValueError(f"Unsupported timeframe: {timeframe}")

        params = TIMEFRAME_MAP[timeframe]
        for attempt in range(1, self.retries + 1):
            try:
                elapsed = time.monotonic() - self._last_call
                if elapsed < self.min_call_gap:
                    time.sleep(self.min_call_gap - elapsed)
                self._last_call = time.monotonic()

                df = yf.download(
                    tickers=ticker,
                    period=params["period"],
                    interval=params["interval"],
                    auto_adjust=False,
                    progress=False,
                    threads=False,
                )
                if df.empty:
                    raise RuntimeError(f"No OHLCV data returned for {ticker} {timeframe}")
                return self._normalize_download(df, ticker)
            except Exception as exc:
                logger.warning("Market data fetch failed", extra={"ticker": ticker, "attempt": attempt})
                if attempt == self.retries:
                    raise
                time.sleep(self.retry_delay_seconds * attempt)
        raise RuntimeError(f"Failed to fetch market data for {ticker}")

    def _normalize_download(self, df: pd.DataFrame, ticker: str) -> pd.DataFrame:
        if isinstance(df.columns, pd.MultiIndex):
            ticker_levels = [
                level
                for level in range(df.columns.nlevels)
                if ticker in set(str(value) for value in df.columns.get_level_values(level))
            ]
            if ticker_levels:
                df = df.xs(ticker, axis=1, level=ticker_levels[-1], drop_level=True)
            else:
                df.columns = df.columns.get_level_values(0)

        df = df.rename(
            columns={
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume",
            }
        )
        normalized = pd.DataFrame(index=df.index)
        for column in ["open", "high", "low", "close", "volume"]:
            values = df[column]
            if isinstance(values, pd.DataFrame):
                values = values.iloc[:, 0]
            normalized[column] = pd.to_numeric(values, errors="coerce")
        normalized = normalized.dropna().copy()
        if normalized.empty:
            raise RuntimeError(f"No normalized OHLCV data returned for {ticker}")
        normalized.index = pd.to_datetime(normalized.index)
        return normalized
