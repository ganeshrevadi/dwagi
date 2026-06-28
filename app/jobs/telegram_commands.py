import logging
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import User
from app.jobs.models import Job, JobApplication, ResumeProfile
from app.jobs.resume_parser import parse_resume, resume_to_profile_text
from app.jobs.resume_profile import (
    format_profile_text,
    get_effective_experience,
    get_effective_skills,
    get_effective_titles,
    get_or_create_resume_profile,
)
from app.jobs.scanner import run_scan
from app.telegram.client import TelegramClient

logger = logging.getLogger(__name__)

JOBS_HELP = """Job Tracker Commands:
/jobs — New matching jobs today
/jobs:all — All tracked jobs
/apply <job_id> — Mark a job as applied
/referrals — Jobs where a referral would help
/pipeline — Application summary
/scan — Run job search now
/resume — Show your parsed resume profile
/upload_resume — Send your resume PDF to parse"""

# Track which job IDs are shown in which messages so dismiss buttons can edit the correct keyboard.
# _chat_message_jobs[chat_id][message_id] = [job_id, ...]
_chat_message_jobs: dict[int, dict[int, list[int]]] = {}

BATCH_SIZE = 5


def _esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


async def handle_jobs_command(db: Session, client: TelegramClient, user: User, chat_id: int, arg: str) -> None:
    if arg == "all":
        # For /jobs:all, exclude dismissed from the displayed list
        all_jobs = (
            db.query(Job)
            .order_by(Job.match_score.desc(), Job.found_at.desc())
            .limit(50)
            .all()
        )
        if not all_jobs:
            await client.send_message(chat_id, "No jobs tracked yet. Run /scan first.")
            return

        dismissed_ids = {
            ja.job_id for ja in db.query(JobApplication.job_id).filter(JobApplication.status == "dismissed").all()
        }
        jobs = [j for j in all_jobs if j.id not in dismissed_ids]
        if not jobs:
            await client.send_message(chat_id, "All tracked jobs have been dismissed. Run /scan to find new ones.")
            return

        lines = [f"📋 Tracked Jobs ({len(jobs)} shown, {len(all_jobs) - len(jobs)} dismissed)"]
        for j in jobs:
            app = db.query(JobApplication).filter(JobApplication.job_id == j.id).first()
            status = f" [{app.status}]" if app else ""
            lines.append(f"• #{j.id} <a href=\"{j.url}\">{_esc(j.title)} @ {j.company_name}</a>{status}")
        await client.send_message(chat_id, "\n".join(lines), parse_mode="HTML", disable_web_page_preview=True)
        return

    done_ids = {
        ja.job_id for ja in db.query(JobApplication.job_id).filter(
            JobApplication.status.in_(["dismissed", "applied", "interviewing", "offer"]),
        ).all()
    }
    new_jobs = (
        db.query(Job)
        .filter(Job.found_at >= date.today())
        .order_by(Job.match_score.desc())
        .all()
    )
    if not new_jobs:
        await client.send_message(chat_id, "No new jobs found today. Run /scan to check.")
        return

    matched = [j for j in new_jobs if j.match_score and j.match_score >= 30 and j.id not in done_ids]
    total = len(matched)
    if total == 0:
        await client.send_message(chat_id, "No jobs matching your profile today. Run /scan to check again.")
        return

    await _send_job_batches(client, db, chat_id, matched, total)


