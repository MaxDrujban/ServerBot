from telegram import Bot
import asyncio


class TelegramService:

    def __init__(self, token: str):
        self.bot = Bot(token=token)

    async def send_bulk(self, chat_ids, text):
        await asyncio.gather(
            *[self.bot.send_message(chat_id=c, text=text) for c in chat_ids],
            return_exceptions=True
        )
