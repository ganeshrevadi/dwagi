import logging
from datetime import date, datetime
from urllib.parse import urlencode

import httpx
from bs4 import BeautifulSoup

from app.jobs.scrapers.base import BaseScraper, ScrapedJob

logger = logging.getLogger(__name__)

LINKEDIN_SEARCH_URL = "https://www.linkedin.com/jobs/search"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


class LinkedInScraper(BaseScraper):
    source = "linkedin"

    def __init__(self, keywords: str = "software engineer", location: str = "India"):
        self.keywords = keywords
        self.location = location

    async def scrape(self) -> list[ScrapedJob]:
        jobs: list[ScrapedJob] = []
        params = {
            "keywords": self.keywords,
            "location": self.location,
            "f_TPR": "r86400",
            "position": 1,
            "pageNum": 0,
        }
        url = f"{LINKEDIN_SEARCH_URL}?{urlencode(params)}"

        try:
            async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
                resp = await client.get(url, headers=HEADERS)
                resp.raise_for_status()
        except Exception as e:
            logger.error("LinkedIn request failed: %s", e)
            return jobs

        soup = BeautifulSoup(resp.text, "lxml")

        seen: set[str] = set()
        for card in soup.select(".job-search-card, .base-card, [data-job-id]"):
            try:
                title_el = card.select_one(".base-search-card__title, h3, [data-anonymize='job-title']")
                company_el = card.select_one(".base-search-card__subtitle, .job-card-container__company-name, [data-anonymize='company-name']")
                link_el = card.select_one("a.base-card__full-link, a[data-job-id]")

                if not title_el or not company_el:
                    continue

                title = title_el.get_text(strip=True)
                company = company_el.get_text(strip=True)

                url = ""
                if link_el:
                    href = link_el.get("href", "")
                    url = href if href else ""

                if not url:
                    continue

                ext_id = f"li:{company}:{title}".lower().replace(" ", "-")[:200]
                if ext_id in seen:
                    continue
                seen.add(ext_id)

                location_el = card.select_one(".job-search-card__location, .job-card-container__metadata-wrapper")
                location = location_el.get_text(strip=True) if location_el else None

                remote = False
                if location and any(kw in location.lower() for kw in ["remote", "anywhere"]):
                    remote = True

                posted_el = card.select_one("time, .job-search-card__listdate")
                posted_at = date.today()
                if posted_el and posted_el.get("datetime"):
                    try:
                        posted_at = datetime.fromisoformat(posted_el["datetime"].replace("Z", "+00:00")).date()
                    except (ValueError, IndexError):
                        pass

                jobs.append(ScrapedJob(
                    title=title,
                    company_name=company,
                    url=url,
                    source=self.source,
                    external_id=ext_id,
                    location=location,
                    remote=remote,
                    posted_at=posted_at,
                ))
            except Exception:
                logger.debug("Failed to parse a LinkedIn card", exc_info=True)

        logger.info("LinkedIn: found %d jobs for '%s'", len(jobs), self.keywords)
        return jobs
