from datetime import datetime

from app.models.enums import Momentum, RiskLevel, SignalType, TrendDirection
from app.models.schemas import TimeframeSignal, WatchlistEntry
from app.services.recommendations.aggregator import RecommendationAggregator


def make_signal(timeframe: str, score: float) -> TimeframeSignal:
    return TimeframeSignal(
        ticker="NVDA",
        timeframe=timeframe,
        signal=SignalType.BUY,
        confidence=80,
        risk_level=RiskLevel.LOW,
        explanation="price above moving averages",
        suggested_entry=100,
        stop_loss=95,
        take_profit=115,
        take_profit_2=125,
        risk_reward_ratio=3,
        trend_direction=TrendDirection.BULLISH,
        momentum=Momentum.STRONG,
        volatility_level=RiskLevel.LOW,
        score=score,
    )


def test_aggregator_creates_buy_recommendation():
    entry = WatchlistEntry(
        ticker="NVDA",
        exchange="NASDAQ",
        company_name="NVIDIA",
        currency="USD",
        sector="Technology",
        country="United States",
    )
    rec = RecommendationAggregator().aggregate(
        entry,
        100,
        1.5,
        {tf: make_signal(tf, 40) for tf in ["5m", "15m", "1h", "1d"]},
        [],
        None,
    )
    assert rec.overall_score >= 65
    assert rec.last_analysis_time <= datetime.utcnow()

