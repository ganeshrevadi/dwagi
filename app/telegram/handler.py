import logging
import re
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.banking.categorizer import categorize
from app.banking.sync import create_consent_for_user, ingest_fi_data, trigger_data_fetch
from app.chat.agent import chat_with_agent
from app.config import get_settings
from app.db.models import Consent, Institution, Transaction, TransactionSource, User
from app.statements.hsbc_credit import parse_hsbc_credit_statement
from app.jobs.telegram_commands import (
    handle_apply_command,
    handle_jobs_command,
    handle_pipeline_command,
    handle_profile_command,
    handle_referrals_command,
    handle_resume_command,
    handle_scan_command,
)
from app.telegram.client import TelegramClient
from app.telegram.security import is_user_allowed

logger = logging.getLogger(__name__)

HELP_TEXT = """Puppy — Spending Bot

Commands:
/start — Welcome message
/help — This help
/status — Linked accounts & transaction count
/connect <phone> — Link bank accounts (HSBC, BOB, Canara, IDFC)
  Example: /connect 9876543210
/upload — How to import HSBC credit card PDF
/sync — Refresh bank transactions

Job Tracker:
/jobs — New matching jobs today
/jobs:all — All tracked jobs
/apply <id> — Mark a job as applied
/referrals — Jobs needing referrals
/pipeline — Application summary
/scan — Run job search now
/profile — Show your search profile
/resume — Show your parsed resume data
Send a PDF named "resume" → parse & update your profile

Ask spending questions in plain English:
• How much did I spend on food last month?
• Top merchants this week
"""


async def handle_update(db: Session, update: dict) -> None:
    client = TelegramClient()

    if "message" not in update:
        return

    message = update["message"]
    chat_id = message["chat"]["id"]
    from_user = message.get("from", {})
    user_id = from_user.get("id")
    if not user_id:
        return

    if not is_user_allowed(user_id):
        await client.send_message(chat_id, "This bot is private. Access denied.")
        return

    user = _get_or_create_user(db, user_id)

    if "document" in message:
        await _handle_document(db, client, user, chat_id, message["document"])
        return

    text = message.get("text", "").strip()
    if not text:
        return

    if text.startswith("/"):
        await _handle_command(db, client, user, chat_id, text)
        return

    await client.send_message(chat_id, "Thinking...")
    reply = await chat_with_agent(db, user.id, text)
    await client.send_message_chunked(chat_id, reply)


def _get_or_create_user(db: Session, telegram_user_id: int) -> User:
    user = db.query(User).filter(User.telegram_user_id == telegram_user_id).first()
    if not user:
        user = User(telegram_user_id=telegram_user_id)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


async def _handle_command(db: Session, client: TelegramClient, user: User, chat_id: int, text: str) -> None:
    parts = text.split(maxsplit=1)
    command = parts[0].lower().split("@")[0]
    arg = parts[1].strip() if len(parts) > 1 else ""

    if command == "/start":
        await client.send_message(
            chat_id,
            "Hi! I'm Puppy, your spending analysis bot.\n\n"
            "Link bank accounts with /connect, upload HSBC credit card PDFs, "
            "then ask me anything about your spending.\n\n"
            "Type /help for commands.",
        )
    elif command == "/help":
        await client.send_message(chat_id, HELP_TEXT)
    elif command == "/status":
        await _send_status(db, client, user, chat_id)
    elif command == "/connect":
        await _handle_connect(db, client, user, chat_id, arg)
    elif command == "/upload":
        await client.send_message(
            chat_id,
            "To import your HSBC credit card statement:\n\n"
            "1. Download the e-statement PDF from HSBC net banking or email\n"
            "2. Send it to me here as a document (not a photo)\n"
            "3. I'll parse transactions and include them in spending analysis",
        )
    elif command == "/sync":
        await _handle_sync(db, client, user, chat_id)
    elif command == "/jobs":
        await handle_jobs_command(db, client, user, chat_id, arg or "")
    elif command == "/jobs:all":
        await handle_jobs_command(db, client, user, chat_id, "all")
    elif command == "/apply":
        await handle_apply_command(db, client, user, chat_id, arg)
    elif command == "/referrals":
        await handle_referrals_command(db, client, user, chat_id)
    elif command == "/pipeline":
        await handle_pipeline_command(db, client, user, chat_id)
    elif command == "/scan":
        await handle_scan_command(db, client, user, chat_id)
    elif command == "/profile":
        await handle_profile_command(db, client, user, chat_id)
    elif command == "/resume":
        await handle_resume_command(db, client, user, chat_id)
    else:
        await client.send_message(chat_id, "Unknown command. Try /help")


async def _send_status(db: Session, client: TelegramClient, user: User, chat_id: int) -> None:
    txn_count = db.query(Transaction).filter(Transaction.user_id == user.id).count()
    consents = db.query(Consent).filter(Consent.user_id == user.id).order_by(Consent.id.desc()).limit(3).all()

    lines = [f"Transactions stored: {txn_count}"]
    if consents:
        lines.append("\nBank consents:")
        for c in consents:
            lines.append(f"• {c.status} — {c.setu_consent_id[:8]}...")
    else:
        lines.append("\nNo bank accounts linked yet. Use /connect <phone>")

    lines.append("\nCredit card: send HSBC PDF to import")
    await client.send_message(chat_id, "\n".join(lines))


