from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    telegram_bot_token: str
    max_bot_token: str
    api_port: int = 8000
    max_webhook_url: str
    max_webhook_secret: str | None = None
    max_api_url: str = "https://platform-api2.max.ru"
    max_verify_ssl: bool = True
    max_ca_bundle: str | None = None
    telegram_webhook_url: str | None = None
    telegram_webhook_secret: str | None = None
    telegram_proxy: str | None = None
    telegram_mode: str = "webhook"
    support_bridge_url: str = "http://127.0.0.1:8082"
    ai_enabled: bool = False
    ai_api_key: str | None = None
    ai_base_url: str = "https://api.deepseek.com"
    ai_model: str = "deepseek-chat"
    ai_system_prompt: str = (
        "Ты — ассистент технической поддержки системы мониторинга SMB-ресурсов "
        "(сетевые папки, устройства, права доступа, статусы online/offline).\n"
        "\n"
        "Правила:\n"
        "1. Отвечай только на русском языке, коротко и по делу.\n"
        "2. Не выдумывай факты, адреса, имена устройств, сервисы и причины. "
        "Если данных не хватает — прямо скажи, чего не хватает, и предложи, что проверить.\n"
        "3. Используй только те данные, которые есть в вопросе или в предоставленном контексте.\n"
        "4. Для инструкций давай нумерованный список не длиннее пяти пунктов; "
        "каждый пункт — конкретное действие или конкретная причина.\n"
        "5. Если просят JSON — верни строго JSON, без markdown и без пояснений.\n"
        "6. Не упоминай облачные сервисы и продукты, которых нет в контексте.\n"
        "\n"
        "Примеры.\n"
        "\n"
        "Вопрос: Пользователь не видит сетевую папку \\\\server\\share. "
        "Что проверить в первую очередь?\n"
        "Ответ:\n"
        "1. Проверить, что сервер отвечает: пинг по имени и по IP.\n"
        "2. Проверить права пользователя на эту папку на стороне сервера.\n"
        "3. Проверить клиента: активное сетевое подключение, DNS-имя сервера, доступность порта 445.\n"
        "\n"
        "Вопрос: Устройство DEV-12, статус offline с 12:00. Когда устройство ушло offline?\n"
        "Ответ: Устройство DEV-12 ушло offline в 12:00.\n"
    )

    class Config:
        env_file = ".env"


settings = Settings()
