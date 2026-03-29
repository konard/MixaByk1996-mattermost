"""
Bot configuration
"""
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class BotConfig:
    """Bot configuration settings"""

    # Telegram
    telegram_token: str = os.getenv("TELEGRAM_TOKEN", "")

    # Core API
    core_api_url: str = os.getenv("CORE_API_URL", "http://localhost:8000/api")
    core_api_timeout: int = 30

    # Redis
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/1")

    # YooKassa
    yookassa_shop_id: str = os.getenv("YOOKASSA_SHOP_ID", "")
    yookassa_secret_key: str = os.getenv("YOOKASSA_SECRET_KEY", "")

    # Bot settings
    polling_interval: float = 0.5
    max_workers: int = 10
    http_port: int = int(os.getenv("BOT_HTTP_PORT", "8001"))

    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_file: Optional[str] = os.getenv("LOG_FILE")


config = BotConfig()
