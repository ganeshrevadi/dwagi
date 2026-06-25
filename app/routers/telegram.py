import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.telegram.handler import handle_update
from app.telegram.security import is_user_allowed, verify_telegram_secret

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telegram", tags=["telegram"])


@router.post("/webhook")
async def telegram_webhook(request: Request, db: Session = Depends(get_db)) -> dict:
    verify_telegram_secret(request)
    update = await request.json()

    user_id = update.get("message", {}).get("from", {}).get("id")
    if user_id and not is_user_allowed(user_id):
        logger.warning("Rejected update from unauthorized user %s", user_id)
        return {"ok": True}

    try:
        await handle_update(db, update)
    except Exception:
        logger.exception("Error handling Telegram update")

    return {"ok": True}
