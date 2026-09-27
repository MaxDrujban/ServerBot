"""Единственные экземпляры сервисов приложения.

Их используют и обработчики событий Telegram и MAX, и REST-маршруты.
Создаются в одном месте, чтобы не появлялось по два независимых клиента
с раздельным состоянием.
"""

from config import settings
from services.ai_service import AiService
from services.max_service import MaxService
from services.support_service import SupportService
from services.telegram_service import TelegramService

ai_service = (
    AiService(
        api_key=settings.ai_api_key,
        base_url=settings.ai_base_url,
        model=settings.ai_model,
        system_prompt=settings.ai_system_prompt,
    )
    if settings.ai_enabled and settings.ai_api_key
    else None
)

support_service = SupportService(settings.support_bridge_url, ai_service=ai_service)

telegram_service = TelegramService(
    settings.telegram_bot_token,
    proxy=settings.telegram_proxy,
    support=support_service,
)

max_service = MaxService(
    settings.max_bot_token,
    api_url=settings.max_api_url,
    verify_ssl=settings.max_verify_ssl,
    ca_bundle=settings.max_ca_bundle,
)
