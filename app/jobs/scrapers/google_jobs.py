import logging
from datetime import date, datetime

import httpx
from bs4 import BeautifulSoup

from app.jobs.scrapers.base import BaseScraper, ScrapedJob

logger = logging.getLogger(__name__)

GOOGLE_JOBS_URL = "https://www.google.com/search"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


class GoogleJobsScraper(BaseScraper):
    source = "google_jobs"

    def __init__(self, query: str = "software engineer"):
        self.query = query

    async def scrape(self) -> list[ScrapedJob]:
        jobs: list[ScrapedJob] = []
        params = {
            "q": f"{self.query} jobs",
            "ibp": "htl;jobs",
            "uule": "w+CAIQICINVW5pdGVkIFN0YXRlcw",
        }

        try:
            async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
                resp = await client.get(GOOGLE_JOBS_URL, params=params, headers=HEADERS)
                resp.raise_for_status()
        except Exception as e:
            logger.error("Google Jobs request failed: %s", e)
            return jobs

        soup = BeautifulSoup(resp.text, "lxml")
        job_cards = soup.select("[data-chips], .job-card, [jsname]")

        seen: set[str] = set()
        for card in job_cards:
            try:
                title_el = card.select_one("h3, .job-title, [role='heading']")
                company_el = card.select_one(".company-name, .vNEEBe, [jsname='NjCds']")
                link_el = card.select_one("a[href]")

                if not title_el or not company_el:
                    continue

                title = title_el.get_text(strip=True)
                company = company_el.get_text(strip=True)
                url = ""
                if link_el and link_el.get("href"):
                    href = link_el["href"]
                    url = f"https://www.google.com{href}" if href.startswith("/") else href

                external_id = f"{company}:{title}".lower().replace(" ", "-")[:200]
                if external_id in seen:
                    continue
                seen.add(external_id)

                location_el = card.select_one(".location, .sOBnJb, [jsname='LgbsSe']")
                location = location_el.get_text(strip=True) if location_el else None

                remote = False
                if location and any(kw in location.lower() for kw in ["remote", "anywhere"]):
                    remote = True

                snippet_el = card.select_one(".description, .QsDR1c, .Yg3E9e")
                snippet = snippet_el.get_text(strip=True)[:500] if snippet_el else None

                jobs.append(ScrapedJob(
                    title=title,
                    company_name=company,
                    url=url,
                    source=self.source,
                    external_id=external_id,
                    location=location,
                    description_snippet=snippet,
                    remote=remote,
                    posted_at=date.today(),
                ))
            except Exception:
                logger.debug("Failed to parse a Google Jobs card", exc_info=True)

        logger.info("Google Jobs: found %d jobs for query '%s'", len(jobs), self.query)
        return jobs
