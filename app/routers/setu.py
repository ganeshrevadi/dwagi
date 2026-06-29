import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/setu", tags=["setu"])


@router.post("/webhook")
async def setu_webhook(request: Request, db: Session = Depends(get_db)) -> dict:
    payload = await request.json()
    logger.info("Setu notification: %s", payload.get("type"))
    return {"success": True}
