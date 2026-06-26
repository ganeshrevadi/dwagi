import logging
from datetime import date

import httpx

from app.jobs.scrapers.base import BaseScraper, ScrapedJob

logger = logging.getLogger(__name__)

LEVER_API = "https://api.lever.co/v0/postings/{company}"


class LeverScraper(BaseScraper):
    source = "lever"

    def __init__(self, company: str):
        self.company = company

    async def scrape(self) -> list[ScrapedJob]:
        jobs: list[ScrapedJob] = []
        url = LEVER_API.format(company=self.company.lower())

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            logger.error("Lever request failed for %s: %s", self.company, e)
            return jobs

        if not isinstance(data, list):
            data = [data]

        for item in data:
            try:
                title = item.get("text", "")
                if not title:
                    continue

                external_id = item.get("id", "") or item.get("hostedUrl", "")
                if not external_id:
                    continue

                url = item.get("hostedUrl", "")
                location = None
                if item.get("categories"):
                    location = item["categories"].get("location")
                    if item["categories"].get("commitment"):
                        location = f"{location} - {item['categories']['commitment']}" if location else item["categories"]["commitment"]

                salary_min = salary_max = None
                if item.get("salaryRange"):
                    sr = item["salaryRange"]
                    if sr.get("min"):
                        try:
                            salary_min = float(sr["min"])
                        except (ValueError, TypeError):
                            pass
                    if sr.get("max"):
                        try:
                            salary_max = float(sr["max"])
                        except (ValueError, TypeError):
                            pass

                description = item.get("descriptionPlain", "") or item.get("description", "")
                snippet = description[:500] if description else None

                remote = location and "remote" in location.lower() if location else False

                jobs.append(ScrapedJob(
                    title=title,
                    company_name=self.company,
                    url=url,
                    source=self.source,
                    external_id=str(external_id),
                    location=location,
                    salary_min=salary_min,
                    salary_max=salary_max,
                    salary_currency="USD",
                    description_snippet=snippet,
                    remote=remote,
                    posted_at=date.today(),
                ))
            except Exception:
                logger.debug("Failed to parse a Lever job for %s", self.company, exc_info=True)

        logger.info("Lever [%s]: found %d jobs", self.company, len(jobs))
        return jobs
