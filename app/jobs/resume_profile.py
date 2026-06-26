import json
import logging

from sqlalchemy.orm import Session

from app.jobs.config import get_job_settings
from app.jobs.models import ResumeProfile

logger = logging.getLogger(__name__)

FALLBACK_SKILLS = ["python", "javascript", "typescript", "react", "node.js", "sql", "git", "aws", "docker"]

FALLBACK_TITLES = [
    "software engineer", "sde", "sde 1", "sde 2", "sde i", "sde ii",
    "software developer engineer", "member of technical staff",
    "software engineer 1", "software engineer 2",
    "software engineer i", "software engineer ii",
    "frontend engineer", "front end engineer",
    "backend engineer", "backend developer",
    "full stack engineer", "full stack developer",
    "platform engineer", "infrastructure engineer",
]


def get_or_create_resume_profile(db: Session, telegram_user_id: int) -> ResumeProfile:
    profile = db.query(ResumeProfile).filter(ResumeProfile.user_id == telegram_user_id).first()
    if not profile:
        profile = ResumeProfile(user_id=telegram_user_id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


def get_effective_skills(db: Session, telegram_user_id: int) -> list[str]:
    settings = get_job_settings()
    env_skills = settings.skills_list
    if env_skills:
        return env_skills

    profile = get_or_create_resume_profile(db, telegram_user_id)
    resume_skills = profile.get_skills()
    if resume_skills:
        return resume_skills

    return FALLBACK_SKILLS


def get_effective_titles(db: Session, telegram_user_id: int) -> list[str]:
    settings = get_job_settings()
    env_titles = settings.target_titles_list
    if env_titles:
        return env_titles

    profile = get_or_create_resume_profile(db, telegram_user_id)
    resume_titles = profile.get_job_titles()
    if resume_titles:
        return [t.lower() for t in resume_titles]

    return FALLBACK_TITLES


def get_effective_experience(db: Session, telegram_user_id: int) -> float:
    settings = get_job_settings()
    if settings.profile_experience_years:
        return float(settings.profile_experience_years)

    profile = get_or_create_resume_profile(db, telegram_user_id)
    return profile.experience_years or 0.0


def get_effective_min_salary() -> int:
    settings = get_job_settings()
    return settings.profile_min_salary or 2500000


def _source_label(db: Session, telegram_user_id: int) -> str:
    settings = get_job_settings()
    if settings.skills_list or settings.target_titles_list:
        return "sourced from .env"
    profile = get_or_create_resume_profile(db, telegram_user_id)
    if profile.get_skills():
        return "sourced from your resume"
    return "using defaults (upload a resume or set .env to customize)"


def format_profile_text(db: Session, telegram_user_id: int) -> str:
    settings = get_job_settings()
    skills = ", ".join(get_effective_skills(db, telegram_user_id))
    titles = ", ".join(get_effective_titles(db, telegram_user_id))
    exp = get_effective_experience(db, telegram_user_id)
    salary = get_effective_min_salary()
    exp_str = f"{exp:.0f} years" if exp else "auto-detected from resume"
    salary_str = f"₹{salary/100000:.1f} LPA" if salary >= 100000 else f"${salary:,}"
    source = _source_label(db, telegram_user_id)

    lines = [
        "👤 Your Job Profile",
        f"   Skills: {skills}",
        f"   Target titles: {titles}",
        f"   Experience: {exp_str}",
        f"   Min salary: {salary_str}",
        f"   Companies: {settings.company_min_employees}+ employees",
        f"   Locations: Bangalore onsite | Remote India",
        f"\n📌 Profile {source}",
    ]
    return "\n".join(lines)
