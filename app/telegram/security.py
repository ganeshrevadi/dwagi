import logging

from fastapi import HTTPException, Request

from app.config import get_settings

logger = logging.getLogger(__name__)


def verify_telegram_secret(request: Request) -> None:
    settings = get_settings()
    if not settings.telegram_secret_token:
        return
    token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if token != settings.telegram_secret_token:
        logger.warning("Rejected Telegram webhook: invalid secret token")
        raise HTTPException(status_code=403, detail="Invalid secret token")


def is_user_allowed(telegram_user_id: int) -> bool:
    allowed = get_settings().allowed_user_ids
    if not allowed:
        return True
    return telegram_user_id in allowed
