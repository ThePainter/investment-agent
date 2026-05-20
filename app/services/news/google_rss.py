from datetime import datetime
from urllib.parse import quote_plus

import feedparser

from app.models.schemas import NewsArticle, WatchlistEntry
from app.services.news.base import NewsProvider
from app.services.news.sentiment import NewsSentimentEngine


class GoogleNewsRSSProvider(NewsProvider):
    def __init__(self):
        self.sentiment = NewsSentimentEngine()

    def fetch(self, entry: WatchlistEntry, limit: int = 8) -> list[NewsArticle]:
        query = quote_plus(f"{entry.company_name} {entry.ticker} stock")
        url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
        parsed = feedparser.parse(url)
        articles: list[NewsArticle] = []
        for item in parsed.entries[:limit]:
            text = f"{getattr(item, 'title', '')} {getattr(item, 'summary', '')}"
            sentiment, impact, event_type = self.sentiment.classify(text)
            published = None
            if getattr(item, "published_parsed", None):
                published = datetime(*item.published_parsed[:6])
            articles.append(
                NewsArticle(
                    ticker=entry.ticker,
                    title=getattr(item, "title", "Untitled"),
                    source=getattr(item, "source", {}).get("title", "Google News"),
                    published_at=published,
                    url=getattr(item, "link", ""),
                    summary=getattr(item, "summary", ""),
                    sentiment=sentiment,
                    impact=impact,
                    event_type=event_type,
                )
            )
        return articles