async def _send_job_batches(
    client: TelegramClient, db: Session, chat_id: int, jobs: list[Job], total: int,
) -> None:
    batches = [jobs[i:i + BATCH_SIZE] for i in range(0, len(jobs), BATCH_SIZE)]
    for batch in batches:
        lines: list[str] = []
        keyboard: list[list[dict[str, str]]] = []
        for j in batch:
            lines.append(f"• #{j.id} <a href=\"{j.url}\">{_esc(j.title)} @ {j.company_name}</a>")
            keyboard.append([{"text": "Dismiss", "callback_data": f"dismiss:{j.id}"}])
        if total > BATCH_SIZE:
            lines.append(f"\n{total} matching jobs — dismiss ones you've seen")
        else:
            lines.append("\nTap Dismiss to remove from this list")

        reply_markup = {"inline_keyboard": keyboard}
        result = await client.send_message(
            chat_id, "\n".join(lines),
            parse_mode="HTML", disable_web_page_preview=True,
            reply_markup=reply_markup,
        )
        if result and result.get("ok") and result.get("result", {}).get("message_id"):
            msg_id = result["result"]["message_id"]
            _chat_message_jobs.setdefault(chat_id, {})[msg_id] = [j.id for j in batch]


async def handle_dismiss_callback(
    db: Session, client: TelegramClient, chat_id: int, message_id: int, job_id: int,
) -> None:
    job = db.query(Job).filter(Job.id == job_id).first()
    if job:
        app = db.query(JobApplication).filter(JobApplication.job_id == job.id).first()
        if app and app.status == "discovered":
            app.status = "dismissed"
            db.commit()
        elif not app:
            app = JobApplication(job_id=job.id, status="dismissed")
            db.add(app)
            db.commit()

    # Rebuild keyboard: remove the dismissed button
    msg_jobs = _chat_message_jobs.get(chat_id, {}).get(message_id, [])
    remaining = [jid for jid in msg_jobs if jid != job_id]
    if remaining:
        _chat_message_jobs[chat_id][message_id] = remaining
        new_keyboard = [[{"text": "Dismiss", "callback_data": f"dismiss:{jid}"}] for jid in remaining]
        await client.edit_message_reply_markup(chat_id, message_id, {"inline_keyboard": new_keyboard})
    else:
        _chat_message_jobs[chat_id].pop(message_id, None)
        await client.edit_message_reply_markup(chat_id, message_id, None)


async def handle_apply_command(db: Session, client: TelegramClient, user: User, chat_id: int, arg: str) -> None:
    try:
        job_id = int(arg.strip())
    except (ValueError, IndexError):
        await client.send_message(chat_id, "Usage: /apply <job_id>")
        return

    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        await client.send_message(chat_id, f"Job #{job_id} not found.")
        return

    app = db.query(JobApplication).filter(JobApplication.job_id == job.id).first()
    if app and app.status != "discovered":
        await client.send_message(chat_id, f"Job #{job_id} already marked as '{app.status}'.")
        return

    if app:
        app.status = "applied"
        from datetime import datetime, timezone
        app.applied_at = datetime.now(timezone.utc)
    else:
        from datetime import datetime, timezone
        app = JobApplication(job_id=job.id, status="applied", applied_at=datetime.now(timezone.utc))
        db.add(app)
    db.commit()

    title = job.title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    await client.send_message(
        chat_id,
        f"✅ Marked as applied: <a href=\"{job.url}\">{title} @ {job.company_name}</a>",
        parse_mode="HTML", disable_web_page_preview=True,
    )


async def handle_referrals_command(db: Session, client: TelegramClient, user: User, chat_id: int) -> None:
    jobs = (
        db.query(Job)
        .filter(Job.requires_referral == True)
        .order_by(Job.match_score.desc())
        .limit(30)
        .all()
    )
    if not jobs:
        await client.send_message(chat_id, "No jobs needing referrals right now.")
        return

    lines = ["🎯 Jobs Where a Referral Helps\n"]
    for j in jobs[:15]:
        app = db.query(JobApplication).filter(JobApplication.job_id == j.id).first()
        status = f" [{app.status}]" if app else ""
        title = j.title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        lines.append(f"• #{j.id} <a href=\"{j.url}\">{title} @ {j.company_name}</a>{status}")
    if len(jobs) > 15:
        lines.append(f"\n... and {len(jobs) - 15} more")

    await client.send_message(chat_id, "\n".join(lines), parse_mode="HTML", disable_web_page_preview=True)


