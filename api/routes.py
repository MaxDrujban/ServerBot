from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from config import settings
from models.message import MessageRequest, MessageResponse
from services.instances import max_service, support_service, telegram_service
from services.max_service import extract_incoming_message
from services.support_service import parse_external_user

import httpx
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


async def _post_to_support_bridge(path: str, payload: dict):
    async with httpx.AsyncClient(timeout=10, trust_env=False) as client:
        response = await client.post(
            f"{settings.support_bridge_url}{path}",
            json=payload,
        )
        response.raise_for_status()
        return response.json()


def _verify_secret(request: Request, expected: str | None, header: str):
    """Проверка подписи вебхука по заголовку.

    Если секрет не задан в настройках, проверка считается пройденной.
    Для боевого режима секрет нужен обязательно.
    """
    if not expected:
        return True

    return request.headers.get(header) == expected


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
        await telegram_service.send_bulk(req.chat_ids, req.text)
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


@router.post("/integrations/support/message")
async def support_message(request: Request):
    payload = await request.json()
    external_user = payload.get("external_user")
    text = payload.get("message")

    if not external_user or not text:
        raise HTTPException(status_code=400, detail="external_user and message are required")

    return await _post_to_support_bridge(
        "/internal/support/message",
        {
            "external_user": external_user,
            "message": text,
            "source": payload.get("source", "telegram"),
            "timestamp": payload.get("timestamp"),
        },
    )


@router.post("/integrations/support/reply")
async def support_reply(request: Request):
    payload = await request.json()
    external_user = payload.get("external_user")
    text = payload.get("message")

    if not external_user or not text:
        raise HTTPException(status_code=400, detail="external_user and message are required")

    try:
        channel, target = parse_external_user(str(external_user))
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err

    try:
        if channel == "telegram":
            await telegram_service.send_message(chat_id=target["chat_id"], text=text)
        else:
            await max_service.send_with_retry(text=text, **target)
    except Exception as err:
        logger.exception("Ответ не отправлен в %s (external_user=%s)", channel, external_user)
        raise HTTPException(status_code=502, detail=f"{channel}: {err}") from err

    return {"status": "sent", "channel": channel}


@router.post("/telegram/webhook")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    if not _verify_secret(request, settings.telegram_webhook_secret, "X-Telegram-Bot-Api-Secret-Token"):
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

    result = await telegram_service.send_alert(
        chat_id=str(chat_id),
        title=title,
        details=details,
        severity=severity,
    )
    return {"status": "ok", "result": result}


async def _process_max_update(update: dict):
    """Обработка события MAX: обращение уходит в чат поддержки, затем отвечает ИИ."""
    if update.get("update_type") != "message_created":
        return

    incoming = extract_incoming_message(update)
    if not incoming:
        return

    external_user = incoming["external_user"]
    logger.info("MAX message from %s: %s", external_user, incoming["text"])

    await support_service.forward_message(external_user, incoming["text"], incoming["display_name"], "max")

    try:
        reply = await support_service.ai_reply(external_user, incoming["text"])
    except Exception:
        logger.exception("AI reply failed for %s", external_user)
        reply = None

    if reply:
        await max_service.send_with_retry(text=reply, **incoming["target"])
        await support_service.forward_message(external_user, reply, "ИИ-ассистент", "ai")


async def _process_max_payload(payload: dict):
    """MAX присылает объект Update; принимаем и обёртку {"updates": [...]}."""
    updates = payload.get("updates") if isinstance(payload, dict) else None
    updates = updates if isinstance(updates, list) else [payload]

    for update in updates:
        if isinstance(update, dict):
            await _process_max_update(update)


@router.post("/webhook/max")
async def max_webhook(request: Request, background_tasks: BackgroundTasks):
    if not _verify_secret(request, settings.max_webhook_secret, "X-Max-Bot-Api-Secret"):
        raise HTTPException(status_code=403, detail="Invalid MAX secret token")

    payload = await request.json()
    logger.info("MAX webhook received: update_type=%s", payload.get("update_type"))
    background_tasks.add_task(_process_max_payload, payload)
    return {"status": "ok"}
    