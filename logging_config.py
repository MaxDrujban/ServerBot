"""Настройка логирования: один формат, фильтрация «шумных» библиотек.

Вызывается первой строкой main.py, до импорта приложения, потому что
logging.basicConfig() молча ничего не делает, если у корневого логгера
уже появился обработчик.
"""

import logging

# httpx и httpcore пишут полный URL каждого запроса на уровне INFO,
# а в URL Telegram лежит токен бота — на INFO это утечка секрета в логи
NOISY_LOGGERS = ("httpx", "httpcore")


def configure_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    for name in NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)
