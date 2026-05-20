import pandas as pd

from app.services.market_data.yahoo import YahooFinanceProvider


def test_normalize_download_handles_yfinance_multiindex_columns():
    index = pd.date_range("2026-01-01", periods=3, freq="D")
    columns = pd.MultiIndex.from_tuples(
        [
            ("Adj Close", "DSY.PA"),
            ("Close", "DSY.PA"),
            ("High", "DSY.PA"),
            ("Low", "DSY.PA"),
            ("Open", "DSY.PA"),
            ("Volume", "DSY.PA"),
        ],
        names=["Price", "Ticker"],
    )
    raw = pd.DataFrame(
        [
            [10, 10, 11, 9, 10, 1000],
            [11, 11, 12, 10, 11, 1100],
            [12, 12, 13, 11, 12, 1200],
        ],
        index=index,
        columns=columns,
    )

    normalized = YahooFinanceProvider()._normalize_download(raw, "DSY.PA")

    assert list(normalized.columns) == ["open", "high", "low", "close", "volume"]
    assert normalized["close"].iloc[-1] == 12

