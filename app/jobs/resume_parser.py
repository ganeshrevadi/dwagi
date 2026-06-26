import io
import logging
import re
from dataclasses import dataclass, field

import pdfplumber

logger = logging.getLogger(__name__)

SKILL_KEYWORDS = [
    "python", "typescript", "javascript", "java", "go", "golang", "rust",
    "c++", "c#", "swift", "kotlin", "scala", "ruby", "php", "perl",
    "react", "angular", "vue", "svelte", "next.js", "nuxt",
    "node.js", "deno", "express", "fastapi", "django", "flask",
    "spring", "spring boot", "asp.net", "rails", "laravel",
    "postgresql", "postgres", "mysql", "mongodb", "redis", "elasticsearch",
    "kafka", "rabbitmq", "nats",
    "aws", "azure", "gcp", "google cloud", "cloud",
    "docker", "kubernetes", "k8s", "terraform", "ansible", "jenkins",
    "ci/cd", "github actions", "gitlab ci", "circleci",
    "rest", "graphql", "grpc", "api", "microservices",
    "sql", "nosql", "dynamodb", "cassandra", "couchbase",
    "react native", "flutter", "android", "ios",
    "machine learning", "deep learning", "nlp", "llm", "genai",
    "tensorflow", "pytorch", "keras", "scikit-learn",
    "pandas", "numpy", "jupyter",
    "system design", "architecture", "distributed systems",
    "linux", "unix", "bash", "shell", "git", "github",
    "html", "css", "sass", "tailwind", "bootstrap",
    "redux", "mobx", "webpack", "vite",
    "jest", "mocha", "cypress", "playwright", "pytest",
    "oop", "functional programming", "design patterns",
    "agile", "scrum", "jira", "confluence",
    "datadog", "prometheus", "grafana", "sentry", "new relic",
    "sdlc", "tdd", "bdd",
    "blockchain", "web3", "solidity",
    "data engineering", "data pipeline", "etl", "airflow",
    "tableau", "power bi", "looker",
    "figma", "sketch", "adobe xd",
]

EXPERIENCE_PATTERNS = [
    re.compile(r"(\d+)\+?\s*years?\s*(?:of)?\s*(?:professional)?\s*(?:work)?\s*(?:experience)?", re.I),
    re.compile(r"(?:experience|exp)\s*(?:of|:)?\s*(\d+)\+?\s*years?", re.I),
    re.compile(r"(\d+)\+?\s*yr?s?\s*(?:of)?\s*(?:exp|experience)", re.I),
]

DATE_RANGE = re.compile(
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s*\d{4}\s*(?:-|–|to)\s*"
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s*\d{4}|"
    r"(?:19|20)\d{2}\s*(?:-|–|to)\s*(?:19|20)\d{2}|"
    r"(?:19|20)\d{2}\s*(?:-|–|to)\s*(?:present|current|now)",
    re.I,
)

TITLE_STOP_WORDS = {"at", "in", "the", "a", "an", "for", "of", "and", "with", "-"}


@dataclass
class ParsedResume:
    skills: list[str] = field(default_factory=list)
    experience_years: float = 0.0
    job_titles: list[str] = field(default_factory=list)
    email: str = ""
    phone: str = ""
    linkedin: str = ""
    raw_text: str = ""
    education: list[str] = field(default_factory=list)


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            parts = []
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    parts.append(text)
            return "\n".join(parts)
    except Exception as e:
        logger.error("Failed to parse PDF: %s", e)
        return ""


def _extract_skills(text: str) -> list[str]:
    text_lower = text.lower()
    found: list[str] = []
    seen = set()
    for skill in SKILL_KEYWORDS:
        if skill in text_lower and skill not in seen:
            found.append(skill)
            seen.add(skill)
    found.sort(key=lambda s: len(s), reverse=True)
    return found


