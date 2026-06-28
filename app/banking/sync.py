import logging
import re
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.banking.categorizer import categorize
from app.banking.setu_client import SetuClient
from app.config import get_settings
from app.db.models import Consent, Institution, Transaction, TransactionSource, User

logger = logging.getLogger(__name__)

FIP_TO_INSTITUTION = {
    "hsbc": Institution.BANK_AA.value,
    "hdfc": Institution.UNKNOWN.value,
    "baroda": Institution.BANK_AA2.value,
    "bob": Institution.BANK_AA2.value,
    "canara": Institution.BANK_AA3.value,
    "idfc": Institution.BANK_AA4.value,
}


def _map_fip_to_institution(fip_id: str) -> str:
    lower = fip_id.lower()
    for key, inst in FIP_TO_INSTITUTION.items():
        if key in lower:
            return inst
    return Institution.UNKNOWN.value


def _parse_txn_date(value: str) -> date:
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(value.replace("+00:00", "Z"), fmt.replace("%z", "Z"))
            return dt.date()
        except ValueError:
            continue
    return datetime.now(timezone.utc).date()


async def create_consent_for_user(db: Session, user: User, phone: str) -> Consent:
    settings = get_settings()
    if not settings.setu_configured:
        raise ValueError("Setu is not configured. Add SETU_CLIENT_ID, SETU_CLIENT_SECRET, SETU_PRODUCT_INSTANCE_ID.")

    vua = phone if "@" in phone else f"{phone}@onemoney"
    user.phone_vua = vua

    client = SetuClient()
    result = await client.create_consent(vua=vua)

    consent_id = result.get("id") or result.get("consentId")
    consent_url = result.get("url")
    if not consent_id:
        raise RuntimeError(f"Unexpected Setu consent response: {result}")

    consent = Consent(
        user_id=user.id,
        setu_consent_id=consent_id,
        status=result.get("status", "PENDING"),
        consent_url=consent_url,
    )
    db.add(consent)
    db.commit()
    db.refresh(consent)
    return consent


def ingest_fi_data(db: Session, user: User, fi_payload: dict) -> int:
    """Parse Setu FI data (auto-fetch or session fetch) into transactions. Returns count inserted."""
    inserted = 0
    fi_data = fi_payload.get("fiData") or []
    fips = fi_payload.get("fips") or []

    if fi_data:
        for fip_block in fi_data:
            fip_id = fip_block.get("fipID", "")
            institution = _map_fip_to_institution(fip_id)
            for account in fip_block.get("data", []):
                inserted += _ingest_account_data(db, user, account, institution, fip_id)
    elif fips:
        for fip_block in fips:
            fip_id = fip_block.get("fipID", "")
            institution = _map_fip_to_institution(fip_id)
            for account in fip_block.get("accounts", []):
                data = account.get("data") or account.get("decryptedFI")
                if data:
                    inserted += _ingest_account_data(db, user, {"decryptedFI": data, **account}, institution, fip_id)

    db.commit()
    return inserted


def _ingest_account_data(db: Session, user: User, account: dict, institution: str, fip_id: str) -> int:
    decrypted = account.get("decryptedFI") or account
    acct = decrypted.get("account") if isinstance(decrypted.get("account"), dict) else decrypted
    if not acct:
        return 0

    masked = acct.get("maskedAccNumber") or account.get("maskedAccNumber") or "XXXX"
    institution = institution if institution != Institution.UNKNOWN.value else _map_fip_to_institution(fip_id)

    transactions = acct.get("transactions", {})
    txn_list = transactions.get("transaction", [])
    if isinstance(txn_list, dict):
        txn_list = [txn_list]

    inserted = 0
    for txn in txn_list:
        txn_id = txn.get("txnId") or txn.get("reference") or f"{masked}-{txn.get('transactionTimestamp')}"
        external_id = f"aa:{institution}:{txn_id}"

        existing = (
            db.query(Transaction)
            .filter(Transaction.user_id == user.id, Transaction.external_id == external_id)
            .first()
        )
        if existing:
            continue

        narration = txn.get("narration") or txn.get("description") or ""
        amount = float(txn.get("amount", 0))
        txn_type = (txn.get("type") or "DEBIT").upper()
        txn_date = _parse_txn_date(
            txn.get("transactionTimestamp") or txn.get("valueDate") or datetime.now(timezone.utc).isoformat()
        )

        row = Transaction(
            user_id=user.id,
            source=TransactionSource.AA_DEPOSIT.value,
            institution=institution,
            account_masked=masked,
            txn_date=txn_date,
            amount=amount,
            txn_type=txn_type,
            description=narration,
            category=categorize(narration),
            external_id=external_id,
        )
        db.add(row)
        inserted += 1
    return inserted


async def trigger_data_fetch(db: Session, consent: Consent) -> str | None:
    client = SetuClient()
    session = await client.create_data_session(consent.setu_consent_id)
    session_id = session.get("id")
    if session_id:
        data = await client.fetch_session_data(session_id)
        user = db.query(User).filter(User.id == consent.user_id).first()
        if user:
            ingest_fi_data(db, user, data)
    return session_id
