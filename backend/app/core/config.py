import os

from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = os.getenv("APP_NAME", "Factory Shift")
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://factory_shift:factory_shift@localhost:5432/factory_shift_db",
    )
    sqlalchemy_echo: bool = os.getenv("SQLALCHEMY_ECHO", "false").lower() == "true"
    auto_create_tables: bool = os.getenv("AUTO_CREATE_TABLES", "false").lower() == "true"
    bot_webhook_secret: str = os.getenv("BOT_WEBHOOK_SECRET", "local-dev-secret")
    default_bot_platform: str = os.getenv("DEFAULT_BOT_PLATFORM", "bale")
    bale_bot_token: str = os.getenv("BALE_BOT_TOKEN", "")
    bale_api_base_url: str = os.getenv("BALE_API_BASE_URL", "https://tapi.bale.ai")
    bale_webhook_url: str = os.getenv("BALE_WEBHOOK_URL", "")
    bale_send_url: str = os.getenv("BALE_SEND_URL", "")
    rubika_send_url: str = os.getenv("RUBIKA_SEND_URL", "")


settings = Settings()
