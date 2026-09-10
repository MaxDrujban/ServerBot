# ServerBot

FastAPI-сервис — шлюз между Telegram/MAX и веб-приложением SMB Monitor.

## Назначение

Принимает сообщения пользователей из Telegram/MAX, передаёт их в чат поддержки SMB Monitor и возвращает ответы поддержки обратно пользователям. Поддерживает автоответы через DeepSeek API.

## Архитектура

```text
Telegram/MAX user
  → ServerBot (polling или webhook)
  → POST /internal/support/message (bridge SMB Monitor)
  → чат поддержки

Ответ поддержки из SMB Monitor
  → POST /integrations/support/reply
  → Telegram/MAX user
```

## Стек

- Python 3.12, FastAPI, uvicorn
- python-telegram-bot
- httpx
- pydantic-settings
- Docker / Docker Compose

## Структура

```
main.py                  точка входа, lifespan, polling
config.py                настройки из .env
api/routes.py            REST API и webhook-маршруты
services/telegram_service.py  логика Telegram
services/max_service.py       клиент MAX
services/ai_service.py        DeepSeek AI ассистент
clients/httpt_client.py       HTTP-клиент
models/message.py             Pydantic-модели
Dockerfile, docker-compose.yml
```

## Переменные окружения (`.env`)

```env
TELEGRAM_BOT_TOKEN=...
MAX_BOT_TOKEN=...
API_PORT=8010
MAX_WEBHOOK_URL=https://example.com/webhook/max
TELEGRAM_WEBHOOK_URL=https://example.com/telegram/webhook
TELEGRAM_WEBHOOK_SECRET=...
TELEGRAM_MODE=polling
TELEGRAM_PROXY=socks5://PROXY_HOST:PORT
SUPPORT_BRIDGE_URL=http://SMB_MONITOR_HOST:8082
AI_ENABLED=true
AI_API_KEY=...
AI_BASE_URL=https://api.deepseek.com
AI_MODEL=deepseek-chat
AI_SYSTEM_PROMPT=...
```

## Режимы Telegram

- `TELEGRAM_MODE=polling` — сервер сам опрашивает Telegram через `getUpdates`.
- `TELEGRAM_MODE=webhook` — Telegram отправляет update на публичный HTTPS-адрес.

Не включайте polling и webhook одновременно для одного бота.

## Запуск (Docker)

```bash
cp .env.example .env   # заполните значения
docker compose build
docker compose up -d
docker compose logs -f serverbot
```

Проверка:

```bash
curl http://127.0.0.1:8010/telegram/health
# {"status":"ok"}
```

## Обновление на сервере

```bash
cd /opt/serverbot
git pull origin main
docker compose build --no-cache
docker compose up -d --force-recreate
```

> После изменения кода обязательно выполняйте `docker compose build`, иначе образ останется старым.
