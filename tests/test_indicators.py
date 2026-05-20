import pandas as pd

from app.services.indicators.engine import IndicatorEngine


def sample_candles(rows: int = 260) -> pd.DataFrame:
    index = pd.date_range("2025-01-01", periods=rows, freq="D")
    close = [float(value) for value in range(100, 100 + rows)]
    return pd.DataFrame(
        {
            "open": [value - 1 for value in close],
            "high": [value + 2 for value in close],
            "low": [value - 2 for value in close],
            "close": close,
            "volume": [1000 + i for i in range(rows)],
        },
        index=index,
    )


def test_indicator_engine_calculates_required_columns():
    df = IndicatorEngine().calculate(sample_candles())
    for column in [
        "ema_9",
        "ema_20",
        "ema_50",
        "ema_200",
        "sma_50",
        "sma_200",
        "rsi_14",
        "macd",
        "macd_signal",
        "macd_histogram",
        "bollinger_upper",
        "atr_14",
        "volume_ma_20",
        "vwap",
    ]:
        assert column in df.columns
    assert df["ema_20"].iloc[-1] > df["ema_50"].iloc[-1]


def test_support_resistance_returns_recent_levels():
    df = IndicatorEngine().calculate(sample_candles())
    support, resistance = IndicatorEngine().support_resistance(df)
    assert support is None or support > 0
    assert resistance is None or resistance > 0
