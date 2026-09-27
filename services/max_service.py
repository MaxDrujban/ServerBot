"""Клиент Bot API MAX: https://dev.max.ru/docs-api

Особенности API, важные для работы:
* базовый домен — platform-api2.max.ru (старый platform-api.max.ru не использовать);
* токен передаётся в заголовке Authorization: <token>, без префикса Bearer;
* отправка: POST /messages?user_id=<id> для диалога и ?chat_id=<id> для чата или канала;
* лимит — два сообщения в секунду в один диалог, при превышении приходит 429;
* события приходят вебхуком (POST /subscriptions), подпись — заголовок X-Max-Bot-Api-Secret.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Union

import httpx

logger = logging.getLogger(__name__)

DEFAULT_API_URL = "https://platform-api2.max.ru"
RETRYABLE_STATUSES = {429, 500, 503}


def display_name(user: Dict[str, Any]) -> str:
    """Имя собеседника для чата поддержки. Поле name в API устарело, не используем его."""
    first = user.get("first_name") or ""
    last = user.get("last_name") or ""
    username = user.get("username") or ""

    return f"{first} {last}".strip() or username or f"MAX {user.get('user_id')}"


def extract_incoming_message(update: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Достаёт из события MAX данные обращения.

    Возвращает None, если событие не является текстовым сообщением.
    """
    message = update.get("message") or {}
    sender = message.get("sender") or {}
    recipient = message.get("recipient") or {}
    body = message.get("body") or {}

    text = body.get("text")
    user_id = sender.get("user_id")
    chat_id = recipient.get("chat_id")
    chat_type = str(recipient.get("chat_type") or "dialog").lower()

    if not text or not user_id:
        return None

    # Личный диалог: отвечаем пользователю по user_id
    if chat_type == "dialog" or not chat_id:
        return {
            "external_user": f"max:user:{user_id}",
            "target": {"user_id": user_id},
            "text": text,
            "display_name": display_name(sender),
        }

    # Групповой чат или канал: отвечаем по chat_id
    return {
        "external_user": f"max:chat:{chat_id}",
        "target": {"chat_id": chat_id},
        "text": text,
        "display_name": display_name(sender),
    }


class MaxService:
    """Отправка сообщений и подписка на события MAX."""

    def __init__(self, token: str, api_url: str = DEFAULT_API_URL, verify_ssl: bool = True):
        self.token = token
        self.api = api_url.rstrip("/")
        self.verify_ssl = verify_ssl

    def _client(self) -> httpx.AsyncClient:
        # trust_env=False: прокси окружения настроен для Telegram и здесь не нужен
        return httpx.AsyncClient(timeout=10, trust_env=False, proxy=None, verify=self.verify_ssl)

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": self.token, "Content-Type": "application/json"}

    async def set_webhook(
        self,
        url: str,
        secret: Optional[str] = None,
        update_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Подписка на события бота: POST /subscriptions."""
        payload: Dict[str, Any] = {"url": url}

        if secret:
            payload["secret"] = secret
        if update_types:
            payload["update_types"] = update_types

        async with self._client() as client:
            response = await client.post(f"{self.api}/subscriptions", headers=self._headers(), json=payload)
            response.raise_for_status()
            return response.json()

    async def send_message(
        self,
        text: str,
        user_id: Optional[Union[int, str]] = None,
        chat_id: Optional[Union[int, str]] = None,
    ) -> Dict[str, Any]:
        """Отправка сообщения в диалог (user_id) или чат и канал (chat_id)."""
        if user_id is None and chat_id is None:
            raise ValueError("Нужно указать user_id или chat_id")

        params = {"user_id": user_id} if user_id is not None else {"chat_id": chat_id}

        async with self._client() as client:
            response = await client.post(
                f"{self.api}/messages",
                params=params,
                headers=self._headers(),
                json={"text": text},
            )
            response.raise_for_status()
            return response.json()

    async def send_with_retry(
        self,
        text: str,
        user_id: Optional[Union[int, str]] = None,
        chat_id: Optional[Union[int, str]] = None,
        attempts: int = 3,
        base_delay: float = 0.5,
    ) -> Dict[str, Any]:
        """Отправка с повторами: сеть и лимит запросов сбоят временно."""
        for attempt in range(1, attempts + 1):
            try:
                return await self.send_message(text=text, user_id=user_id, chat_id=chat_id)
            except httpx.HTTPStatusError as err:
                if attempt == attempts or err.response.status_code not in RETRYABLE_STATUSES:
                    raise
                delay = base_delay * attempt
                logger.warning(
                    "MAX ответил %s, повтор через %.1f с (попытка %s)",
                    err.response.status_code,
                    delay,
                    attempt,
                )
            except httpx.TransportError as err:
                if attempt == attempts:
                    raise
                delay = base_delay * attempt
                logger.warning(
                    "Отправка в MAX не удалась (%s), повтор через %.1f с (попытка %s)",
                    type(err).__name__,
                    delay,
                    attempt,
                )

            await asyncio.sleep(delay)

    async def send_bulk_messages(self, chat_ids: List[Union[int, str]], text: str) -> List[Any]:
        """Отправка одного текста в несколько чатов — для ручки /send/max."""
        results = await asyncio.gather(
            *[self.send_with_retry(text=text, chat_id=chat_id) for chat_id in chat_ids],
            return_exceptions=True,
        )

        for chat_id, result in zip(chat_ids, results):
            if isinstance(result, Exception):
                logger.error("Сообщение в чат MAX %s не отправлено: %s", chat_id, result)

        return results
