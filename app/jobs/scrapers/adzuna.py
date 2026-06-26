import logging
from datetime import date

import httpx

from app.jobs.scrapers.base import BaseScraper, ScrapedJob

logger = logging.getLogger(__name__)

ADZUNA_API = "https://api.adzuna.com/v1/api/jobs/in/search/1"


class AdzunaScraper(BaseScraper):
    source = "adzuna"

    def __init__(self, app_id: str, app_key: str, query: str = "software engineer"):
        self.app_id = app_id
        self.app_key = app_key
        self.query = query

    async def scrape(self) -> list[ScrapedJob]:
        jobs: list[ScrapedJob] = []
        if not self.app_id or not self.app_key:
            logger.warning("Adzuna API credentials not configured — skipping")
            return jobs

        params = {
            "app_id": self.app_id,
            "app_key": self.app_key,
            "what": self.query,
            "results_per_page": 50,
            "content_type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(ADZUNA_API, params=params)
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            logger.error("Adzuna request failed: %s", e)
            return jobs

        for item in data.get("results", []):
            try:
                title = item.get("title", "")
                if not title:
                    continue

                company = item.get("company", {}).get("display_name", "")
                if not company:
                    continue

                external_id = item.get("id", "")
                if not external_id:
                    continue

                url = item.get("redirect_url", "")
                location = item.get("location", {}).get("display_name", "")
                area = item.get("area", [])
                if not location and area:
                    location = ", ".join(a for a in area if a)

                salary_min = None
                salary_max = None
                if item.get("salary_min"):
                    try:
                        salary_min = float(item["salary_min"])
                    except (ValueError, TypeError):
                        pass
                if item.get("salary_max"):
                    try:
                        salary_max = float(item["salary_max"])
                    except (ValueError, TypeError):
                        pass
                salary_currency = item.get("salary_currency", "INR")

                description = item.get("description", "")
                snippet = description[:500] if description else None

                loc_lower = location.lower() if location else ""
                remote = any(kw in loc_lower for kw in ["remote", "work from home", "anywhere"])

                posted_at = date.today()
                if item.get("created"):
                    try:
                        posted_at = date.fromisoformat(item["created"].split("T")[0])
                    except (ValueError, IndexError):
                        pass

                jobs.append(ScrapedJob(
                    title=title,
                    company_name=company,
                    url=url,
                    source=self.source,
                    external_id=external_id,
                    location=location,
                    salary_min=salary_min,
                    salary_max=salary_max,
                    salary_currency=salary_currency or "INR",
                    description_snippet=snippet,
                    remote=remote,
                    posted_at=posted_at,
                ))
            except Exception:
                logger.debug("Failed to parse an Adzuna job", exc_info=True)

        logger.info("Adzuna [%s]: found %d jobs", self.query, len(jobs))
        return jobs
