import asyncio
from typing import Any, Dict, Optional

from telegram import Bot
from telegram.request import HTTPXRequest


class TelegramService:

    def __init__(self, token: str, proxy: Optional[str] = None):
        request_kwargs = {"proxy": proxy, "httpx_kwargs": {"trust_env": False}}
        self.bot = Bot(
            token=token,
            request=HTTPXRequest(**request_kwargs),
            get_updates_request=HTTPXRequest(**request_kwargs),
        )
        self.users: Dict[int, Dict[str, Any]] = {}
        self.chat_ids = set()

    def remember_user(self, chat_id: int, user_id: Optional[int], username: Optional[str] = None, first_name: Optional[str] = None):
        chat_id = int(chat_id)
        user_id = int(user_id) if user_id is not None else None
        self.chat_ids.add(chat_id)
        self.users[chat_id] = {
            "chat_id": chat_id,
            "user_id": user_id,
            "username": username,
            "first_name": first_name,
        }
        return self.users[chat_id]

    async def set_webhook(self, url: str, secret_token: Optional[str] = None):
        kwargs = {"url": url, "drop_pending_updates": True}
        if secret_token:
            kwargs["secret_token"] = secret_token
        return await self.bot.set_webhook(**kwargs)

    async def get_webhook_info(self):
        return await self.bot.get_webhook_info()

    async def send_message(self, chat_id: int, text: str):
        return await self.bot.send_message(chat_id=chat_id, text=text)

    async def answer_callback_query(self, callback_query_id: str, text: str):
        return await self.bot.answer_callback_query(callback_query_id=callback_query_id, text=text)

    async def send_alert(self, chat_id: int, title: str, details: str, severity: str = "info"):
        emoji = {
            "info": "ℹ️",
            "warning": "⚠️",
            "critical": "🚨",
            "ok": "✅",
        }.get(severity.lower(), "ℹ️")

        text = (
            f"{emoji} {title}\n\n"
            f"{details}"
        )
        return await self.send_message(chat_id, text)

    async def send_bulk(self, chat_ids, text):
        await asyncio.gather(
            *[self.bot.send_message(chat_id=c, text=text) for c in chat_ids],
            return_exceptions=True
        )

    async def _handle_command(self, chat_id: int, text: str, user: Dict[str, Any]):
        cleaned = text.strip().lower()

        if cleaned in ("/start", "/help", "/status", "/ping"):
            self.remember_user(
                chat_id=chat_id,
                user_id=user.get("id"),
                username=user.get("username"),
                first_name=user.get("first_name"),
            )

        if cleaned == "/start":
            return await self.send_message(
                chat_id,
                "Привет! Я бот для уведомлений.\n\nКоманды:\n/start - начать\n/help - помощь\n/status - показать состояние\n/ping - проверка связи"
            )

        if cleaned == "/help":
            return await self.send_message(
                chat_id,
                "Доступные команды:\n/start\n/help\n/status\n/ping"
            )

        if cleaned == "/status":
            return await self.send_message(
                chat_id,
                f"Активных чатов: {len(self.chat_ids)}\nВаш chat_id: {chat_id}"
            )

        if cleaned == "/ping":
            return await self.send_message(chat_id, "pong")

        return await self.send_message(chat_id, "Неизвестная команда. Используйте /help")

    async def _handle_callback(self, callback_query: Dict[str, Any]):
        callback_id = callback_query.get("id")
        data = callback_query.get("data") or ""
        message = callback_query.get("message", {})
        chat = message.get("chat", {})
        chat_id = chat.get("id")
        user = callback_query.get("from", {})

        self.remember_user(
            chat_id=chat_id,
            user_id=user.get("id"),
            username=user.get("username"),
            first_name=user.get("first_name"),
        )

        if not data:
            await self.bot.answer_callback_query(callback_query_id=callback_id, text="Нет данных")
            return {"status": "ignored"}

        if data.startswith("alert_ack:"):
            await self.answer_callback_query(callback_query_id=callback_id, text="Подтверждено")
            return {"status": "acknowledged", "data": data}

        if data.startswith("action:"):
            action = data.split(":", 1)[1]
            await self.answer_callback_query(callback_query_id=callback_id, text=f"Действие: {action}")
            return {"status": "action", "data": action}

        await self.answer_callback_query(callback_query_id=callback_id, text="Неизвестный callback")
        return {"status": "unknown_callback", "data": data}

    async def handle_update(self, update_payload: Dict[str, Any]):
        if not update_payload:
            return {"status": "empty"}

        if "message" in update_payload:
            message = update_payload["message"]
            chat = message.get("chat", {})
            chat_id = chat.get("id")
            user = message.get("from", {})
            text = message.get("text", "")

            if not chat_id:
                return {"status": "missing_chat_id"}

            self.remember_user(
                chat_id=chat_id,
                user_id=user.get("id"),
                username=user.get("username"),
                first_name=user.get("first_name"),
            )

            if text.startswith("/"):
                return await self._handle_command(chat_id, text, user)

            return await self.send_message(chat_id, f"Получено сообщение: {text}")

        if "callback_query" in update_payload:
            return await self._handle_callback(update_payload["callback_query"])

        return {"status": "ignored"}
