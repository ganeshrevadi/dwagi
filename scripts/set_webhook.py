#!/usr/bin/env python3
"""Manually register Telegram webhook."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.telegram.client import TelegramClient


async def main() -> None:
    client = TelegramClient()
    result = await client.set_webhook()
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
