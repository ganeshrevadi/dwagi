import logging
from datetime import date

import httpx

from app.jobs.scrapers.base import BaseScraper, ScrapedJob

logger = logging.getLogger(__name__)

GREENHOUSE_API = "https://boards-api.greenhouse.io/v1/boards/{company}/jobs"


class GreenhouseScraper(BaseScraper):
    source = "greenhouse"

    def __init__(self, company: str, board_name: str | None = None):
        self.company = company
        self.board_name = board_name or company

    async def scrape(self) -> list[ScrapedJob]:
        jobs: list[ScrapedJob] = []
        url = GREENHOUSE_API.format(company=self.board_name)
        params = {"content": "true", "page": 1}

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            logger.error("Greenhouse request failed for %s: %s", self.company, e)
            return jobs

        for item in data.get("jobs", []):
            try:
                title = item.get("title", "")
                if not title:
                    continue

                external_id = str(item.get("id", ""))
                if not external_id:
                    continue

                absolute_url = item.get("absolute_url") or ""
                location_data = item.get("offices", [{}])[0] if item.get("offices") else {}
                location = location_data.get("name")

                metadata = item.get("metadata", [])
                salary_min = salary_max = None
                for m in metadata:
                    if "min" in m.get("name", "").lower():
                        try:
                            salary_min = float(m.get("value", 0))
                        except (ValueError, TypeError):
                            pass
                    if "max" in m.get("name", "").lower():
                        try:
                            salary_max = float(m.get("value", 0))
                        except (ValueError, TypeError):
                            pass

                description = item.get("content", "")
                snippet = description[:500] if description else None

                remote = location and "remote" in location.lower() if location else False

                posted_at = None
                if item.get("updated_at"):
                    try:
                        posted_dt = date.fromisoformat(item["updated_at"].split("T")[0])
                        posted_at = posted_dt
                    except (ValueError, IndexError):
                        pass

                jobs.append(ScrapedJob(
                    title=title,
                    company_name=self.company,
                    url=absolute_url,
                    source=self.source,
                    external_id=external_id,
                    location=location,
                    salary_min=salary_min,
                    salary_max=salary_max,
                    salary_currency="USD",
                    description_snippet=snippet,
                    remote=remote,
                    posted_at=posted_at or date.today(),
                ))
            except Exception:
                logger.debug("Failed to parse a Greenhouse job for %s", self.company, exc_info=True)

        logger.info("Greenhouse [%s]: found %d jobs", self.company, len(jobs))
        return jobs
