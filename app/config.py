import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _admin_ids() -> frozenset[int]:
    return _telegram_ids("ADMIN_IDS")


def _telegram_ids(key: str) -> frozenset[int]:
    ids=set()
    for value in os.getenv(key, "").split(","):
        try:
            if value.strip(): ids.add(int(value.strip()))
        except ValueError:
            continue
    return frozenset(ids)


@dataclass(frozen=True)
class Settings:
    bot_token: str = os.getenv("BOT_TOKEN", "")
    admin_ids: frozenset[int] = _admin_ids()
    super_admin_ids: frozenset[int] = _telegram_ids("SUPER_ADMIN_IDS")
    database_path: str = os.getenv("DATABASE_PATH", "data/studio.sqlite3")
    telegram_stars_enabled: bool = os.getenv("TELEGRAM_STARS_ENABLED", "false").lower() == "true"
    payment_test_mode: bool = os.getenv("PAYMENT_TEST_MODE", "true").lower() == "true"
    default_timezone: str = os.getenv("DEFAULT_TIMEZONE", "UTC")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
    welcome_sticker_file_id: str = os.getenv("WELCOME_STICKER_FILE_ID", "")
    output_dir: str = os.getenv("OUTPUT_DIR", "data/generated")


settings = Settings()
