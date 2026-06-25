import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


class SetuClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._token: str | None = None
        self._token_expires_at: float = 0

    async def _get_token(self) -> str:
        if self._token and time.time() < self._token_expires_at - 30:
            return self._token

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.settings.setu_auth_url,
                headers={"client": "bridge", "Content-Type": "application/json"},
                json={
                    "clientID": self.settings.setu_client_id,
                    "secret": self.settings.setu_client_secret,
                    "grant_type": "client_credentials",
                },
            )
            response.raise_for_status()
            data = response.json()

        token = data.get("access_token") or data.get("accessToken") or data.get("token")
        if not token:
            raise RuntimeError("Setu auth response missing access token")

        self._token = token
        expires_in = data.get("expiresIn") or data.get("expires_in") or 300
        self._token_expires_at = time.time() + int(expires_in)
        return token

    def _headers(self, token: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "x-product-instance-id": self.settings.setu_product_instance_id,
        }

    async def create_consent(self, vua: str, data_months: int = 6) -> dict[str, Any]:
        token = await self._get_token()
        now = datetime.now(timezone.utc)
        data_from = now - timedelta(days=30 * data_months)

        payload = {
            "vua": vua,
            "consentMode": "VIEW",
            "fetchType": "PERIODIC",
            "consentTypes": ["TRANSACTIONS", "PROFILE", "SUMMARY"],
            "fiTypes": ["DEPOSIT"],
            "dataRange": {
                "from": data_from.strftime("%Y-%m-%dT00:00:00Z"),
                "to": now.strftime("%Y-%m-%dT23:59:59Z"),
            },
            "consentDuration": {"unit": "YEAR", "value": 1},
            "dataLife": {"unit": "MONTH", "value": 12},
            "frequency": {"unit": "MONTH", "value": 1},
            "purpose": {
                "code": "104",
                "text": "Personal finance management and spending analysis",
                "ref": "PFM_Spending_Bot",
            },
            "redirectUrl": self.settings.setu_redirect_url,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.settings.setu_base_url.rstrip('/')}/v2/consents",
                headers=self._headers(token),
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    async def create_data_session(self, consent_id: str, months: int = 6) -> dict[str, Any]:
        token = await self._get_token()
        now = datetime.now(timezone.utc)
        data_from = now - timedelta(days=30 * months)

        payload = {
            "consentId": consent_id,
            "format": "json",
            "dataRange": {
                "from": data_from.strftime("%Y-%m-%dT00:00:00Z"),
                "to": now.strftime("%Y-%m-%dT23:59:59Z"),
            },
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.settings.setu_base_url.rstrip('/')}/v2/sessions",
                headers=self._headers(token),
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    async def fetch_session_data(self, session_id: str) -> dict[str, Any]:
        token = await self._get_token()
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(
                f"{self.settings.setu_base_url.rstrip('/')}/v2/sessions/{session_id}",
                headers=self._headers(token),
            )
            response.raise_for_status()
            return response.json()
