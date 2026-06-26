import logging
from datetime import date

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.jobs.company_db import get_company_list
from app.jobs.config import get_job_settings
from app.jobs.models import Company, Job, JobApplication
from app.jobs.company_db import COMPANIES
from app.jobs.scrapers.adzuna import AdzunaScraper
from app.jobs.scrapers.ashby import AshbyScraper
from app.jobs.scrapers.base import ScrapedJob
from app.jobs.scrapers.google_jobs import GoogleJobsScraper
from app.jobs.scrapers.greenhouse import GreenhouseScraper
from app.jobs.scrapers.lever import LeverScraper
from app.jobs.scrapers.linkedin import LinkedInScraper
from app.jobs.scrapers.remoteok import RemoteOKScraper

logger = logging.getLogger(__name__)

BOARD_TYPE_MAP: dict[str, list[str]] = {}
for c in COMPANIES:
    bt = c.get("board_type", "")
    name = c["name"]
    if bt == "greenhouse":
        BOARD_TYPE_MAP.setdefault("greenhouse", []).append(name)
    elif bt == "lever":
        BOARD_TYPE_MAP.setdefault("lever", []).append(name)
    elif bt == "ashby":
        BOARD_TYPE_MAP.setdefault("ashby", []).append(name)


def _ensure_company(db: Session, name: str) -> int | None:
    from app.jobs.company_db import lookup_company

    existing = db.query(Company).filter(Company.name.ilike(name)).first()
    if existing:
        return existing.id

    info = lookup_company(name)
    if info:
        company = Company(
            name=info["name"],
            domain=info.get("domain"),
            employee_count=info.get("employees"),
            board_type=info.get("board_type"),
        )
        db.add(company)
        db.flush()
        return company.id
    return None


def _insert_job(db: Session, scraped: ScrapedJob, score: float, needs_referral: bool) -> Job | None:
    existing = (
        db.query(Job)
        .filter(Job.source == scraped.source, Job.external_id == scraped.external_id)
        .first()
    )
    if existing:
        existing.match_score = max(existing.match_score or 0, score)
        existing.requires_referral = existing.requires_referral or needs_referral
        return None

    company_id = _ensure_company(db, scraped.company_name)

    job = Job(
        company_id=company_id,
        title=scraped.title,
        company_name=scraped.company_name,
        location=scraped.location,
        salary_min=scraped.salary_min,
        salary_max=scraped.salary_max,
        salary_currency=scraped.salary_currency,
        description_snippet=scraped.description_snippet,
        url=scraped.url,
        source=scraped.source,
        external_id=scraped.external_id,
        remote=scraped.remote,
        posted_at=scraped.posted_at or date.today(),
        match_score=score,
        requires_referral=needs_referral,
    )
    db.add(job)
    db.flush()

    app = JobApplication(job_id=job.id, status="discovered")
    db.add(app)
    return job


FALLBACK_TITLES = [
    "software engineer", "software developer",
    "backend engineer", "backend developer",
    "full stack engineer", "full stack developer",
    "platform engineer", "sde",
    "frontend engineer", "front end engineer",
]

FALLBACK_SKILLS = ["python", "typescript", "javascript", "react", "node.js", "sql", "aws", "docker", "git"]


async def run_scan(
    custom_titles: list[str] | None = None,
    custom_skills: list[str] | None = None,
    experience_years: float = 0.0,
) -> dict:
    settings = get_job_settings()
    all_scraped: list[ScrapedJob] = []
    scrapers: list = []

    titles = custom_titles or settings.target_titles_list or FALLBACK_TITLES

    if settings.google_jobs_enabled:
        scrapers.append(GoogleJobsScraper(query="software engineer"))

    if settings.greenhouse_enabled:
        for company in BOARD_TYPE_MAP.get("greenhouse", []):
            scrapers.append(GreenhouseScraper(company=company))

    if settings.lever_enabled:
        for company in BOARD_TYPE_MAP.get("lever", []):
            scrapers.append(LeverScraper(company=company))

    if settings.ashby_enabled:
        for company in BOARD_TYPE_MAP.get("ashby", []):
            scrapers.append(AshbyScraper(company=company))

    if settings.remoteok_enabled:
        scrapers.append(RemoteOKScraper())

    if settings.adzuna_enabled and settings.adzuna_app_id and settings.adzuna_api_key:
        scrapers.append(AdzunaScraper(app_id=settings.adzuna_app_id, app_key=settings.adzuna_api_key, query="software engineer"))

    if settings.linkedin_enabled:
        scrapers.append(LinkedInScraper())

    import asyncio

    for scraper in scrapers:
        try:
            jobs = await scraper.scrape()
            all_scraped.extend(jobs)
        except Exception as e:
            logger.error("Scraper %s failed: %s", scraper.source, e)

    from app.jobs.matcher import match_jobs

    skills = custom_skills or settings.skills_list or FALLBACK_SKILLS

    matched = match_jobs(
        all_scraped,
        custom_titles=titles,
        custom_skills=skills,
        experience_years=experience_years,
    )

    db = SessionLocal()
    try:
        new_count = 0
        for scraped_job, score, needs_ref in matched:
            job = _insert_job(db, scraped_job, score, needs_ref)
            if job:
                new_count += 1
        db.commit()

        total_tracked = db.query(Job).count()
        referral_count = db.query(Job).filter(Job.requires_referral == True).count()

        result = {
            "new_jobs": new_count,
            "matched_jobs": len(matched),
            "referrals_needed": referral_count,
            "total_tracked": total_tracked,
        }
        logger.info("Scan complete: %s", result)
        return result
    except Exception:
        db.rollback()
        logger.exception("Scan failed during DB insert")
        raise
    finally:
        db.close()
