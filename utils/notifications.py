
from __future__ import annotations
from typing import Optional, Dict, Any
import asyncio
import json

try:
    import aiohttp
except Exception:
    aiohttp = None

from utils.logger import get_logger
logger = get_logger(__name__)

class TelegramNotifier:
    def __init__(self, bot_token: Optional[str], chat_id: Optional[str]):
        self.bot_token = bot_token
        self.chat_id = chat_id

    async def send(self, text: str) -> bool:
        if not self.bot_token or not self.chat_id or aiohttp is None:
            logger.info("Telegram disabled or aiohttp missing; message skipped.")
            return False
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        try:
            async with aiohttp.ClientSession() as s:
                async with s.post(url, json={"chat_id": self.chat_id, "text": text}) as resp:
                    ok = resp.status == 200
                    if not ok:
                        logger.info(f"Telegram send failed: {resp.status}")
                    return ok
        except Exception as e:
            logger.info(f"Telegram error: {e}")
            return False

def get_notifier_from_config(config_manager=None) -> TelegramNotifier:
    bot_token = chat_id = None
    try:
        if config_manager and hasattr(config_manager, "get_setting"):
            bot_token = config_manager.get_setting("notifications", "telegram_bot_token", None)
            chat_id = config_manager.get_setting("notifications", "telegram_chat_id", None)
    except Exception:
        pass
    return TelegramNotifier(bot_token, chat_id)