async def _handle_connect(db: Session, client: TelegramClient, user: User, chat_id: int, phone: str) -> None:
    settings = get_settings()
    if not settings.setu_configured:
        await client.send_message(
            chat_id,
            "Setu Account Aggregator is not configured yet.\n"
            "Add SETU_CLIENT_ID, SETU_CLIENT_SECRET, SETU_PRODUCT_INSTANCE_ID to .env",
        )
        return

    phone = re.sub(r"\D", "", phone)
    if len(phone) != 10:
        await client.send_message(
            chat_id,
            "Please provide your 10-digit mobile number registered with your banks.\n"
            "Example: /connect 9876543210",
        )
        return

    try:
        await client.send_message(chat_id, "Creating bank consent link...")
        consent = await create_consent_for_user(db, user, phone)
        if consent.consent_url:
            await client.send_message(
                chat_id,
                f"Open this link to link your bank accounts (HSBC, BOB, Canara, IDFC):\n\n{consent.consent_url}\n\n"
                "After approving, I'll fetch your transactions automatically.",
            )
        else:
            await client.send_message(
                chat_id,
                f"Consent created (ID: {consent.setu_consent_id}). Check Setu dashboard for URL.",
            )
    except Exception as e:
        logger.exception("Failed to create consent")
        await client.send_message(chat_id, f"Failed to create consent: {e}")


async def _handle_sync(db: Session, client: TelegramClient, user: User, chat_id: int) -> None:
    consent = (
        db.query(Consent)
        .filter(Consent.user_id == user.id, Consent.status == "ACTIVE")
        .order_by(Consent.id.desc())
        .first()
    )
    if not consent:
        await client.send_message(chat_id, "No active bank consent. Use /connect first.")
        return
    try:
        await client.send_message(chat_id, "Syncing bank transactions...")
        await trigger_data_fetch(db, consent)
        count = db.query(Transaction).filter(Transaction.user_id == user.id).count()
        await client.send_message(chat_id, f"Sync complete. Total transactions: {count}")
    except Exception as e:
        logger.exception("Sync failed")
        await client.send_message(chat_id, f"Sync failed: {e}")


async def _handle_document(db: Session, client: TelegramClient, user: User, chat_id: int, document: dict) -> None:
    mime = document.get("mime_type", "")
    file_name = document.get("file_name", "").lower()
    if mime != "application/pdf" and not file_name.endswith(".pdf"):
        await client.send_message(chat_id, "Please send a PDF document.")
        return

    try:
        pdf_bytes = await client.get_file_bytes(document["file_id"])
    except Exception as e:
        logger.exception("Failed to download PDF")
        await client.send_message(chat_id, f"Failed to download file: {e}")
        return

    is_resume = "resume" in file_name or "cv" in file_name

    if not is_resume:
        try:
            await client.send_message(chat_id, "Parsing PDF statement...")
            parsed = parse_hsbc_credit_statement(pdf_bytes)
            if parsed:
                inserted = 0
                for txn in parsed:
                    external_id = f"pdf:hsbc_cc:{txn.txn_date}:{txn.description[:40]}:{txn.amount}"
                    existing = (
                        db.query(Transaction)
                        .filter(Transaction.user_id == user.id, Transaction.external_id == external_id)
                        .first()
                    )
                    if existing:
                        continue
                    db.add(
                        Transaction(
                            user_id=user.id,
                            source=TransactionSource.PDF_CREDIT_CARD.value,
                            institution=Institution.HSBC_CC.value,
                            account_masked="HSBC-CC",
                            txn_date=txn.txn_date,
                            amount=txn.amount,
                            txn_type=txn.txn_type,
                            description=txn.description,
                            category=categorize(txn.description),
                            external_id=external_id,
                        )
                    )
                    inserted += 1
                db.commit()
                await client.send_message(
                    chat_id,
                    f"Imported {inserted} new transactions from HSBC credit card PDF "
                    f"({len(parsed)} found, {len(parsed) - inserted} duplicates skipped).",
                )
                return
        except Exception:
            logger.exception("HSBC parse failed, trying resume...")

    from app.jobs.telegram_commands import handle_upload_resume
    try:
        await handle_upload_resume(db, client, user, chat_id, pdf_bytes)
    except Exception:
        logger.exception("Resume upload failed")
        await client.send_message(chat_id, "Failed to parse resume PDF.")


async def handle_setu_notification(db: Session, payload: dict) -> None:
    notif_type = payload.get("type")
    consent_id = payload.get("consentId")

    if not consent_id:
        return

    consent = db.query(Consent).filter(Consent.setu_consent_id == consent_id).first()
    if not consent:
        logger.warning("Unknown consent ID in Setu notification: %s", consent_id)
        return

    if notif_type == "CONSENT_STATUS_UPDATE":
        status = payload.get("data", {}).get("status") or payload.get("status")
        if status:
            consent.status = status
            consent.updated_at = datetime.now(timezone.utc)
            db.commit()
        if status == "ACTIVE":
            try:
                await trigger_data_fetch(db, consent)
            except Exception:
                logger.exception("Auto-fetch after consent activation failed")

    elif notif_type in ("SESSION_STATUS_UPDATE", "FI_DATA_READY"):
        user = db.query(User).filter(User.id == consent.user_id).first()
        if user:
            ingest_fi_data(db, user, payload.get("data") or payload)
            if notif_type == "FI_DATA_READY":
                ingest_fi_data(db, user, payload)
