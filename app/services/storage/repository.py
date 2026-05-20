import json

import pandas as pd
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import AlertORM, GeneratedSignalORM, NewsArticleORM, PriceCandleORM, TechnicalIndicatorORM
from app.models.schemas import NewsArticle, TimeframeSignal


class AnalysisRepository:
    def save_candles(self, db: Session, ticker: str, timeframe: str, candles: pd.DataFrame) -> None:
        for timestamp, row in candles.tail(500).iterrows():
            exists = (
                db.query(PriceCandleORM)
                .filter_by(ticker=ticker, timeframe=timeframe, timestamp=timestamp.to_pydatetime())
                .one_or_none()
            )
            if exists:
                continue
            db.add(
                PriceCandleORM(
                    ticker=ticker,
                    timeframe=timeframe,
                    timestamp=timestamp.to_pydatetime(),
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row["volume"]),
                )
            )
        db.commit()

    def save_indicators(self, db: Session, ticker: str, timeframe: str, indicators: pd.DataFrame) -> None:
        row = indicators.tail(1).iloc[0]
        timestamp = indicators.tail(1).index[0].to_pydatetime()
        payload = {k: (None if pd.isna(v) else float(v)) for k, v in row.items()}
        exists = (
            db.query(TechnicalIndicatorORM)
            .filter_by(ticker=ticker, timeframe=timeframe, timestamp=timestamp)
            .one_or_none()
        )
        if exists:
            exists.payload_json = json.dumps(payload)
        else:
            db.add(
                TechnicalIndicatorORM(
                    ticker=ticker,
                    timeframe=timeframe,
                    timestamp=timestamp,
                    payload_json=json.dumps(payload),
                )
            )
        db.commit()

    def save_signal(self, db: Session, signal: TimeframeSignal) -> None:
        db.add(
            GeneratedSignalORM(
                ticker=signal.ticker,
                timeframe=signal.timeframe,
                signal=signal.signal,
                confidence=signal.confidence,
                risk_level=signal.risk_level,
                explanation=signal.explanation,
                payload_json=signal.model_dump_json(),
            )
        )
        db.commit()

    def save_news(self, db: Session, articles: list[NewsArticle]) -> None:
        seen_urls: set[str] = set()
        for article in articles:
            if not article.url:
                continue
            url = article.url[:2048]
            if url in seen_urls:
                continue
            seen_urls.add(url)
            exists = db.query(NewsArticleORM).filter_by(url=url).one_or_none()
            if exists:
                continue
            db.add(
                NewsArticleORM(
                    ticker=article.ticker,
                    title=article.title[:256],
                    source=article.source[:128],
                    published_at=article.published_at,
                    url=url,
                    summary=article.summary,
                    sentiment=article.sentiment,
                    impact=article.impact,
                    event_type=article.event_type,
                )
            )
        try:
            db.commit()
        except IntegrityError:
            db.rollback()

    def latest_alerts(self, db: Session, limit: int = 50) -> list[AlertORM]:
        return db.query(AlertORM).order_by(AlertORM.created_at.desc()).limit(limit).all()
