import asyncio
import logging
from typing import Any, Dict, Optional

import httpx
from telegram import Bot
from telegram.request import HTTPXRequest

logger = logging.getLogger(__name__)


class TelegramService:

    def __init__(
        self,
        token: str,
        proxy: Optional[str] = None,
        support_bridge_url: Optional[str] = None,
        ai_service: Optional[Any] = None,
    ):
        request_kwargs = {"proxy": proxy, "httpx_kwargs": {"trust_env": False}}
        self.bot = Bot(
            token=token,
            request=HTTPXRequest(**request_kwargs),
            get_updates_request=HTTPXRequest(**request_kwargs),
        )
        self.users: Dict[int, Dict[str, Any]] = {}
        self.chat_ids = set()
        self._support_bridge_url = support_bridge_url
        self.ai_service = ai_service
        self.conversations: Dict[int, list] = {}

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

    async def _send_support_message(self, external_user: str, text: str, display_name: Optional[str] = None, source: str = "telegram"):
        async with httpx.AsyncClient(timeout=10, trust_env=False) as client:
            response = await client.post(
                f"{self._support_bridge_url}/internal/support/message",
                json={
                    "external_user": external_user,
                    "display_name": display_name,
                    "message": text,
                    "source": source,
                },
            )
            response.raise_for_status()
            return response.json()

    async def delete_webhook(self):
        return await self.bot.delete_webhook(drop_pending_updates=False)

    async def poll_updates(self, stop_event: asyncio.Event):
        offset = None
        logger.info("Telegram polling loop started")
        while not stop_event.is_set():
            try:
                updates = await self.bot.get_updates(
                    offset=offset,
                    timeout=30,
                    allowed_updates=["message", "callback_query"],
                )
                if updates:
                    logger.info("Telegram polling received %s update(s)", len(updates))
                for update in updates:
                    await self.handle_update(update.to_dict())
                    offset = update.update_id + 1
            except Exception:
                if not stop_event.is_set():
                    logger.exception("Telegram polling iteration failed; retrying")
                    await asyncio.sleep(5)
        logger.info("Telegram polling loop stopped")

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

            if self._support_bridge_url:
                first = user.get("first_name") or ""
                last = user.get("last_name") or ""
                username = user.get("username") or ""
                display_name = (first + " " + last).strip() or username or f"telegram:{chat_id}"

                external_user = f"telegram:{chat_id}"
                await self._send_support_message(
                    external_user=external_user,
                    text=text,
                    display_name=display_name,
                    source="telegram",
                )

                # Автоответ ИИ-ассистента
                if self.ai_service:
                    try:
                        history = self.conversations.setdefault(chat_id, [])
                        history.append({"role": "user", "content": text})
                        reply = await self.ai_service.chat(history[-20:])
                        history.append({"role": "assistant", "content": reply})

                        await self.send_message(chat_id, reply)
                        await self._send_support_message(
                            external_user=external_user,
                            text=reply,
                            display_name="ИИ-ассистент",
                            source="ai",
                        )
                    except Exception:
                        logger.exception("AI reply failed")

                return {"status": "forwarded_to_support"}

            return await self.send_message(chat_id, f"Получено сообщение: {text}")

        if "callback_query" in update_payload:
            return await self._handle_callback(update_payload["callback_query"])

        return {"status": "ignored"}
