from __future__ import annotations

import numpy as np
import pandas as pd


class IndicatorEngine:
    def calculate(self, candles: pd.DataFrame) -> pd.DataFrame:
        df = candles.copy()
        for period in (9, 20, 50, 200):
            df[f"ema_{period}"] = df["close"].ewm(span=period, adjust=False).mean()
        for period in (50, 200):
            df[f"sma_{period}"] = df["close"].rolling(period).mean()

        delta = df["close"].diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        df["rsi_14"] = 100 - (100 / (1 + rs))
        df.loc[(loss == 0) & (gain > 0), "rsi_14"] = 100
        df.loc[(loss == 0) & (gain == 0), "rsi_14"] = 50

        ema_12 = df["close"].ewm(span=12, adjust=False).mean()
        ema_26 = df["close"].ewm(span=26, adjust=False).mean()
        df["macd"] = ema_12 - ema_26
        df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
        df["macd_histogram"] = df["macd"] - df["macd_signal"]

        sma_20 = df["close"].rolling(20).mean()
        std_20 = df["close"].rolling(20).std()
        df["bollinger_mid"] = sma_20
        df["bollinger_upper"] = sma_20 + 2 * std_20
        df["bollinger_lower"] = sma_20 - 2 * std_20

        high_low = df["high"] - df["low"]
        high_close = (df["high"] - df["close"].shift()).abs()
        low_close = (df["low"] - df["close"].shift()).abs()
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df["atr_14"] = true_range.rolling(14).mean()

        df["volume_ma_20"] = df["volume"].rolling(20).mean()
        typical_price = (df["high"] + df["low"] + df["close"]) / 3
        cumulative_volume = df["volume"].replace(0, np.nan).cumsum()
        df["vwap"] = (typical_price * df["volume"]).cumsum() / cumulative_volume

        df["swing_high"] = df["high"][
            (df["high"] > df["high"].shift(1)) & (df["high"] > df["high"].shift(-1))
        ]
        df["swing_low"] = df["low"][
            (df["low"] < df["low"].shift(1)) & (df["low"] < df["low"].shift(-1))
        ]
        df["nearest_resistance"] = df["swing_high"].ffill()
        df["nearest_support"] = df["swing_low"].ffill()
        return df

    def support_resistance(self, indicators: pd.DataFrame, lookback: int = 80) -> tuple[float | None, float | None]:
        recent = indicators.tail(lookback)
        support = recent["swing_low"].dropna().tail(1)
        resistance = recent["swing_high"].dropna().tail(1)
        return (
            float(support.iloc[-1]) if not support.empty else None,
            float(resistance.iloc[-1]) if not resistance.empty else None,
        )
