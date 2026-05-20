from pathlib import Path

from app.db.models import WatchlistItemORM
from app.services.watchlist import WatchlistService


def test_parse_tradingview_symbols_accepts_prefixed_and_plain_tickers():
    service = WatchlistService(Path("missing.yml"))
    parsed = service.parse_tradingview_symbols(
        "NASDAQ:NVDA, NASDAQ:MSFT\nEURONEXT:ALDRV ALDRV XETR:RHM KRAKEN:BTCUSD MIL:1RHM"
    )
    assert parsed == [
        ("NASDAQ", "NVDA"),
        ("NASDAQ", "MSFT"),
        ("EURONEXT", "ALDRV.PA"),
        ("", "ALDRV"),
        ("XETR", "RHM.DE"),
        ("KRAKEN", "BTC-USD"),
    ]


def test_import_tradingview_symbols_preserves_existing_metadata(db_session):
    db_session.add(
        WatchlistItemORM(
            ticker="NVDA",
            exchange="NASDAQ",
            company_name="NVIDIA",
            currency="USD",
            sector="Technology",
            country="United States",
        )
    )
    db_session.commit()

    service = WatchlistService(Path("missing.yml"))
    imported = service.import_tradingview_symbols(
        db_session,
        "NASDAQ:NVDA, NASDAQ:MSFT",
        default_currency="USD",
    )

    assert imported[0].company_name == "NVIDIA"
    assert db_session.query(WatchlistItemORM).filter_by(ticker="NVDA").one().sector == "Technology"
    assert db_session.query(WatchlistItemORM).filter_by(ticker="MSFT").one().exchange == "NASDAQ"


def test_list_entries_normalizes_existing_imported_tickers(db_session):
    db_session.add_all(
        [
            WatchlistItemORM(
                ticker="1RHM",
                exchange="MIL",
                company_name="1RHM",
                currency="",
                sector="",
                country="",
            ),
            WatchlistItemORM(
                ticker="BTCUSD",
                exchange="KRAKEN",
                company_name="BTCUSD",
                currency="",
                sector="",
                country="",
            ),
        ]
    )
    db_session.commit()

    entries = WatchlistService(Path("missing.yml")).list_entries(db_session)
    tickers = {entry.ticker for entry in entries}

    assert "1RHM" not in tickers
    assert "BTCUSD" not in tickers
    assert {"RHM.DE", "BTC-USD"}.issubset(tickers)
