import logging
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org"


class TelegramClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.base = f"{TELEGRAM_API}/bot{self.settings.telegram_bot_token}"

    async def _post(self, method: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.settings.telegram_bot_token:
            logger.error("TELEGRAM_BOT_TOKEN not configured")
            return {"ok": False}
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{self.base}/{method}", json=payload)
            response.raise_for_status()
            data = response.json()
            if not data.get("ok"):
                logger.error("Telegram API error on %s: %s", method, data)
            return data

    async def send_message(self, chat_id: int, text: str, parse_mode: str | None = None) -> None:
        payload: dict[str, Any] = {"chat_id": chat_id, "text": text}
        if parse_mode:
            payload["parse_mode"] = parse_mode
        await self._post("sendMessage", payload)

    async def send_message_chunked(self, chat_id: int, text: str, chunk_size: int = 4000) -> None:
        if len(text) <= chunk_size:
            await self.send_message(chat_id, text)
            return
        for i in range(0, len(text), chunk_size):
            await self.send_message(chat_id, text[i : i + chunk_size])

    async def get_file_bytes(self, file_id: str) -> bytes:
        async with httpx.AsyncClient(timeout=60.0) as client:
            file_resp = await client.get(
                f"{self.base}/getFile",
                params={"file_id": file_id},
            )
            file_resp.raise_for_status()
            file_path = file_resp.json()["result"]["file_path"]
            download = await client.get(f"{TELEGRAM_API}/file/bot{self.settings.telegram_bot_token}/{file_path}")
            download.raise_for_status()
            return download.content

    async def set_webhook(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"url": self.settings.telegram_webhook_url}
        if self.settings.telegram_secret_token:
            payload["secret_token"] = self.settings.telegram_secret_token
        return await self._post("setWebhook", payload)

    async def delete_webhook(self) -> dict[str, Any]:
        return await self._post("deleteWebhook", {})
