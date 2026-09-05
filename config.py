from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    telegram_bot_token: str
    max_bot_token: str
    api_port: int = 8000
    max_webhook_url: str

    class Config:
        env_file = ".env"


settings = Settings()