async def handle_pipeline_command(db: Session, client: TelegramClient, user: User, chat_id: int) -> None:
    apps = (
        db.query(JobApplication.status, JobApplication)
        .join(Job)
        .all()
    )
    counts: dict[str, int] = {"discovered": 0, "applied": 0, "rejected": 0, "interviewing": 0, "offer": 0, "dismissed": 0}
    for status, _ in apps:
        if status in counts:
            counts[status] += 1
    counts["total"] = len(apps)

    total = db.query(Job).count()

    lines = [
        f"📊 Application Pipeline",
        f"   Total jobs tracked: {total}",
        f"   🆕 Discovered: {counts['discovered']}",
        f"   ✅ Applied: {counts['applied']}",
        f"   🔄 Interviewing: {counts['interviewing']}",
        f"   ❌ Rejected: {counts['rejected']}",
        f"   🎉 Offers: {counts['offer']}",
        f"   ╳ Dismissed: {counts['dismissed']}",
    ]
    await client.send_message(chat_id, "\n".join(lines))


async def handle_scan_command(db: Session, client: TelegramClient, user: User, chat_id: int) -> None:
    await client.send_message(chat_id, "🔍 Running job scan... This may take a minute.")

    titles = get_effective_titles(db, user.telegram_user_id)
    skills = get_effective_skills(db, user.telegram_user_id)
    experience = get_effective_experience(db, user.telegram_user_id)

    try:
        result = await run_scan(custom_titles=titles, custom_skills=skills, experience_years=experience)
        await client.send_message(
            chat_id,
            f"✅ Scan complete!\n"
            f"   New jobs found: {result['new_jobs']}\n"
            f"   Matching profile: {result['matched_jobs']}\n"
            f"   Total tracked: {result['total_tracked']}\n\n"
            f"Use /jobs to see them.",
        )
    except Exception as e:
        logger.exception("Manual scan failed")
        await client.send_message(chat_id, f"Scan failed: {e}")


async def handle_profile_command(db: Session, client: TelegramClient, user: User, chat_id: int) -> None:
    text = format_profile_text(db, user.telegram_user_id)
    await client.send_message(chat_id, text)


async def handle_upload_resume(db: Session, client: TelegramClient, user: User, chat_id: int, pdf_bytes: bytes) -> None:
    await client.send_message(chat_id, "📄 Parsing your resume...")

    parsed = parse_resume(pdf_bytes)
    if not parsed.skills and not parsed.job_titles:
        await client.send_message(
            chat_id,
            "Couldn't extract skills or job titles from this PDF. "
            "Make sure it's a text-based PDF resume (not scanned/image).",
        )
        return

    profile = get_or_create_resume_profile(db, user.telegram_user_id)
    profile.set_skills(parsed.skills)
    profile.experience_years = parsed.experience_years
    profile.set_job_titles(parsed.job_titles)
    if parsed.education:
        profile.education_json = __import__("json").dumps(parsed.education)
    if parsed.email:
        profile.email = parsed.email
    if parsed.linkedin:
        profile.linkedin = parsed.linkedin
    db.commit()

    await client.send_message(chat_id, resume_to_profile_text(parsed))


async def handle_resume_command(db: Session, client: TelegramClient, user: User, chat_id: int) -> None:
    profile = db.query(ResumeProfile).filter(ResumeProfile.user_id == user.telegram_user_id).first()
    if not profile or not profile.get_skills():
        await client.send_message(
            chat_id,
            "No resume uploaded yet. Send your resume PDF or use /upload_resume with a file.",
        )
        return

    from app.jobs.resume_parser import ParsedResume
    fake = ParsedResume(
        skills=profile.get_skills(),
        experience_years=profile.experience_years or 0,
        job_titles=profile.get_job_titles(),
        email=profile.email or "",
        phone=profile.phone or "",
        linkedin=profile.linkedin or "",
        education=__import__("json").loads(profile.education_json) if profile.education_json else [],
    )
    await client.send_message(chat_id, resume_to_profile_text(fake))
