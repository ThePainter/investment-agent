from app.models.enums import SignalType
from app.services.indicators.engine import IndicatorEngine
from app.services.signals.engine import SignalEngine
from tests.test_indicators import sample_candles


def test_signal_engine_returns_explainable_signal():
    indicators = IndicatorEngine().calculate(sample_candles())
    signal = SignalEngine().analyze("TEST", "1d", indicators)
    assert signal.signal in set(SignalType)
    assert 0 <= signal.confidence <= 100
    assert signal.explanation
    assert signal.risk_reward_ratio is not None

