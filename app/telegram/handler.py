import logging

from sqlalchemy.orm import Session

from app.banking.categorizer import categorize
from app.chat.agent import chat_with_agent
from app.db.models import Institution, Transaction, TransactionSource, User
from app.statements.bank_statement import parse_bank_statement
from app.statements.credit_card import parse_credit_statement
from app.statements.pdf_parser import ParsedTransaction
from app.jobs.telegram_commands import (
    handle_apply_command,
    handle_dismiss_callback,
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
/status — Transaction count
/upload — Import bank or credit card statement PDF

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

    if "callback_query" in update:
        await _handle_callback_query(db, client, update["callback_query"])
        return

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
            "Upload credit card or bank statement PDFs, "
            "then ask me anything about your spending.\n\n"
            "Type /help for commands.",
        )
    elif command == "/help":
        await client.send_message(chat_id, HELP_TEXT)
    elif command == "/status":
        await _send_status(db, client, user, chat_id)
    elif command == "/upload":
        await client.send_message(
            chat_id,
            "To import your statement:\n\n"
            "1. Download the e-statement PDF from your bank's net banking or email\n"
            "2. Send it to me here as a document (not a photo)\n"
            "3. I'll parse credit card and bank statement PDFs automatically\n\n"
            "Tip: include \"statement\" in the filename for better detection",
        )
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
    await client.send_message(
        chat_id,
        f"Transactions stored: {txn_count}\n\n"
        "Send a PDF statement to import more.",
    )


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
    is_statement = any(kw in file_name for kw in ("statement", "account", "bank", "sbi", "hdfc", "icici", "axis"))

    if not is_resume:
        parsed: list[ParsedTransaction] = []
        label = ""
        source_type = TransactionSource.PDF_BANK_STATEMENT
        institution = Institution.UNKNOWN

        if is_statement:
            await client.send_message(chat_id, "Parsing bank statement PDF...")
            parsed = parse_bank_statement(pdf_bytes)
            label = "bank statement"
        else:
            await client.send_message(chat_id, "Parsing PDF statement...")
            parsed = parse_credit_statement(pdf_bytes)
            if parsed:
                label = "credit card"
                source_type = TransactionSource.PDF_CREDIT_CARD
                institution = Institution.CREDIT_CARD
            else:
                parsed = parse_bank_statement(pdf_bytes)
                if parsed:
                    label = "bank statement"

        if parsed:
            inserted = _import_statement(db, user, parsed, source_type, institution)
            await client.send_message(chat_id,
                f"Imported {inserted} new transactions from {label} PDF "
                f"({len(parsed)} found, {len(parsed) - inserted} duplicates skipped).")
            return

    from app.jobs.telegram_commands import handle_upload_resume
    try:
        await handle_upload_resume(db, client, user, chat_id, pdf_bytes)
    except Exception:
        logger.exception("Resume upload failed")
        await client.send_message(chat_id, "Failed to parse resume PDF.")


def _import_statement(
    db: Session, user: User, parsed: list[ParsedTransaction],
    source: TransactionSource, institution: Institution,
) -> int:
    if not parsed:
        return 0
    prefix = "pdf:cc" if source == TransactionSource.PDF_CREDIT_CARD else "pdf:bnk"
    acct = "CC-PDF" if source == TransactionSource.PDF_CREDIT_CARD else "BANK-PDF"
    inserted = 0
    for txn in parsed:
        external_id = f"{prefix}:{txn.txn_date}:{txn.description[:40]}:{txn.amount}"
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
                source=source.value,
                institution=institution.value,
                account_masked=acct,
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
    return inserted


async def _handle_callback_query(db: Session, client: TelegramClient, cq: dict) -> None:
    data = cq.get("data", "")
    chat_id = cq["message"]["chat"]["id"]
    message_id = cq["message"]["message_id"]
    callback_id = cq["id"]

    if data.startswith("dismiss:"):
        try:
            job_id = int(data.split(":", 1)[1])
        except (ValueError, IndexError):
            await client.answer_callback_query(callback_id, "Invalid job")
            return
        await handle_dismiss_callback(db, client, chat_id, message_id, job_id)
        await client.answer_callback_query(callback_id, "Dismissed")
    else:
        await client.answer_callback_query(callback_id, "Unknown action")



