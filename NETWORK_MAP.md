# Сетевая карта системы

Общая схема сетевых связей и модулей: **ServerBot** (шлюз мессенджеров), **SMB Monitor**
(веб-приложение с чатом поддержки) и **микросервис инференса** (локальный ИИ-ассистент).

Локальный ассистент описан отдельно в [LOCAL_AI.md](LOCAL_AI.md).

## Диаграмма

```mermaid
flowchart LR
    subgraph External["Внешние системы"]
        User["Пользователь"]
        TG["Telegram API"]
        MX["MAX API"]
        DS["DeepSeek API (альтернатива)"]
    end

    subgraph Proxy["HappProxy (Windows, SOCKS5 :10808)"]
        HP["SOCKS5 proxy"]
    end

    subgraph SB["Контейнер ServerBot :8010"]
        FAST["FastAPI"]
        POLL["Telegram polling"]
        MAXS["MaxService"]
        AI["AiService"]
    end

    subgraph SMB["Контейнер SMB Monitor"]
        EX["Express API :3030"]
        WS["WebSocket чат :8081"]
        BR["Bridge ServerBot :8082"]
        PDB[("PostgreSQL :5432")]
        UI["Браузер сотрудника"]
    end

    subgraph GPUHOST["Хост с GPU: ВМ микросервиса инференса"]
        OL["Ollama :11434"]
        CARD["GPU 4 ГБ VRAM"]
    end

    User -->|сообщение| TG
    TG -->|getUpdates| POLL
    POLL -.->|SOCKS5| HP
    POLL --> FAST
    FAST -->|POST /internal/support/message| BR
    BR -->|рассылка| WS
    WS --> UI
    UI -->|ответ сотрудника| WS
    WS --> BR
    BR -->|POST /integrations/support/reply| FAST
    FAST -->|sendMessage| TG
    FAST --> AI
    AI -->|"POST /v1/chat/completions"| OL
    OL --- CARD
    AI -.->|"если AI_BASE_URL указывает в облако"| DS
    FAST --> MAXS
    MAXS --> MX
    EX --> PDB
```

## Направления трафика

| Из | В | Протокол / порт | Назначение |
|----|----|-----------------|------------|
| Telegram API | ServerBot polling | HTTPS (через SOCKS5 `:10808`) | получение сообщений |
| ServerBot | SMB Monitor bridge | HTTP `:8082` | передача обращения в чат |
| Bridge | WebSocket-чат | внутренний процесс | рассылка сотрудникам |
| WebSocket-чат | Браузер | WS `:8081` | доставка сообщений в UI |
| Браузер | WebSocket-чат | WS `:8081` | ответ сотрудника |
| Bridge | ServerBot | HTTP `:8010` | отправка ответа пользователю |
| ServerBot | Telegram API | HTTPS (через SOCKS5 `:10808`) | ответ пользователю |
| ServerBot | Микросервис инференса | HTTP `:11434` | автоответ ИИ (локальная модель) |
| ServerBot | DeepSeek API | HTTPS `:443` | автоответ ИИ (внешний API, альтернативный режим) |
| ServerBot | MAX API | HTTPS `:443` | работа с MAX |
| Express API | PostgreSQL | TCP `:5432` | данные мониторинга |

## Порты

| Порт | Сервис | Где слушает |
|------|--------|-------------|
| 8010 | ServerBot FastAPI | контейнер ServerBot |
| 3030 | SMB Monitor Express API | контейнер SMB Monitor |
| 8081 | SMB Monitor WebSocket-чат | контейнер SMB Monitor |
| 8082 | SMB Monitor bridge ServerBot | контейнер SMB Monitor |
| 11434 | Микросервис инференса (Ollama) | ВМ на хосте с GPU |
| 10808 | HappProxy SOCKS5 | Windows-хост (для Telegram) |
| 5432 | PostgreSQL | хост или отдельный контейнер |

## Ключевые модули

### ServerBot (`main.py`, `api/routes.py`, `services/*`)

- `TelegramService` — polling/webhook, команды, пересылка в bridge.
- `MaxService` — отправка сообщений и webhook MAX.
- `AiService` — автоответы: локальная модель или внешний API (выбирается через `AI_BASE_URL`).
- `SupportService` — пересылка обращений в чат поддержки и генерация автоответов с историей диалога.
- `routes.py` — REST API и обработчики webhook.

### Микросервис инференса (Ollama на хосте с GPU)

- OpenAI-совместимый API `/v1/chat/completions`, модель `qwen2.5:3b-instruct-q8_0`.
- Модель целиком (89–100%) считается на GPU; подробности и инструкции — в `LOCAL_AI.md`.

### SMB Monitor (`server.js`, `chat/websocket.js`)

- `server.js` — Express API: авторизация, мониторинг, чат.
- `chat/websocket.js` — WebSocket-чат `8081` и bridge `8082`.
- `chat/chat.js` — клиент чата: вкладки, бейджи, отображение.

## Поток обращения пользователя

```text
1. Пользователь пишет боту (Telegram/MAX)
2. ServerBot получает сообщение (polling)
3. ServerBot отправляет в bridge :8082
4. Bridge рассылает сотрудникам через WebSocket :8081
5. Ассистент отвечает автоматически: локальная модель (:11434) или внешний API
6. Сотрудник отвечает в чате
7. Bridge отправляет ответ в ServerBot
8. ServerBot отправляет ответ пользователю в Telegram/MAX
```
