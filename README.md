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
models/message.py             Pydantic-модели
Dockerfile, docker-compose.yml
```

## Переменные окружения (`.env`)

```env
TELEGRAM_BOT_TOKEN=...
MAX_BOT_TOKEN=...
API_PORT=8010
MAX_WEBHOOK_URL=https://example.com/webhook/max
MAX_WEBHOOK_SECRET=...            # секрет подписки: приходит в заголовке X-Max-Bot-Api-Secret
MAX_API_URL=https://platform-api2.max.ru
MAX_VERIFY_SSL=true               # false только если сертификат Минцифры не установлен в образ
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

## Настройка MAX

MAX не использует опрос: события приходят вебхуком на `POST /webhook/max`.

1. Подписка создаётся при старте приложения — `POST /subscriptions` с адресом из `MAX_WEBHOOK_URL`,
   списком событий `message_created` и `bot_started`, и секретом из `MAX_WEBHOOK_SECRET`.
2. Требования MAX к адресу: HTTPS строго на порту 443 (в URL порт не указывается), сертификат
   доверенного центра или Минцифры, полная цепочка сертификатов. Если адрес не отвечает `200`
   в течение 30 секунд, MAX повторяет доставку, а через 8 часов отписывает бота.
3. Секрет приходит в заголовке `X-Max-Bot-Api-Secret`. Если `MAX_WEBHOOK_SECRET` задан,
   запросы с чужой подписью отклоняются с кодом 403.
4. Запросы к API идут на `platform-api2.max.ru` (домен `platform-api.max.ru` устарел). Сертификаты
   Минцифры уже добавлены в образ (`certs/`, файлы с https://gu-st.ru/content/Other/doc/russiantrustedca.pem).
   Если цепочка всё равно не проходит: укажите свой файл в `MAX_CA_BUNDLE=/путь/к/ca.pem`
   (или, для разовой проверки, `MAX_VERIFY_SSL=false` — это отключает проверку TLS и годится только для отладки).

Адресация собеседников в чате поддержки:

```text
max:user:<id>   личный диалог -> POST /messages?user_id=<id>
max:chat:<id>   чат или канал -> POST /messages?chat_id=<id>
```

Из сообщений MAX обрабатывается только текст: вложения в чат поддержки не переносятся.

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
./update.sh            # git pull + сборка образа + пересоздание контейнера + проверка API
./update.sh --clean    # то же, но с полной пересборкой без кеша
```

Первое обновление, пока скрипта на сервере ещё нет:

```bash
cd /opt/serverbot
git pull origin main
docker compose build
docker compose up -d --force-recreate
```

> После изменения кода обязательно выполняйте сборку (`./update.sh`), иначе образ останется старым.
