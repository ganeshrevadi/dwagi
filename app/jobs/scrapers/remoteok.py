import logging
from datetime import date, datetime

import httpx

from app.jobs.scrapers.base import BaseScraper, ScrapedJob

logger = logging.getLogger(__name__)

REMOTEOK_API = "https://remoteok.com/api"


class RemoteOKScraper(BaseScraper):
    source = "remoteok"

    def __init__(self, tags: str = "software,developer,backend,fullstack"):
        self.tags = tags

    async def scrape(self) -> list[ScrapedJob]:
        jobs: list[ScrapedJob] = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(REMOTEOK_API, headers=headers)
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            logger.error("RemoteOK request failed: %s", e)
            return jobs

        if not isinstance(data, list):
            return jobs

        seen: set[str] = set()
        for item in data[1:]:
            try:
                title = item.get("position", "")
                company = item.get("company", "")
                if not title or not company:
                    continue

                external_id = str(item.get("id", ""))
                if not external_id or external_id in seen:
                    continue
                seen.add(external_id)

                url = item.get("url", "")
                location = item.get("location", "Remote")

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
                salary_currency = item.get("currency", "USD")

                description = item.get("description", "")
                snippet = description[:500] if description else None

                jobs.append(ScrapedJob(
                    title=title,
                    company_name=company,
                    url=url,
                    source=self.source,
                    external_id=external_id,
                    location=location,
                    salary_min=salary_min,
                    salary_max=salary_max,
                    salary_currency=salary_currency,
                    description_snippet=snippet,
                    remote=True,
                    posted_at=date.today(),
                ))
            except Exception:
                logger.debug("Failed to parse a RemoteOK job", exc_info=True)

        logger.info("RemoteOK: found %d jobs", len(jobs))
        return jobs
