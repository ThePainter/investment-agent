from abc import ABC, abstractmethod

from app.models.schemas import NewsArticle, WatchlistEntry


class NewsProvider(ABC):
    @abstractmethod
    def fetch(self, entry: WatchlistEntry, limit: int = 8) -> list[NewsArticle]:
        raise NotImplementedError

