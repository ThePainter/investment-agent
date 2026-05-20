from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.enums import (
    ImpactLevel,
    Momentum,
    NewsSentiment,
    RecommendationType,
    RiskLevel,
    SignalType,
    TrendDirection,
)


class WatchlistEntry(BaseModel):
    ticker: str
    exchange: str = ""
    company_name: str = ""
    currency: str = ""
    sector: str = ""
    country: str = ""
    shares_owned: Optional[float] = None
    average_buy_price: Optional[float] = None
    investment_amount: Optional[float] = None


class TradingViewImportRequest(BaseModel):
    symbols: str
    default_currency: str = ""
    default_sector: str = ""
    default_country: str = ""


class Candle(BaseModel):
    ticker: str
    timeframe: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class TimeframeSignal(BaseModel):
    ticker: str
    timeframe: str
    signal: SignalType
    confidence: int = Field(ge=0, le=100)
    risk_level: RiskLevel
    explanation: str
    suggested_entry: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    take_profit_2: Optional[float] = None
    risk_reward_ratio: Optional[float] = None
    invalidation_level: Optional[float] = None
    trend_direction: TrendDirection
    momentum: Momentum
    volatility_level: RiskLevel
    score: float = 0.0


class NewsArticle(BaseModel):
    ticker: str
    title: str
    source: str
    published_at: Optional[datetime] = None
    url: str
    summary: str = ""
    sentiment: NewsSentiment = NewsSentiment.NEUTRAL
    impact: ImpactLevel = ImpactLevel.LOW
    event_type: str = "other"


class PortfolioSnapshot(BaseModel):
    ticker: str
    shares: float
    average_buy_price: float
    invested_amount: float
    current_market_value: float
    unrealized_gain_loss: float
    unrealized_gain_loss_pct: float
    distance_to_stop_loss_pct: Optional[float] = None
    distance_to_take_profit_pct: Optional[float] = None
    recommended_action: str


class FinalRecommendation(BaseModel):
    ticker: str
    company_name: str
    current_price: float
    daily_change_pct: Optional[float] = None
    recommendation: RecommendationType
    overall_score: int = Field(ge=0, le=100)
    confidence: int = Field(ge=0, le=100)
    risk_level: RiskLevel
    explanation: str
    positive_factors: list[str]
    negative_factors: list[str]
    suggested_action: str
    entry_zone: Optional[str] = None
    stop_loss: Optional[float] = None
    take_profit_1: Optional[float] = None
    take_profit_2: Optional[float] = None
    upside_pct: Optional[float] = None
    downside_pct: Optional[float] = None
    risk_reward_ratio: Optional[float] = None
    news_sentiment: NewsSentiment = NewsSentiment.NEUTRAL
    latest_important_news: Optional[str] = None
    portfolio: Optional[PortfolioSnapshot] = None
    last_analysis_time: datetime
