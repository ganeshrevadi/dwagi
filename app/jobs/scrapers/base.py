import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date

logger = logging.getLogger(__name__)


@dataclass
class ScrapedJob:
    title: str
    company_name: str
    url: str
    source: str
    external_id: str
    location: str | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    salary_currency: str | None = None
    description_snippet: str | None = None
    remote: bool = False
    posted_at: date | None = None


class BaseScraper(ABC):
    source: str = "base"

    @abstractmethod
    async def scrape(self) -> list[ScrapedJob]:
        ...

    def normalize_company(self, name: str) -> str:
        return name.strip().lower().replace("inc.", "").replace("llc", "").replace(",", "").strip()
