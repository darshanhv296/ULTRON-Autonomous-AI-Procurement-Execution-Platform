"""
ULTRON Backend Configuration Module
Loads environment variables safely from .env without hardcoding secrets.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"

if ENV_FILE.exists():
    load_dotenv(dotenv_path=ENV_FILE, override=False)


def _is_real_credential(val: str) -> bool:
    if not val:
        return False
    cleaned = val.strip()
    placeholders = {
        "YOUR_KEY",
        "YOUR_MODEL",
        "YOUR_SANDBOX_CLIENT_ID",
        "YOUR_SANDBOX_SECRET",
        "YOUR_SANDBOX_CLIENT_SECRET",
        "YOUR_OPTIONAL_GROQ_KEY",
        "CHANGE_ME",
        "your_groq_api_key_here",
        "your_openrouter_api_key_here",
        "your_channel3_api_key_here",
        "MY_GEMINI_API_KEY",
    }
    return cleaned not in placeholders and not cleaned.startswith("YOUR_")


class Settings:
    """Centralized configuration for ULTRON."""

    def __init__(self) -> None:
        self.reload()

    def reload(self) -> None:
        if ENV_FILE.exists():
            load_dotenv(dotenv_path=ENV_FILE, override=True)

        self.APP_NAME: str = os.getenv("APP_NAME", "ULTRON")
        self.APP_ENV: str = os.getenv("APP_ENV", "development")
        self.APP_HOST: str = os.getenv("APP_HOST", "127.0.0.1")
        self.APP_PORT: int = int(os.getenv("APP_PORT", os.getenv("PORT", "8000")))
        self.APP_URL: str = os.getenv("APP_URL", f"http://{self.APP_HOST}:{self.APP_PORT}")

        # MySQL 8+ Configuration
        self.MYSQL_HOST: str = os.getenv("MYSQL_HOST", "localhost")
        self.MYSQL_PORT: int = int(os.getenv("MYSQL_PORT", "3306"))
        self.MYSQL_DATABASE: str = os.getenv("MYSQL_DATABASE", "ultron")
        self.MYSQL_USER: str = os.getenv("MYSQL_USER", "root")
        self.MYSQL_PASSWORD: str = os.getenv("MYSQL_PASSWORD", "")

        # AI Providers (OpenRouter & Groq)
        self.OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "").strip()
        self.OPENROUTER_MODEL: str = os.getenv(
            "OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct"
        ).strip()
        if not _is_real_credential(self.OPENROUTER_MODEL):
            self.OPENROUTER_MODEL = "meta-llama/llama-3.3-70b-instruct"

        self.GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "").strip()
        self.GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()

        # PayPal Developer Sandbox REST API
        self.PAYPAL_CLIENT_ID: str = os.getenv("PAYPAL_CLIENT_ID", "").strip()
        self.PAYPAL_CLIENT_SECRET: str = os.getenv("PAYPAL_CLIENT_SECRET", "").strip()
        self.PAYPAL_BASE_URL: str = os.getenv(
            "PAYPAL_BASE_URL", "https://api-m.sandbox.paypal.com"
        ).strip()
        self.PAYPAL_MERCHANT_EMAIL: str = os.getenv(
            "PAYPAL_MERCHANT_EMAIL", "demo@example.invalid"
        ).strip()
        self.PAYPAL_BUYER_EMAIL: str = os.getenv(
            "PAYPAL_BUYER_EMAIL", "demo@example.invalid"
        ).strip()

        # Channel3 Product Discovery Integration
        self.CHANNEL3_API_KEY: str = os.getenv("CHANNEL3_API_KEY", "").strip()
        self.CHANNEL3_API_URL: str = os.getenv(
            "CHANNEL3_API_URL", "https://api.channel3.io/v1"
        ).strip()

    @property
    def is_openrouter_configured(self) -> bool:
        return _is_real_credential(self.OPENROUTER_API_KEY)

    @property
    def is_groq_configured(self) -> bool:
        return _is_real_credential(self.GROQ_API_KEY)

    @property
    def is_paypal_configured(self) -> bool:
        return _is_real_credential(self.PAYPAL_CLIENT_ID) and _is_real_credential(
            self.PAYPAL_CLIENT_SECRET
        )

    @property
    def is_channel3_configured(self) -> bool:
        return _is_real_credential(self.CHANNEL3_API_KEY)

    @property
    def mysql_url(self) -> str:
        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
        )


settings = Settings()
