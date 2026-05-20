import pandas as pd

from app.models.enums import Momentum, RiskLevel, SignalType, TrendDirection
from app.models.schemas import TimeframeSignal


def _pct_distance(a: float, b: float) -> float:
    return abs(a - b) / b * 100 if b else 0.0


class SignalEngine:
    def analyze(self, ticker: str, timeframe: str, indicators: pd.DataFrame) -> TimeframeSignal:
        df = indicators.dropna(subset=["close", "ema_20", "ema_50", "rsi_14", "macd_histogram"])
        if len(df) < 3:
            return TimeframeSignal(
                ticker=ticker,
                timeframe=timeframe,
                signal=SignalType.WATCH,
                confidence=20,
                risk_level=RiskLevel.HIGH,
                explanation="Insufficient indicator history for a reliable signal.",
                trend_direction=TrendDirection.NEUTRAL,
                momentum=Momentum.WEAK,
                volatility_level=RiskLevel.HIGH,
            )

        latest = df.iloc[-1]
        previous = df.iloc[-2]
        price = float(latest["close"])
        atr = float(latest.get("atr_14", 0) or 0)
        atr_pct = atr / price * 100 if price else 0
        support = latest.get("nearest_support")
        resistance = latest.get("nearest_resistance")
        support = float(support) if pd.notna(support) else None
        resistance = float(resistance) if pd.notna(resistance) else None

        bullish_points: list[str] = []
        bearish_points: list[str] = []
        score = 0.0

        if price > latest["ema_20"] > latest["ema_50"]:
            score += 22
            bullish_points.append("price is above EMA 20 and EMA 50")
        elif price < latest["ema_20"] < latest["ema_50"]:
            score -= 22
            bearish_points.append("price is below EMA 20 and EMA 50")

        if previous["ema_9"] <= previous["ema_20"] and latest["ema_9"] > latest["ema_20"]:
            score += 18
            bullish_points.append("EMA 9 crossed above EMA 20")
        if previous["ema_9"] >= previous["ema_20"] and latest["ema_9"] < latest["ema_20"]:
            score -= 18
            bearish_points.append("EMA 9 crossed below EMA 20")

        rsi = float(latest["rsi_14"])
        if 45 <= rsi <= 70:
            score += 14
            bullish_points.append("RSI is in a constructive range")
        elif rsi > 75:
            score -= 20
            bearish_points.append("RSI is overbought")
        elif rsi < 45:
            score -= 14
            bearish_points.append("RSI is below 45")

        if previous["macd_histogram"] <= 0 < latest["macd_histogram"]:
            score += 16
            bullish_points.append("MACD histogram turned positive")
        elif previous["macd_histogram"] >= 0 > latest["macd_histogram"]:
            score -= 16
            bearish_points.append("MACD histogram turned negative")
        elif latest["macd_histogram"] > previous["macd_histogram"]:
            score += 6
            bullish_points.append("MACD momentum is improving")
        else:
            score -= 4

        if latest["volume"] > latest.get("volume_ma_20", latest["volume"]) * 1.2:
            score += 8
            bullish_points.append("volume is above average")

        if support and price < support:
            score -= 18
            bearish_points.append("support was broken")
        if resistance and price > resistance:
            score += 12
            bullish_points.append("price broke above resistance")

        distance_from_ema20 = _pct_distance(price, float(latest["ema_20"]))
        if distance_from_ema20 > 12:
            score -= 10
            bearish_points.append("price is extended from EMA 20")

        trend = (
            TrendDirection.BULLISH
            if score > 15
            else TrendDirection.BEARISH
            if score < -15
            else TrendDirection.NEUTRAL
        )
        volatility = RiskLevel.HIGH if atr_pct > 6 else RiskLevel.MEDIUM if atr_pct > 3 else RiskLevel.LOW
        if rsi > 75:
            momentum = Momentum.EXHAUSTED
        elif abs(score) > 35:
            momentum = Momentum.STRONG
        elif previous["macd_histogram"] * latest["macd_histogram"] < 0:
            momentum = Momentum.REVERSING
        else:
            momentum = Momentum.WEAK

        if score >= 45:
            signal = SignalType.BUY
        elif score <= -45:
            signal = SignalType.SELL
        elif score >= 20:
            signal = SignalType.WATCH
        elif score <= -20:
            signal = SignalType.AVOID
        else:
            signal = SignalType.HOLD

        stop_loss = support or price - (2 * atr if atr else price * 0.05)
        take_profit = resistance if resistance and resistance > price else price + (2.5 * atr if atr else price * 0.08)
        take_profit_2 = price + (4 * atr if atr else price * 0.14)
        downside = max(price - stop_loss, 0.01)
        upside = max(take_profit - price, 0.01)
        rr = upside / downside
        risk = RiskLevel.HIGH if volatility == RiskLevel.HIGH or rr < 1 else RiskLevel.MEDIUM if rr < 1.8 else RiskLevel.LOW
        confidence = int(max(0, min(100, 50 + score)))
        explanation_parts = bullish_points + bearish_points
        explanation = "; ".join(explanation_parts) or "No dominant technical edge."

        return TimeframeSignal(
            ticker=ticker,
            timeframe=timeframe,
            signal=signal,
            confidence=confidence,
            risk_level=risk,
            explanation=explanation,
            suggested_entry=round(price, 4),
            stop_loss=round(stop_loss, 4),
            take_profit=round(take_profit, 4),
            take_profit_2=round(take_profit_2, 4),
            risk_reward_ratio=round(rr, 2),
            invalidation_level=round(stop_loss, 4),
            trend_direction=trend,
            momentum=momentum,
            volatility_level=volatility,
            score=score,
        )

