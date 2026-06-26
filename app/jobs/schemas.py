from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class CompanyResponse(BaseModel):
    id: int
    name: str
    domain: str | None
    employee_count: int | None
    career_page_url: str | None
    active: bool


class JobResponse(BaseModel):
    id: int
    title: str
    company_name: str
    location: str | None
    salary_min: float | None
    salary_max: float | None
    salary_currency: str | None
    url: str
    source: str
    remote: bool
    posted_at: date | None
    found_at: datetime
    match_score: float | None
    requires_referral: bool

    class Config:
        from_attributes = True


class ApplicationResponse(BaseModel):
    id: int
    job: JobResponse
    status: str
    applied_at: datetime | None
    notes: str | None
    created_at: datetime


class ScanResult(BaseModel):
    new_jobs: int
    matched_jobs: int
    referrals_needed: int
    total_tracked: int
    jobs: list[JobResponse]


class PipelineSummary(BaseModel):
    discovered: int
    applied: int
    rejected: int
    interviewing: int
    offer: int
    total: int
