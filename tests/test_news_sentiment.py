from app.models.enums import ImpactLevel, NewsSentiment
from app.services.news.sentiment import NewsSentimentEngine


def test_negative_high_impact_news():
    sentiment, impact, event_type = NewsSentimentEngine().classify(
        "Company cuts guidance after earnings miss"
    )
    assert sentiment == NewsSentiment.NEGATIVE
    assert impact == ImpactLevel.HIGH
    assert event_type in {"earnings", "guidance"}