def _extract_experience_years(text: str) -> float:
    for pattern in EXPERIENCE_PATTERNS:
        match = pattern.search(text)
        if match:
            try:
                return float(match.group(1))
            except (ValueError, IndexError):
                pass

    ranges = DATE_RANGE.findall(text)
    total_years = 0.0
    for r in ranges[:8]:
        years = re.findall(r"(?:19|20)\d{2}", r)
        if len(years) >= 2:
            start, end = int(years[0]), int(years[-1])
            if "present" in r.lower() or "current" in r.lower() or "now" in r.lower():
                from datetime import date
                end = date.today().year
            diff = end - start
            if 0 < diff < 40:
                total_years += diff

    return total_years if total_years > 0 else 0.0


def _extract_job_titles(text: str) -> list[str]:
    lines = text.split("\n")
    titles = []
    for line in lines:
        line = line.strip()
        if not line or len(line) > 80:
            continue
        lower = line.lower()
        has_separator = any(c in line for c in ["|", "-", "–", "·", "•"])
        if not has_separator:
            continue
        for keyword in ["engineer", "developer", "architect", "manager", "lead", "intern", "sde", "swe"]:
            if keyword in lower:
                title = line.split("|")[0].split("–")[0].split("-")[0].strip()
                title = re.sub(r"[·•]", "", title).strip()
                if title and len(title) > 5:
                    titles.append(title)
                break

    seen = set()
    unique = []
    for t in titles:
        lower = t.lower().strip()
        if lower not in seen:
            seen.add(lower)
            unique.append(t.strip())
    return unique[:10]


def _extract_contact(text: str) -> tuple[str, str, str]:
    email = ""
    phone = ""
    linkedin = ""

    email_match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
    if email_match:
        email = email_match.group(0)

    phone_match = re.search(r"(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", text)
    if phone_match:
        phone = phone_match.group(0)

    li_match = re.search(r"(?:linkedin\.com/in/|linkedin\.com/)[a-zA-Z0-9_-]+", text)
    if li_match:
        linkedin = li_match.group(0)

    return email, phone, linkedin


def _extract_education(text: str) -> list[str]:
    edu_lines = []
    edu_keywords = [
        "bachelor", "master", "phd", "b.tech", "m.tech", "b.e.", "m.e.",
        "b.sc", "m.sc", "bca", "mca", "b.b.a", "m.b.a", "mba",
        "bachelor of", "master of", "doctor of",
        "university", "college", "institute", "school of",
        "b.s.", "m.s.", "ph.d", "b.eng", "m.eng",
    ]
    for line in text.split("\n"):
        line = line.strip()
        if not line or len(line) > 120:
            continue
        lower = line.lower()
        if any(kw in lower for kw in edu_keywords):
            line_clean = re.sub(r"[•·●○◆◇■□]", "", line).strip()
            if line_clean:
                edu_lines.append(line_clean)
    return edu_lines[:5]


def parse_resume(pdf_bytes: bytes) -> ParsedResume:
    text = extract_text_from_pdf_bytes(pdf_bytes)
    if not text:
        return ParsedResume()

    return ParsedResume(
        skills=_extract_skills(text),
        experience_years=_extract_experience_years(text),
        job_titles=_extract_job_titles(text),
        email=_extract_contact(text)[0],
        phone=_extract_contact(text)[1],
        linkedin=_extract_contact(text)[2],
        raw_text=text[:2000],
        education=_extract_education(text),
    )


def resume_to_profile_text(resume: ParsedResume) -> str:
    lines = ["📄 Parsed Resume Profile"]
    lines.append(f"   Skills ({len(resume.skills)}): {', '.join(resume.skills[:20])}")
    if len(resume.skills) > 20:
        lines.append(f"     ... and {len(resume.skills) - 20} more")
    lines.append(f"   Experience: {resume.experience_years:.0f} years")
    if resume.job_titles:
        lines.append(f"   Titles: {', '.join(resume.job_titles[:5])}")
    if resume.education:
        lines.append(f"   Education: {', '.join(resume.education[:3])}")
    if resume.email:
        lines.append(f"   Email: {resume.email}")
    if resume.linkedin:
        lines.append(f"   LinkedIn: {resume.linkedin}")
    return "\n".join(lines)
