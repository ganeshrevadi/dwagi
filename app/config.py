from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    telegram_bot_token: str = ""
    telegram_secret_token: str = ""
    allowed_telegram_user_ids: str = ""

    setu_env: Literal["sandbox", "production"] = "sandbox"
    setu_auth_url: str = "https://accountservice.setu.co/v1/users/login"
    setu_base_url: str = "https://fiu-sandbox.setu.co"
    setu_client_id: str = ""
    setu_client_secret: str = ""
    setu_product_instance_id: str = ""
    setu_redirect_url: str = "https://setu.co/"

    gemini_api_key: str = ""
    llm_model: str = "gemini-2.5-flash"

    public_base_url: str = "http://localhost:8000"
    database_url: str = "postgresql://user:pass@localhost:5432/puppy"
    port: int = 8000

    @property
    def allowed_user_ids(self) -> set[int]:
        if not self.allowed_telegram_user_ids.strip():
            return set()
        return {int(x.strip()) for x in self.allowed_telegram_user_ids.split(",") if x.strip()}

    @property
    def telegram_webhook_url(self) -> str:
        return f"{self.public_base_url.rstrip('/')}/telegram/webhook"

    @property
    def setu_configured(self) -> bool:
        return bool(self.setu_client_id and self.setu_client_secret and self.setu_product_instance_id)

    @property
    def gemini_configured(self) -> bool:
        return bool(self.gemini_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
