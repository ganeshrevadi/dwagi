import logging
from datetime import date

import httpx

from app.jobs.scrapers.base import BaseScraper, ScrapedJob

logger = logging.getLogger(__name__)

ASHBY_API = "https://api.ashbyhq.com/posting-api/job-board/{company}"


class AshbyScraper(BaseScraper):
    source = "ashby"

    def __init__(self, company: str):
        self.company = company

    async def scrape(self) -> list[ScrapedJob]:
        jobs: list[ScrapedJob] = []
        url = ASHBY_API.format(company=self.company.lower())

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            logger.error("Ashby request failed for %s: %s", self.company, e)
            return jobs

        for item in data.get("jobs", []):
            try:
                title = item.get("title", "")
                if not title:
                    continue

                external_id = item.get("id", "")
                if not external_id:
                    continue

                url = item.get("jobUrl", "") or item.get("hostedUrl", "")
                location = None
                remote = False
                location_obj = item.get("address")
                if location_obj:
                    location = location_obj.get("locality", "")
                    country = location_obj.get("country", "")
                    if country:
                        location = f"{location}, {country}" if location else country
                else:
                    for loc_field in ("location", "city", "remote", "office"):
                        val = item.get(loc_field)
                        if val and isinstance(val, str):
                            location = val
                            break

                if location and "remote" in location.lower():
                    remote = True

                salary_min = salary_max = None
                salary_currency = None
                salary_obj = item.get("compensation")
                if salary_obj:
                    if salary_obj.get("min"):
                        try:
                            salary_min = float(salary_obj["min"])
                        except (ValueError, TypeError):
                            pass
                    if salary_obj.get("max"):
                        try:
                            salary_max = float(salary_obj["max"])
                        except (ValueError, TypeError):
                            pass
                    salary_currency = salary_obj.get("currency")

                    remote_field = item.get("isRemote") or item.get("remote")
                    if remote_field is True:
                        remote = True

                description = item.get("descriptionHtml", "") or item.get("descriptionPlain", "")
                snippet = description[:500] if description else None

                posted_at = date.today()
                if item.get("publishedAt"):
                    try:
                        posted_at = date.fromisoformat(item["publishedAt"].split("T")[0])
                    except (ValueError, IndexError):
                        pass

                if not location and remote:
                    location = "Remote"

                jobs.append(ScrapedJob(
                    title=title,
                    company_name=self.company,
                    url=url,
                    source=self.source,
                    external_id=external_id,
                    location=location,
                    salary_min=salary_min,
                    salary_max=salary_max,
                    salary_currency=salary_currency,
                    description_snippet=snippet,
                    remote=remote,
                    posted_at=posted_at,
                ))
            except Exception:
                logger.debug("Failed to parse an Ashby job for %s", self.company, exc_info=True)

        logger.info("Ashby [%s]: found %d jobs", self.company, len(jobs))
        return jobs
