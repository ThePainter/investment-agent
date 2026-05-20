from __future__ import annotations

import logging
from datetime import datetime

import pandas as pd
from sqlalchemy.orm import Session

from app.models.enums import NewsSentiment, RecommendationType, RiskLevel
from app.config import get_settings
from app.models.schemas import FinalRecommendation, WatchlistEntry
from app.services.alerts.engine import AlertEngine
from app.services.indicators.engine import IndicatorEngine
from app.services.market_data.factory import get_market_data_provider
from app.services.news.factory import get_news_provider
from app.services.portfolio.engine import PortfolioEngine
from app.services.recommendations.aggregator import RecommendationAggregator
from app.services.signals.engine import SignalEngine
from app.services.storage.repository import AnalysisRepository
from app.services.watchlist import WatchlistService

logger = logging.getLogger(__name__)
TIMEFRAMES = ["5m", "15m", "1h", "1d"]


class AnalysisService:
    def __init__(self):
        self.settings = get_settings()
        self.market_data = get_market_data_provider()
        self.news = get_news_provider()
        self.indicators = IndicatorEngine()
        self.signals = SignalEngine()
        self.portfolio = PortfolioEngine()
        self.aggregator = RecommendationAggregator()
        self.repo = AnalysisRepository()
        self.alerts = AlertEngine()

    def watchlist(self, db: Session) -> list[WatchlistEntry]:
        return WatchlistService(self.settings.watchlist_config).list_entries(db)

    def analyze_watchlist(self, db: Session) -> list[FinalRecommendation]:
        recommendations: list[FinalRecommendation] = []
        for entry in self.watchlist(db):
            try:
                recommendations.append(self.analyze_stock(db, entry))
            except Exception as exc:
                logger.exception("Analysis failed for ticker", extra={"ticker": entry.ticker})
                recommendations.append(self._unavailable_recommendation(entry, exc))
        return recommendations

    def analyze_stock(self, db: Session, entry: WatchlistEntry) -> FinalRecommendation:
        timeframe_signals = {}
        indicator_frames: dict[str, pd.DataFrame] = {}
        candles_by_timeframe: dict[str, pd.DataFrame] = {}

        for timeframe in TIMEFRAMES:
            candles = self.market_data.fetch_ohlcv(entry.ticker, timeframe)
            indicators = self.indicators.calculate(candles)
            signal = self.signals.analyze(entry.ticker, timeframe, indicators)
            self.repo.save_candles(db, entry.ticker, timeframe, candles)
            self.repo.save_indicators(db, entry.ticker, timeframe, indicators)
            self.repo.save_signal(db, signal)
            timeframe_signals[timeframe] = signal
            indicator_frames[timeframe] = indicators
            candles_by_timeframe[timeframe] = candles

        daily = candles_by_timeframe["1d"]
        current_price = float(daily["close"].iloc[-1])
        previous_close = float(daily["close"].iloc[-2]) if len(daily) > 1 else current_price
        daily_change_pct = (current_price - previous_close) / previous_close * 100 if previous_close else None
        articles = self.news.fetch(entry)
        self.repo.save_news(db, articles)
        primary_signal = timeframe_signals.get("1h") or timeframe_signals["1d"]
        portfolio_snapshot = self.portfolio.calculate(
            entry.ticker,
            entry.shares_owned,
            entry.average_buy_price,
            current_price,
            primary_signal,
        )
        recommendation = self.aggregator.aggregate(
            entry, current_price, daily_change_pct, timeframe_signals, articles, portfolio_snapshot
        )
        self.alerts.evaluate(db, recommendation, timeframe_signals, articles)
        return recommendation

    def stock_detail(self, db: Session, ticker: str) -> dict:
        entry = next(item for item in self.watchlist(db) if item.ticker == ticker)
        try:
            recommendation = self.analyze_stock(db, entry)
            candles = self.market_data.fetch_ohlcv(ticker, "1d")
            indicators = self.indicators.calculate(candles)
            articles = self.news.fetch(entry)
            signals = {
                timeframe: self.signals.analyze(
                    ticker,
                    timeframe,
                    self.indicators.calculate(self.market_data.fetch_ohlcv(ticker, timeframe)),
                )
                for timeframe in TIMEFRAMES
            }
            return {
                "recommendation": recommendation.model_dump(mode="json"),
                "signals": {key: value.model_dump(mode="json") for key, value in signals.items()},
                "news": [article.model_dump(mode="json") for article in articles],
                "chart": indicators.tail(250).reset_index(names="timestamp").to_dict(orient="records"),
            }
        except Exception as exc:
            logger.exception("Detail analysis failed", extra={"ticker": ticker})
            return {
                "recommendation": self._unavailable_recommendation(entry, exc).model_dump(mode="json"),
                "signals": {},
                "news": [],
                "chart": [],
            }

    def _unavailable_recommendation(
        self, entry: WatchlistEntry, error: Exception
    ) -> FinalRecommendation:
        return FinalRecommendation(
            ticker=entry.ticker,
            company_name=entry.company_name or entry.ticker,
            current_price=0,
            daily_change_pct=None,
            recommendation=RecommendationType.AVOID,
            overall_score=0,
            confidence=0,
            risk_level=RiskLevel.HIGH,
            explanation=f"Analysis unavailable: {error}",
            positive_factors=[],
            negative_factors=["Market data provider returned no usable OHLCV data."],
            suggested_action="Fix or remove this ticker, then refresh analysis.",
            entry_zone=None,
            stop_loss=None,
            take_profit_1=None,
            take_profit_2=None,
            upside_pct=None,
            downside_pct=None,
            risk_reward_ratio=None,
            news_sentiment=NewsSentiment.NEUTRAL,
            latest_important_news=None,
            portfolio=None,
            last_analysis_time=datetime.utcnow(),
        )
