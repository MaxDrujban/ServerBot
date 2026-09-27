"""Общая часть поддержки для Telegram и MAX:

* разбор идентификатора внешнего пользователя, который хранится в комнате чата;
* пересылка обращений в чат поддержки приложения (bridge на порту 8082);
* автоответ ИИ-ассистента с историей переписки по каждому собеседнику.
"""

import logging
from typing import Any, Dict, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)


def parse_external_user(external_user: str) -> Tuple[str, Dict[str, int]]:
    """Разбирает идентификатор собеседника и говорит, куда отправлять ответ.

    Форматы:
      telegram:123456  -> ("telegram", {"chat_id": 123456})
      max:user:123     -> ("max", {"user_id": 123})
      max:chat:456     -> ("max", {"chat_id": 456})
    """
    if not isinstance(external_user, str) or ":" not in external_user:
        raise ValueError(f"Ожидается формат '<канал>:<id>', получено: {external_user!r}")

    parts = external_user.split(":")
    channel = parts[0].lower()

    if channel == "telegram":
        if len(parts) == 2 and parts[1].isdigit():
            return "telegram", {"chat_id": int(parts[1])}
        raise ValueError(f"Идентификатор Telegram ожидается в виде 'telegram:<chat_id>', получено: {external_user!r}")

    if channel == "max":
        # Личный диалог: отвечаем по user_id
        if len(parts) == 2 and parts[1].isdigit():
            return "max", {"user_id": int(parts[1])}

        # Групповой чат или канал: отвечаем по chat_id
        if len(parts) == 3 and parts[1].lower() in ("user", "chat") and parts[2].isdigit():
            return "max", {f"{parts[1].lower()}_id": int(parts[2])}

        raise ValueError(f"Идентификатор MAX ожидается в виде 'max:user:<id>' или 'max:chat:<id>', получено: {external_user!r}")

    raise ValueError(f"Неизвестный канал: {external_user!r}")


class SupportService:
    """Пересылка обращений в чат поддержки приложения и автоответы ИИ."""

    def __init__(self, bridge_url: Optional[str] = None, ai_service: Optional[Any] = None):
        self.bridge_url = bridge_url
        self.ai_service = ai_service
        self.conversations: Dict[str, list] = {}

    @property
    def enabled(self) -> bool:
        """Чат поддержки подключён, если задан адрес bridge."""
        return bool(self.bridge_url)

    async def forward_message(
        self,
        external_user: str,
        text: str,
        display_name: Optional[str] = None,
        source: str = "telegram",
    ) -> Optional[Dict[str, Any]]:
        """Отправляет сообщение в чат поддержки приложения."""
        if not self.bridge_url:
            return None

        async with httpx.AsyncClient(timeout=10, trust_env=False) as client:
            response = await client.post(
                f"{self.bridge_url}/internal/support/message",
                json={
                    "external_user": external_user,
                    "display_name": display_name,
                    "message": text,
                    "source": source,
                },
            )
            response.raise_for_status()
            return response.json()

    async def ai_reply(self, conversation_key: str, text: str) -> Optional[str]:
        """Ответ ИИ-ассистента с учётом истории диалога.

        conversation_key — идентификатор собеседника, у каждого своя история.
        Возвращает None, если ИИ выключен.
        """
        if not self.ai_service:
            return None

        history = self.conversations.setdefault(conversation_key, [])
        history.append({"role": "user", "content": text})

        reply = await self.ai_service.chat(history[-20:])
        history.append({"role": "assistant", "content": reply})
        return reply
