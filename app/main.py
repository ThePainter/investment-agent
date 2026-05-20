from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.db.session import init_db
from app.logging_config import configure_logging
from app.scheduler.jobs import start_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    init_db()
    scheduler = start_scheduler()
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(
    title="Investment Agent",
    description="Decision-support stock signals with technical analysis, news monitoring, and portfolio tracking.",
    version="0.1.0",
    lifespan=lifespan,
)
app.include_router(router, prefix="/api")

