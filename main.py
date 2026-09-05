from fastapi import FastAPI
from api.routes import router
from config import settings
from services.max_service import MaxService
from contextlib import asynccontextmanager

max_service = MaxService(settings.max_bot_token)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await max_service.set_webhook(settings.max_webhook_url)
    print("MAX webhook registered")
    yield
    # Shutdown
    print("Application shutting down")

app = FastAPI(lifespan=lifespan)
app.include_router(router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.api_port)
