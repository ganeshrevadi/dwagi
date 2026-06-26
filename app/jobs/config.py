from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class JobSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    job_scan_enabled: bool = True
    job_scan_cron: str = "0 8,18 * * *"
    company_min_employees: int = 500

    google_jobs_enabled: bool = True
    greenhouse_enabled: bool = True
    lever_enabled: bool = True
    ashby_enabled: bool = True
    remoteok_enabled: bool = True
    linkedin_enabled: bool = True
    adzuna_enabled: bool = True
    adzuna_app_id: str = ""
    adzuna_api_key: str = ""

    profile_skills: str = ""
    profile_target_titles: str = ""
    profile_locations: str = ""
    profile_min_salary: int = 2500000
    profile_experience_years: int = 0
    profile_salary_currency: str = "INR"

    @property
    def skills_list(self) -> list[str]:
        return [s.strip() for s in self.profile_skills.split(",") if s.strip()]

    @property
    def target_titles_list(self) -> list[str]:
        return [t.strip().lower() for t in self.profile_target_titles.split(",") if t.strip()]

    @property
    def locations_list(self) -> list[str]:
        return [l.strip().lower() for l in self.profile_locations.split(",") if l.strip()]


@lru_cache
def get_job_settings() -> JobSettings:
    return JobSettings()
