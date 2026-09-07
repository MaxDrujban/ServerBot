from fastapi import FastAPI
from api.routes import router
from config import settings
from services.max_service import MaxService
from services.telegram_service import TelegramService
from contextlib import asynccontextmanager
import asyncio
import logging

logger = logging.getLogger(__name__)

max_service = MaxService(settings.max_bot_token)
telegram_service = TelegramService(
    settings.telegram_bot_token,
    proxy=settings.telegram_proxy,
    support_bridge_url=settings.support_bridge_url,
)
poll_stop_event = asyncio.Event()
poll_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await max_service.set_webhook(settings.max_webhook_url)
        logger.info("MAX webhook registered")
    except Exception:
        logger.exception("Could not register MAX webhook during startup")

    if settings.telegram_mode.lower() == "polling":
        global poll_task
        await telegram_service.delete_webhook()
        logger.info("Telegram webhook removed; polling enabled")
        poll_task = asyncio.create_task(telegram_service.poll_updates(poll_stop_event))
    elif settings.telegram_webhook_url:
        try:
            await telegram_service.set_webhook(
                settings.telegram_webhook_url,
                secret_token=settings.telegram_webhook_secret,
            )
            webhook_info = await telegram_service.get_webhook_info()
            logger.info(
                "Telegram webhook registered: url=%s pending=%s last_error=%s",
                webhook_info.url,
                webhook_info.pending_update_count,
                webhook_info.last_error_message,
            )
        except Exception:
            logger.exception("Could not register Telegram webhook during startup")
    yield
    if poll_task:
        poll_stop_event.set()
        await poll_task
    logger.info("Application shutting down")

app = FastAPI(lifespan=lifespan)
app.include_router(router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.api_port)
