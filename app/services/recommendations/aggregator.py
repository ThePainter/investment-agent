from __future__ import annotations

from datetime import datetime

from app.models.enums import ImpactLevel, NewsSentiment, RecommendationType, RiskLevel, SignalType
from app.models.schemas import (
    FinalRecommendation,
    NewsArticle,
    PortfolioSnapshot,
    TimeframeSignal,
    WatchlistEntry,
)


WEIGHTS = {"5m": 0.15, "15m": 0.2, "1h": 0.3, "1d": 0.35}


class RecommendationAggregator:
    def aggregate(
        self,
        entry: WatchlistEntry,
        current_price: float,
        daily_change_pct: float | None,
        signals: dict[str, TimeframeSignal],
        news: list[NewsArticle],
        portfolio: PortfolioSnapshot | None,
    ) -> FinalRecommendation:
        weighted_score = 50.0
        positives: list[str] = []
        negatives: list[str] = []

        for timeframe, signal in signals.items():
            weight = WEIGHTS.get(timeframe, 0.0)
            weighted_score += signal.score * weight
            if signal.signal in {SignalType.BUY, SignalType.WATCH}:
                positives.append(f"{timeframe}: {signal.explanation}")
            if signal.signal in {SignalType.SELL, SignalType.AVOID}:
                negatives.append(f"{timeframe}: {signal.explanation}")

        latest_important = next(
            (item for item in news if item.impact in {ImpactLevel.HIGH, ImpactLevel.MEDIUM}),
            news[0] if news else None,
        )
        negative_news = [
            item for item in news if item.sentiment == NewsSentiment.NEGATIVE and item.impact == ImpactLevel.HIGH
        ]
        positive_news = [
            item for item in news if item.sentiment == NewsSentiment.POSITIVE and item.impact == ImpactLevel.HIGH
        ]
        if negative_news:
            weighted_score -= 20
            negatives.append(f"High-impact negative news: {negative_news[0].title}")
        if positive_news:
            weighted_score += 8
            positives.append(f"High-impact positive news: {positive_news[0].title}")

        daily = signals.get("1d")
        hourly = signals.get("1h")
        primary = hourly or daily or next(iter(signals.values()))
        if daily and daily.trend_direction == "BEARISH" and primary.signal == SignalType.BUY:
            weighted_score -= 12
            negatives.append("Daily trend does not confirm the intraday setup")

        score = int(max(0, min(100, weighted_score)))
        recommendation = self._recommendation(score, bool(negative_news), portfolio)
        risk = self._risk(signals, negative_news)
        action = self._action(recommendation, portfolio)
        stop = primary.stop_loss
        tp1 = primary.take_profit
        tp2 = primary.take_profit_2
        upside = ((tp1 - current_price) / current_price * 100) if tp1 else None
        downside = ((current_price - stop) / current_price * 100) if stop else None

        news_sentiment = NewsSentiment.NEUTRAL
        if negative_news:
            news_sentiment = NewsSentiment.NEGATIVE
        elif positive_news:
            news_sentiment = NewsSentiment.POSITIVE
        elif news:
            news_sentiment = news[0].sentiment

        return FinalRecommendation(
            ticker=entry.ticker,
            company_name=entry.company_name,
            current_price=current_price,
            daily_change_pct=daily_change_pct,
            recommendation=recommendation,
            overall_score=score,
            confidence=int(sum(s.confidence for s in signals.values()) / len(signals)),
            risk_level=risk,
            explanation=self._explanation(recommendation, positives, negatives),
            positive_factors=positives[:6],
            negative_factors=negatives[:6],
            suggested_action=action,
            entry_zone=f"{primary.suggested_entry}" if primary.suggested_entry else None,
            stop_loss=stop,
            take_profit_1=tp1,
            take_profit_2=tp2,
            upside_pct=upside,
            downside_pct=downside,
            risk_reward_ratio=primary.risk_reward_ratio,
            news_sentiment=news_sentiment,
            latest_important_news=latest_important.title if latest_important else None,
            portfolio=portfolio,
            last_analysis_time=datetime.utcnow(),
        )

    def _recommendation(
        self, score: int, has_high_negative_news: bool, portfolio: PortfolioSnapshot | None
    ) -> RecommendationType:
        if has_high_negative_news:
            return RecommendationType.AVOID if score < 55 else RecommendationType.WATCH
        if score >= 78:
            return RecommendationType.STRONG_BUY
        if score >= 65:
            return RecommendationType.BUY
        if score >= 52:
            return RecommendationType.HOLD if portfolio else RecommendationType.WATCH
        if score >= 42:
            return RecommendationType.WATCH
        if score >= 30:
            return RecommendationType.REDUCE if portfolio else RecommendationType.AVOID
        return RecommendationType.SELL if portfolio else RecommendationType.AVOID

    def _risk(self, signals: dict[str, TimeframeSignal], negative_news: list[NewsArticle]) -> RiskLevel:
        if negative_news or any(signal.risk_level == RiskLevel.HIGH for signal in signals.values()):
            return RiskLevel.HIGH
        if any(signal.risk_level == RiskLevel.MEDIUM for signal in signals.values()):
            return RiskLevel.MEDIUM
        return RiskLevel.LOW

    def _action(
        self, recommendation: RecommendationType, portfolio: PortfolioSnapshot | None
    ) -> str:
        if portfolio:
            return portfolio.recommended_action
        return {
            RecommendationType.STRONG_BUY: "Consider phased entry if risk controls fit.",
            RecommendationType.BUY: "Consider entry near the stated zone.",
            RecommendationType.WATCH: "Wait for confirmation.",
            RecommendationType.HOLD: "No new action.",
            RecommendationType.REDUCE: "Avoid new buying; reduce only if already held.",
            RecommendationType.SELL: "No new entry; bearish setup.",
            RecommendationType.AVOID: "Avoid until technicals and news improve.",
        }[recommendation]

    def _explanation(self, recommendation: RecommendationType, positives: list[str], negatives: list[str]) -> str:
        if negatives and positives:
            return f"{recommendation}: mixed setup with both confirming and invalidating factors."
        if positives:
            return f"{recommendation}: technical and/or news factors are supportive."
        if negatives:
            return f"{recommendation}: risk factors outweigh bullish confirmation."
        return f"{recommendation}: no clear edge across the monitored timeframes."
