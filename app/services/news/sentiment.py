import re

from app.models.enums import ImpactLevel, NewsSentiment

POSITIVE = {
    "beat",
    "raises",
    "raised",
    "upgrade",
    "contract",
    "partnership",
    "profit",
    "growth",
    "record",
    "approval",
    "buyback",
    "dividend",
}
NEGATIVE = {
    "miss",
    "cuts",
    "cut",
    "downgrade",
    "loss",
    "warning",
    "investigation",
    "lawsuit",
    "recall",
    "sanction",
    "delay",
    "dilution",
    "capital increase",
}
HIGH_IMPACT = {
    "earnings": "earnings",
    "guidance": "guidance",
    "contract": "contract",
    "acquisition": "acquisition",
    "merger": "acquisition",
    "rating": "analyst rating",
    "downgrade": "analyst rating",
    "upgrade": "analyst rating",
    "capital increase": "capital increase",
    "regulatory": "regulatory issue",
}


class NewsSentimentEngine:
    def classify(self, text: str) -> tuple[NewsSentiment, ImpactLevel, str]:
        lowered = text.lower()
        positive_score = sum(1 for word in POSITIVE if re.search(rf"\b{re.escape(word)}\b", lowered))
        negative_score = sum(1 for word in NEGATIVE if re.search(rf"\b{re.escape(word)}\b", lowered))

        if positive_score > negative_score:
            sentiment = NewsSentiment.POSITIVE
        elif negative_score > positive_score:
            sentiment = NewsSentiment.NEGATIVE
        else:
            sentiment = NewsSentiment.NEUTRAL

        event_type = "other"
        impact = ImpactLevel.LOW
        for marker, event in HIGH_IMPACT.items():
            if marker in lowered:
                event_type = event
                impact = ImpactLevel.HIGH if sentiment != NewsSentiment.NEUTRAL else ImpactLevel.MEDIUM
                break
        if impact == ImpactLevel.LOW and (positive_score + negative_score) >= 2:
            impact = ImpactLevel.MEDIUM
        return sentiment, impact, event_type

