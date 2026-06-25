import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.banking.sync import trigger_data_fetch
from app.db.models import Consent
from app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["sync"])


@router.post("/sync")
async def sync_all_active_consents(db: Session = Depends(get_db)) -> dict:
    """Endpoint for external cron (cron-job.org) to refresh bank data."""
    consents = db.query(Consent).filter(Consent.status == "ACTIVE").all()
    synced = 0
    errors: list[str] = []
    for consent in consents:
        try:
            await trigger_data_fetch(db, consent)
            synced += 1
        except Exception as e:
            logger.exception("Sync failed for consent %s", consent.setu_consent_id)
            errors.append(str(e))
    return {"synced": synced, "total": len(consents), "errors": errors}
