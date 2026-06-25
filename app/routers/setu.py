import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.telegram.handler import handle_setu_notification

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/setu", tags=["setu"])


@router.post("/webhook")
async def setu_webhook(request: Request, db: Session = Depends(get_db)) -> dict:
    payload = await request.json()
    logger.info("Setu notification type=%s consentId=%s", payload.get("type"), payload.get("consentId"))
    try:
        await handle_setu_notification(db, payload)
    except Exception:
        logger.exception("Error handling Setu notification")
    return {"success": True}
