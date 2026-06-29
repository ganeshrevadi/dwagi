import logging
import re

from app.jobs.company_db import is_company_qualified
from app.jobs.config import get_job_settings
from app.jobs.scrapers.base import ScrapedJob

logger = logging.getLogger(__name__)

INDIA_CITIES = [
    "bangalore", "bengaluru", "mumbai", "pune", "hyderabad",
    "chennai", "gurgaon", "gurugram", "noida", "delhi",
    "kolkata", "ahmedabad", "kochi", "coimbatore", "indore",
]

REMOTE_INDIA_KEYWORDS = [
    "india", "apac", "asia", "anywhere", "indian time zone",
    "ist", "gmt+5", "remote india", "india remote",
]

US_EUROPE_ONLY_KEYWORDS = [
    "united states", "us remote", "remote - us", "remote us",
    "remote - united states", "remote (u.s.)", "remote in the us",
    "remote - canada", "canada remote", "remote north america",
    "remote ireland", "remote uk", "remote london",
    "remote - uk", "remotely in the uk", "united kingdom",
    "remote germany", "remote france", "remote estonia",
    "remote poland", "poland remote", "remote spain",
    "remote netherlands", "remote europe",
    "remote - estonia", "remote - ireland",
    "remote zone", "bay area", "remote south carolina",
    "remote-friendly us", "us remotely",
    "united states - remote", "seattle metro",
    "brazil", "remote - brazil", "brazil remote",
]

SENIORITY_PREFIXES = [
    "senior", "sr.", "sr ", "staff", "lead", "principal",
    "junior", "jr.", "jr ", "associate", "graduate",
    "entry", "fresher", "distinguished", "chief",
]

ROLE_LEVEL_WORDS = {
    "i": 0, "ii": 1, "iii": 2, "iv": 3,
    "1": 0, "2": 1, "3": 2, "4": 3,
}

EXECUTIVE_WORDS = {
    "manager": 4, "director": 7, "vp": 9, "vice president": 9,
    "head of": 7, "architect": 6, "fellow": 9, "chief": 10,
}

SENIORITY_PREFIX_PATTERN = re.compile(
    r"^(" + "|".join(re.escape(w.rstrip()) for w in SENIORITY_PREFIXES) + r")\s+",
    re.I,
)


def _get_title_level_info(title: str) -> tuple[str, int]:
    lower = title.lower().strip()
    min_years = 0

    for prefix in SENIORITY_PREFIXES:
        stripped = prefix.rstrip()
        if lower.startswith(stripped) or re.search(r"\b" + re.escape(stripped) + r"\b", lower):
            if prefix in ("junior", "jr.", "jr ", "associate", "graduate", "entry", "fresher"):
                min_years = max(min_years, 0)
            elif prefix in ("staff", "lead"):
                min_years = max(min_years, 5)
            else:
                min_years = max(min_years, 4)

    for word, years in EXECUTIVE_WORDS.items():
        if re.search(r"\b" + re.escape(word) + r"\b", lower):
            min_years = max(min_years, years)

    for level_word, years in ROLE_LEVEL_WORDS.items():
        if re.search(r"\b" + re.escape(level_word) + r"\b", lower) and years > 0:
            min_years = max(min_years, years)

    if min_years >= 8:
        return "executive", min_years
    if min_years >= 5:
        return "senior", min_years
    if min_years >= 2:
        return "mid", min_years
    return "junior", 0


def _strip_seniority(title: str) -> str:
    parts = title.split()
    filtered = []
    for word in parts:
        cleaned = word.strip("-,–—|·•()/\\&#")
        if not cleaned:
            continue
        lower = cleaned.lower()
        is_prefix = any(
            lower == p.rstrip().lower() or lower.startswith(p.rstrip().lower())
            for p in SENIORITY_PREFIXES
        )
        is_level = lower in ROLE_LEVEL_WORDS
        is_exec = lower in EXECUTIVE_WORDS
        if is_prefix or is_level or is_exec:
            continue
        filtered.append(word)
    result = " ".join(filtered).strip().strip("-–—|,·•()").strip()
    return result if result else title


def _title_matches_target(title: str, target_titles: list[str]) -> bool:
    base = _strip_seniority(title)
    base_lower = base.lower()

    for target in target_titles:
        if target in base_lower:
            return True

    return False


def _is_location_acceptable(job: ScrapedJob) -> bool:
    loc = (job.location or "").lower()

    if job.remote:
        if any(k in loc for k in REMOTE_INDIA_KEYWORDS):
            return True
        if any(k in loc for k in US_EUROPE_ONLY_KEYWORDS):
            return False
        if not loc or loc.strip() == "remote":
            return True
        return True

    for city in INDIA_CITIES:
        if city in loc:
            return True
    if "india" in loc:
        return True

    return False


def _score_location(job: ScrapedJob) -> float:
    loc = (job.location or "").lower()

    if job.remote:
        if any(k in loc for k in REMOTE_INDIA_KEYWORDS):
            return 15.0
        if not loc or loc.strip() == "remote":
            return 10.0
        return 6.0

    for city in INDIA_CITIES:
        if city in loc:
            if city in ("bangalore", "bengaluru"):
                return 15.0
            return 10.0

    if "india" in loc:
        return 12.0

    return 0.0


def score_job(
    job: ScrapedJob,
    settings: get_job_settings(),
    custom_titles: list[str] | None = None,
    custom_skills: list[str] | None = None,
    experience_years: float = 0.0,
) -> tuple[float, bool]:
    score = 0.0
    requires_referral = False

    if not _is_location_acceptable(job):
        return -50.0, False

    target_titles = custom_titles or settings.target_titles_list
    target_skills = custom_skills or settings.skills_list
    title_lower = job.title.lower()

    level, needed_years = _get_title_level_info(job.title)
    if needed_years > 0 and experience_years < needed_years:
        return -50.0, False

    has_title_match = _title_matches_target(job.title, target_titles)
    if not has_title_match:
        return -50.0, False

    score += 25

    snippet_lower = (job.description_snippet or "").lower()
    title_desc = f"{title_lower} {snippet_lower}"

    matched_skills = [s for s in target_skills if s.lower() in title_desc]
    skill_count = len(matched_skills)
    if skill_count > 0:
        score += min(skill_count * 10, 50)

    score += _score_location(job)

    salary_inr = job.salary_currency is None or job.salary_currency.upper() in ("", "INR", "IN")
    if salary_inr:
        if job.salary_min and job.salary_min >= settings.profile_min_salary:
            score += 10
        elif job.salary_max and job.salary_max >= settings.profile_min_salary:
            score += 5

    company_qualified = is_company_qualified(job.company_name)
    if company_qualified is True:
        score += 10
        requires_referral = True
    elif company_qualified is None:
        score += 3

    if job.source in ("greenhouse", "lever"):
        score += 5
    elif job.source == "linkedin":
        score += 2

    return score, requires_referral


def match_jobs(
    jobs: list[ScrapedJob],
    min_score: float = 30.0,
    custom_titles: list[str] | None = None,
    custom_skills: list[str] | None = None,
    experience_years: float = 0.0,
) -> list[tuple[ScrapedJob, float, bool]]:
    settings = get_job_settings()
    results: list[tuple[ScrapedJob, float, bool]] = []

    for job in jobs:
        score, needs_referral = score_job(
            job, settings, custom_titles, custom_skills, experience_years,
        )
        if score >= min_score:
            results.append((job, score, needs_referral))

    results.sort(key=lambda x: x[1], reverse=True)
    logger.info("Matcher: %d/%d jobs passed (min_score=%.1f)", len(results), len(jobs), min_score)
    return results
