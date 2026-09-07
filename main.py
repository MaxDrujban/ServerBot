from fastapi import FastAPI
from api.routes import router
from config import settings
from services.max_service import MaxService
from services.telegram_service import TelegramService
from contextlib import asynccontextmanager
import logging

logger = logging.getLogger(__name__)

max_service = MaxService(settings.max_bot_token)
telegram_service = TelegramService(
    settings.telegram_bot_token,
    proxy=settings.telegram_proxy,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await max_service.set_webhook(settings.max_webhook_url)
        logger.info("MAX webhook registered")
    except Exception:
        logger.exception("Could not register MAX webhook during startup")

    if settings.telegram_webhook_url:
        try:
            await telegram_service.set_webhook(
                settings.telegram_webhook_url,
                secret_token=settings.telegram_webhook_secret,
            )
            logger.info("Telegram webhook registered")
        except Exception:
            logger.exception("Could not register Telegram webhook during startup")
    yield
    logger.info("Application shutting down")

app = FastAPI(lifespan=lifespan)
app.include_router(router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.api_port)
