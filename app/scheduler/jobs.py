import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import get_settings
from app.db.session import SessionLocal
from app.services.analysis import AnalysisService

logger = logging.getLogger(__name__)


def refresh_job() -> None:
    db = SessionLocal()
    try:
        AnalysisService().analyze_watchlist(db)
        logger.info("Scheduled watchlist refresh completed")
    except Exception:
        logger.exception("Scheduled watchlist refresh failed")
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler:
    settings = get_settings()
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(
        refresh_job,
        "interval",
        minutes=settings.refresh_intraday_minutes,
        id="intraday_refresh",
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        refresh_job,
        "cron",
        hour=settings.refresh_daily_hour,
        id="daily_refresh",
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    return scheduler

