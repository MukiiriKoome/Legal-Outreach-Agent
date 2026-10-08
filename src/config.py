import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Project directories
    BASE_DIR: Path = BASE_DIR
    DATA_DIR: Path = BASE_DIR / "data"
    DB_PATH: Path = BASE_DIR / "data" / "leads.db"

    # Gemini AI
    GEMINI_API_KEY: str = Field(default="")
    GEMINI_MODEL: str = Field(default="gemini-3.8-flash")

    # Startup & Pitch
    STARTUP_NAME: str = "Wakilify AI"
    FOUNDER_NAME: str = "Alex Mwangi"
    FOUNDER_EMAIL: str = "alex@wakilify.co.ke"
    STARTUP_TAGLINE: str = "Automating legal workflows and contract diligence for African legal teams"
    CALENDLY_URL: str = "https://calendly.com/alex-wakilify/investor-coffee-15m"
    MIN_TICKET_USD: int = 10000
    ROUND_TARGET_USD: int = 250000

    # Email delivery
    EMAIL_MODE: str = "mock"  # "mock" or "smtp"
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_NAME: str = "Alex Mwangi | Founder, Wakilify AI"

    # Safeguards
    MAX_EMAILS_PER_DAY: int = 30
    MIN_DELAY_SECONDS: int = 5
    MAX_DELAY_SECONDS: int = 15
    REQUIRE_HUMAN_APPROVAL: bool = True

    # Notifications
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""
    SLACK_WEBHOOK_URL: str = ""

    # Web Dashboard
    PORT: int = 8000
    HOST: str = "0.0.0.0"

settings = Settings()

# Ensure data directory exists
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
