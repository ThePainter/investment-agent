from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.schemas import TradingViewImportRequest, WatchlistEntry
from app.config import get_settings
from app.services.analysis import AnalysisService
from app.services.storage.repository import AnalysisRepository
from app.services.watchlist import WatchlistService

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/watchlist")
def watchlist(db: Session = Depends(get_db)) -> list[dict]:
    return [entry.model_dump() for entry in AnalysisService().watchlist(db)]


@router.post("/watchlist")
def add_watchlist_item(entry: WatchlistEntry, db: Session = Depends(get_db)) -> dict:
    try:
        service = WatchlistService(get_settings().watchlist_config)
        return service.upsert(db, entry).model_dump()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/watchlist/{ticker}")
def delete_watchlist_item(ticker: str, db: Session = Depends(get_db)) -> dict:
    service = WatchlistService(get_settings().watchlist_config)
    if not service.remove(db, ticker):
        raise HTTPException(status_code=404, detail="Ticker not found in watchlist")
    return {"status": "deleted", "ticker": ticker.upper()}


@router.post("/watchlist/import/tradingview")
def import_tradingview_watchlist(
    request: TradingViewImportRequest, db: Session = Depends(get_db)
) -> list[dict]:
    service = WatchlistService(get_settings().watchlist_config)
    entries = service.import_tradingview_symbols(
        db,
        request.symbols,
        default_currency=request.default_currency,
        default_sector=request.default_sector,
        default_country=request.default_country,
    )
    return [entry.model_dump() for entry in entries]


@router.post("/refresh")
def refresh(db: Session = Depends(get_db)) -> list[dict]:
    return [item.model_dump(mode="json") for item in AnalysisService().analyze_watchlist(db)]


@router.get("/analysis")
def analysis(db: Session = Depends(get_db)) -> list[dict]:
    return refresh(db)


@router.get("/analysis/{ticker}")
def stock_detail(ticker: str, db: Session = Depends(get_db)) -> dict:
    try:
        return AnalysisService().stock_detail(db, ticker)
    except StopIteration as exc:
        raise HTTPException(status_code=404, detail="Ticker not found in watchlist") from exc


@router.get("/alerts")
def alerts(db: Session = Depends(get_db)) -> list[dict]:
    return [
        {
            "ticker": alert.ticker,
            "alert_type": alert.alert_type,
            "message": alert.message,
            "severity": alert.severity,
            "created_at": alert.created_at.isoformat(),
        }
        for alert in AnalysisRepository().latest_alerts(db)
    ]
