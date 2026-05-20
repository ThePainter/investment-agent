from app.models.enums import Momentum, RiskLevel, SignalType, TrendDirection
from app.models.schemas import TimeframeSignal
from app.services.portfolio.engine import PortfolioEngine


def test_portfolio_gain_loss():
    signal = TimeframeSignal(
        ticker="MSFT",
        timeframe="1h",
        signal=SignalType.HOLD,
        confidence=60,
        risk_level=RiskLevel.MEDIUM,
        explanation="test",
        stop_loss=90,
        take_profit=130,
        trend_direction=TrendDirection.NEUTRAL,
        momentum=Momentum.WEAK,
        volatility_level=RiskLevel.LOW,
    )
    snapshot = PortfolioEngine().calculate("MSFT", 10, 100, 120, signal)
    assert snapshot is not None
    assert snapshot.current_market_value == 1200
    assert snapshot.unrealized_gain_loss == 200
    assert snapshot.unrealized_gain_loss_pct == 20

