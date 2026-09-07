from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from models.message import MessageRequest, MessageResponse
from services.telegram_service import TelegramService
from services.max_service import MaxService
from config import settings
import httpx
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

telegram = TelegramService(
    settings.telegram_bot_token,
    proxy=settings.telegram_proxy,
)
max_service = MaxService(settings.max_bot_token)


def _verify_telegram_secret(request: Request):
    expected = settings.telegram_webhook_secret
    if not expected:
        return True
    provided = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    return provided == expected


async def _process_telegram_update(payload: dict):
    try:
        logger.info("Processing Telegram update_id=%s", payload.get("update_id"))
        result = await telegram.handle_update(payload)
        logger.info("Telegram update processed: update_id=%s result=%s", payload.get("update_id"), result)
    except Exception:
        logger.exception("Telegram update processing failed: update_id=%s", payload.get("update_id"))


@router.get("/telegram/health")
async def telegram_health():
    return {"status": "ok"}


@router.post("/send/telegram", response_model=MessageResponse)
async def send_telegram(req: MessageRequest):
    try:
        await telegram.send_bulk(req.chat_ids, req.text)
        return MessageResponse(
            status="success",
            message=f"Telegram OK ({len(req.chat_ids)})"
        )
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/telegram/send", response_model=MessageResponse)
async def send_telegram_message(req: MessageRequest):
    try:
        await telegram.send_bulk(req.chat_ids, req.text)
        return MessageResponse(
            status="success",
            message=f"Telegram OK ({len(req.chat_ids)})"
        )
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/send/max", response_model=MessageResponse)
async def send_max(request: MessageRequest):
    try:
        # Не преобразуем к int, MAX может принимать строки
        chat_ids = request.chat_ids
        await max_service.send_bulk_messages(chat_ids, request.text)

        return MessageResponse(
            status="success",
            message=f"MAX OK ({len(chat_ids)})"
        )

    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e.response.text))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# @router.post("/messages")
# async def receive_max_webhook(payload: dict):

#     print("MAX WEBHOOK:")
#     print(payload)

#     return {"status": "ok"}


@router.get("/webhook/health")
async def webhook_health():
    return {"status": "ok"}


@router.post("/telegram/webhook")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    if not _verify_telegram_secret(request):
        raise HTTPException(status_code=403, detail="Invalid Telegram secret token")

    payload = await request.json()
    logger.info("Telegram webhook received: update_id=%s", payload.get("update_id"))
    background_tasks.add_task(_process_telegram_update, payload)
    return {"status": "ok"}


@router.post("/telegram/alert")
async def telegram_alert(request: Request):
    payload = await request.json()
    chat_id = payload.get("chat_id") or payload.get("chatId")
    title = payload.get("title") or "Alert"
    details = payload.get("details") or payload.get("message") or "No details"
    severity = payload.get("severity") or "info"

    if not chat_id:
        raise HTTPException(status_code=400, detail="chat_id is required")

    result = await telegram.send_alert(
        chat_id=str(chat_id),
        title=title,
        details=details,
        severity=severity,
    )
    return {"status": "ok", "result": result}


@router.post("/webhook/max")
async def max_webhook(request: Request):
    data = await request.json()

    print("WEBHOOK HIT")

    message = data.get("message", {})
    body = message.get("body", {})
    sender = message.get("sender", {})
    recipient = message.get("recipient", {})

    text = body.get("text")
    chat_id = recipient.get("chat_id")
    user_id = sender.get("user_id")
    name = sender.get("name")

    print("TEXT:", text)
    print("CHAT ID:", chat_id)
    print("USER ID:", user_id)
    print("NAME:", name)
    print(f'{name} \n {text}')
    if text:
        await max_service.send_message(
            chat_id=chat_id,
            text=f"Ты написал: {text}"
        )

    return {"status": "ok"}
    