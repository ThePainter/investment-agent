from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "local"
    database_url: str = "sqlite:///./investment_agent.db"
    watchlist_config: Path = Path("config/watchlist.yml")
    market_data_provider: str = "yahoo"
    news_provider: str = "google_rss"
    log_level: str = "INFO"

    refresh_intraday_minutes: int = 5
    refresh_news_minutes: int = 30
    refresh_daily_hour: int = 18

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()

