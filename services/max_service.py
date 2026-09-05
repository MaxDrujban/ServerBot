import httpx
import asyncio
from typing import List, Union

class MaxService:
    def __init__(self, token: str):
        self.token = token
        self.api = "https://platform-api.max.ru"

    def headers(self):
        return {
            "Authorization": self.token,
            "Content-Type": "application/json",
        }

    async def set_webhook(self, url: str):
        """
        Регистрация webhook для MAX бота
        """
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                f"{self.api}/subscriptions",
                headers=self.headers(),
                json={"url": url}
            )
            r.raise_for_status()
            return r.json()

    async def send_message(
    self, 
    chat_id: Union[int, str], 
    text: str, 
    disable_link_preview: bool = False, 
    notify: bool = True, 
    format: str = "markdown"
    ):
        """
        Отправка одного сообщения в чат MAX.
        """
        chat_id_str = str(chat_id)  # Приводим к строке
        url = f"{self.api}/messages?chat_id={chat_id_str}"  # Добавляем query param (или ?user_id= если для пользователей)

        payload = {
            "text": text,
            "disable_link_preview": disable_link_preview,
            "notify": notify,
            "format": format
        }

        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(url, headers=self.headers(), json=payload)
            r.raise_for_status()
            return r.json()

    async def send_bulk_messages(self, chat_ids: List[Union[int, str]], text: str):
        """
        Отправка сообщения сразу в несколько чатов (по одному запросу на чат).
        """
        async with httpx.AsyncClient(timeout=10) as client:

            async def send(chat_id):
                chat_id_str = str(chat_id)
                url = f"{self.api}/messages?chat_id={chat_id_str}"  # Добавляем query param

                payload = {
                    "text": text,
                    "disable_link_preview": False,
                    "notify": True,
                    "format": "markdown"
                }
                try:
                    r = await client.post(url, headers=self.headers(), json=payload)
                    r.raise_for_status()
                    return r.json()
                except httpx.HTTPStatusError as e:
                    return {"chat_id": chat_id, "error": e.response.text}

            tasks = [send(chat_id) for chat_id in chat_ids]
            results = await asyncio.gather(*tasks)
            return results
