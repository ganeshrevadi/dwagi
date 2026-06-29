import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.db.session import init_db
from app.jobs.router import router as jobs_router
from app.routers import health, telegram
from app.telegram.client import TelegramClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    init_db()
    logger.info("Database initialized")

    if settings.telegram_bot_token and settings.public_base_url:
        try:
            client = TelegramClient()
            result = await client.set_webhook()
            logger.info("Telegram webhook set: %s", result)
        except Exception:
            logger.exception("Failed to set Telegram webhook")

    yield


app = FastAPI(title="Puppy Spending Bot", lifespan=lifespan)
app.include_router(health.router)
app.include_router(telegram.router)
app.include_router(jobs_router)


@app.get("/")
def root() -> dict:
    return {"service": "puppy", "status": "running"}
