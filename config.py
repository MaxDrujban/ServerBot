from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    telegram_bot_token: str
    max_bot_token: str
    api_port: int = 8000
    max_webhook_url: str
    telegram_webhook_url: str | None = None
    telegram_webhook_secret: str | None = None
    telegram_proxy: str | None = None
    telegram_mode: str = "webhook"
    support_bridge_url: str = "http://127.0.0.1:8082"

    class Config:
        env_file = ".env"


settings = Settings()
