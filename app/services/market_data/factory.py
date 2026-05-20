from app.config import get_settings
from app.services.market_data.base import MarketDataProvider
from app.services.market_data.yahoo import YahooFinanceProvider


def get_market_data_provider() -> MarketDataProvider:
    settings = get_settings()
    if settings.market_data_provider == "yahoo":
        return YahooFinanceProvider()
    raise ValueError(f"Unsupported market data provider: {settings.market_data_provider}")

