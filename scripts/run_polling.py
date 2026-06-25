#!/usr/bin/env python3
"""Run the bot locally via long polling (no public URL needed)."""

import asyncio
import logging
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings
from app.db.session import SessionLocal, init_db
from app.telegram.handler import handle_update
from app.telegram.client import TelegramClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def poll() -> None:
    settings = get_settings()
    if not settings.telegram_bot_token:
        raise SystemExit("TELEGRAM_BOT_TOKEN is not set in .env")

    init_db()
    client = TelegramClient()
    await client.delete_webhook()
    logger.info("Webhook deleted — starting long polling for @dawgi_bot")

    base = f"https://api.telegram.org/bot{settings.telegram_bot_token}"
    offset = 0

    async with httpx.AsyncClient(timeout=60.0) as http:
        while True:
            try:
                response = await http.get(
                    f"{base}/getUpdates",
                    params={"offset": offset, "timeout": 30},
                )
                response.raise_for_status()
                updates = response.json().get("result", [])
                for update in updates:
                    offset = update["update_id"] + 1
                    db = SessionLocal()
                    try:
                        await handle_update(db, update)
                    except Exception:
                        logger.exception("Error handling update %s", update.get("update_id"))
                    finally:
                        db.close()
            except httpx.ReadTimeout:
                continue
            except Exception:
                logger.exception("Polling error")
                await asyncio.sleep(3)


if __name__ == "__main__":
    asyncio.run(poll())
