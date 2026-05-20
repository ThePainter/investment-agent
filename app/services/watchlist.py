from pathlib import Path
import re

import yaml
from sqlalchemy.orm import Session

from app.db.models import PortfolioPositionORM, WatchlistItemORM
from app.models.schemas import WatchlistEntry

YAHOO_SUFFIX_BY_TRADINGVIEW_EXCHANGE = {
    "EPA": ".PA",
    "EURONEXT": ".PA",
    "PAR": ".PA",
    "XETR": ".DE",
    "XETRA": ".DE",
    "FWB": ".F",
}
SPECIAL_TRADINGVIEW_TICKERS = {
    ("MIL", "1RHM"): "RHM.DE",
}
CRYPTO_TICKERS = {"BTCUSD": "BTC-USD", "ETHUSD": "ETH-USD", "XRPUSD": "XRP-USD"}


class WatchlistService:
    def __init__(self, config_path: Path):
        self.config_path = config_path

    def load_from_file(self) -> list[WatchlistEntry]:
        data = yaml.safe_load(self.config_path.read_text()) if self.config_path.exists() else {}
        return [WatchlistEntry(**item) for item in data.get("watchlist", [])]

    def list_entries(self, db: Session) -> list[WatchlistEntry]:
        if db.query(WatchlistItemORM).count() == 0:
            self.seed_from_file(db)
        self.normalize_existing_entries(db)
        return [
            self._entry_from_orm(item)
            for item in db.query(WatchlistItemORM).order_by(WatchlistItemORM.ticker.asc()).all()
        ]

    def seed_from_file(self, db: Session) -> list[WatchlistEntry]:
        entries = self.load_from_file()
        for entry in entries:
            self.upsert(db, entry, commit=False)
        db.commit()
        return self.list_entries(db)

    def upsert(self, db: Session, entry: WatchlistEntry, commit: bool = True) -> WatchlistEntry:
        ticker = entry.ticker.strip().upper()
        if not ticker:
            raise ValueError("Ticker is required")
        normalized = entry.model_copy(update={"ticker": ticker, "company_name": entry.company_name or ticker})
        existing = db.query(WatchlistItemORM).filter_by(ticker=ticker).one_or_none()
        values = normalized.model_dump()
        if existing:
            for key, value in values.items():
                setattr(existing, key, value)
        else:
            existing = WatchlistItemORM(**values)
            db.add(existing)

        self._sync_position(db, normalized)
        if commit:
            db.commit()
            db.refresh(existing)
        return self._entry_from_orm(existing)

    def remove(self, db: Session, ticker: str) -> bool:
        normalized = ticker.strip().upper()
        item = db.query(WatchlistItemORM).filter_by(ticker=normalized).one_or_none()
        if not item:
            return False
        position = db.query(PortfolioPositionORM).filter_by(ticker=normalized).one_or_none()
        if position:
            db.delete(position)
        db.delete(item)
        db.commit()
        return True

    def normalize_existing_entries(self, db: Session) -> None:
        changed = False
        for item in db.query(WatchlistItemORM).all():
            old_ticker = item.ticker
            mapped = self._to_market_data_ticker(item.exchange.upper(), old_ticker.upper())
            if mapped == old_ticker:
                continue
            duplicate = db.query(WatchlistItemORM).filter_by(ticker=mapped).one_or_none()
            if duplicate:
                position = db.query(PortfolioPositionORM).filter_by(ticker=old_ticker).one_or_none()
                if position:
                    db.delete(position)
                db.delete(item)
            else:
                position = db.query(PortfolioPositionORM).filter_by(ticker=old_ticker).one_or_none()
                if position:
                    position.ticker = mapped
                item.ticker = mapped
                if item.company_name == old_ticker or item.company_name in {"1RHM", "BTCUSD", "ETHUSD", "XRPUSD"}:
                    item.company_name = mapped
            changed = True
        if changed:
            db.commit()

    def import_tradingview_symbols(
        self,
        db: Session,
        symbols: str,
        default_currency: str = "",
        default_sector: str = "",
        default_country: str = "",
    ) -> list[WatchlistEntry]:
        entries = [
            self._import_one(db, exchange, ticker, default_currency, default_sector, default_country)
            for exchange, ticker in self.parse_tradingview_symbols(symbols)
        ]
        db.commit()
        return entries

    def parse_tradingview_symbols(self, symbols: str) -> list[tuple[str, str]]:
        parsed: list[tuple[str, str]] = []
        seen: set[str] = set()
        for raw in re.split(r"[\s,;]+", symbols.strip()):
            token = raw.strip().strip('"').strip("'")
            if not token:
                continue
            exchange = ""
            ticker = token
            if ":" in token:
                exchange, ticker = token.split(":", 1)
            ticker = ticker.strip().upper()
            exchange = exchange.strip().upper()
            ticker = self._to_market_data_ticker(exchange, ticker)
            if not ticker or ticker in seen:
                continue
            seen.add(ticker)
            parsed.append((exchange, ticker))
        return parsed

    def _to_market_data_ticker(self, exchange: str, ticker: str) -> str:
        special = SPECIAL_TRADINGVIEW_TICKERS.get((exchange, ticker))
        if special:
            return special
        if exchange in {"KRAKEN", "BINANCE", "COINBASE", "BITSTAMP"} and ticker in CRYPTO_TICKERS:
            return CRYPTO_TICKERS[ticker]
        if "." in ticker:
            return ticker
        suffix = YAHOO_SUFFIX_BY_TRADINGVIEW_EXCHANGE.get(exchange)
        return f"{ticker}{suffix}" if suffix else ticker

    def _sync_position(self, db: Session, entry: WatchlistEntry) -> None:
        position = db.query(PortfolioPositionORM).filter_by(ticker=entry.ticker).one_or_none()
        if entry.shares_owned and entry.average_buy_price:
            invested = entry.investment_amount or entry.shares_owned * entry.average_buy_price
            if position:
                position.shares = entry.shares_owned
                position.average_buy_price = entry.average_buy_price
                position.invested_amount = invested
            else:
                db.add(
                    PortfolioPositionORM(
                        ticker=entry.ticker,
                        shares=entry.shares_owned,
                        average_buy_price=entry.average_buy_price,
                        invested_amount=invested,
                    )
                )
        elif position:
            db.delete(position)

    def _import_one(
        self,
        db: Session,
        exchange: str,
        ticker: str,
        default_currency: str,
        default_sector: str,
        default_country: str,
    ) -> WatchlistEntry:
        existing = db.query(WatchlistItemORM).filter_by(ticker=ticker).one_or_none()
        if existing:
            return self._entry_from_orm(existing)
        return self.upsert(
            db,
            WatchlistEntry(
                ticker=ticker,
                exchange=exchange,
                company_name=ticker,
                currency=default_currency,
                sector=default_sector,
                country=default_country,
            ),
            commit=False,
        )

    def _entry_from_orm(self, item: WatchlistItemORM) -> WatchlistEntry:
        return WatchlistEntry(
            ticker=item.ticker,
            exchange=item.exchange,
            company_name=item.company_name,
            currency=item.currency,
            sector=item.sector,
            country=item.country,
            shares_owned=item.shares_owned,
            average_buy_price=item.average_buy_price,
            investment_amount=item.investment_amount,
        )
