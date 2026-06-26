import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.jobs.models import Job, JobApplication
from app.jobs.schemas import JobResponse, PipelineSummary, ScanResult
from app.jobs.scanner import run_scan

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/")
def list_jobs(db: Session = Depends(get_db), limit: int = 50) -> list[JobResponse]:
    jobs = db.query(Job).order_by(Job.match_score.desc(), Job.found_at.desc()).limit(limit).all()
    return [JobResponse.model_validate(j) for j in jobs]


@router.post("/scan")
async def scan() -> dict:
    return await run_scan()


@router.get("/status")
def status(db: Session = Depends(get_db)) -> PipelineSummary:
    apps = db.query(JobApplication).all()
    counts: dict[str, int] = {"discovered": 0, "applied": 0, "rejected": 0, "interviewing": 0, "offer": 0}
    for app in apps:
        if app.status in counts:
            counts[app.status] += 1
    return PipelineSummary(
        discovered=counts["discovered"],
        applied=counts["applied"],
        rejected=counts["rejected"],
        interviewing=counts["interviewing"],
        offer=counts["offer"],
        total=len(apps),
    )
