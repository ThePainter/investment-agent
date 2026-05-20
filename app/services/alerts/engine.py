from sqlalchemy.orm import Session

from app.db.models import AlertORM, GeneratedSignalORM
from app.models.enums import ImpactLevel, NewsSentiment, SignalType
from app.models.schemas import FinalRecommendation, NewsArticle, TimeframeSignal


class AlertEngine:
    def evaluate(
        self,
        db: Session,
        recommendation: FinalRecommendation,
        signals: dict[str, TimeframeSignal],
        news: list[NewsArticle],
    ) -> None:
        ticker = recommendation.ticker
        latest = (
            db.query(GeneratedSignalORM)
            .filter_by(ticker=ticker, timeframe="1h")
            .order_by(GeneratedSignalORM.created_at.desc())
            .offset(1)
            .first()
        )
        current = signals.get("1h") or next(iter(signals.values()))
        if current.signal in {SignalType.BUY, SignalType.SELL}:
            self._create(db, ticker, f"new_{current.signal.lower()}_signal", current.explanation, "MEDIUM")
        if latest and latest.signal != current.signal:
            self._create(
                db,
                ticker,
                "signal_change",
                f"1h signal changed from {latest.signal} to {current.signal}",
                "MEDIUM",
            )
        if current.stop_loss and recommendation.current_price <= current.stop_loss:
            self._create(db, ticker, "stop_loss_reached", "Price reached the suggested stop-loss.", "HIGH")
        if current.take_profit and recommendation.current_price >= current.take_profit:
            self._create(db, ticker, "take_profit_reached", "Price reached take-profit 1.", "MEDIUM")
        for article in news:
            if article.impact == ImpactLevel.HIGH and article.sentiment == NewsSentiment.NEGATIVE:
                self._create(db, ticker, "strong_negative_news", article.title, "HIGH")
            if article.impact == ImpactLevel.HIGH and article.sentiment == NewsSentiment.POSITIVE:
                self._create(db, ticker, "strong_positive_news", article.title, "MEDIUM")
        db.commit()

    def _create(self, db: Session, ticker: str, alert_type: str, message: str, severity: str) -> None:
        exists = (
            db.query(AlertORM)
            .filter_by(ticker=ticker, alert_type=alert_type, message=message)
            .order_by(AlertORM.created_at.desc())
            .first()
        )
        if not exists:
            db.add(AlertORM(ticker=ticker, alert_type=alert_type, message=message, severity=severity))

