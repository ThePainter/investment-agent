from app.config import get_settings
from app.services.news.base import NewsProvider
from app.services.news.google_rss import GoogleNewsRSSProvider


def get_news_provider() -> NewsProvider:
    settings = get_settings()
    if settings.news_provider == "google_rss":
        return GoogleNewsRSSProvider()
    raise ValueError(f"Unsupported news provider: {settings.news_provider}")

