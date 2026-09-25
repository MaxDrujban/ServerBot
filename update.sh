#!/usr/bin/env bash
# Обновление ServerBot на сервере: забрать код, пересобрать образ, пересоздать контейнер.
#
#   ./update.sh           обычное обновление
#   ./update.sh --clean   то же, но с полной пересборкой без кеша
#
# Запуск из каталога проекта:  cd /opt/serverbot && ./update.sh
set -euo pipefail

cd "$(dirname "$0")"

BUILD_ARGS=""
if [ "${1:-}" = "--clean" ]; then
    BUILD_ARGS="--no-cache"
fi

if [ ! -f .env ]; then
    echo "ОШИБКА: нет файла .env — контейнер не запустится."
    echo "Список переменных: README, раздел «Переменные окружения»."
    exit 1
fi

echo "== 1/5 Забираю код из git =="
git pull --ff-only

echo "== 2/5 Собираю образ =="
docker compose build $BUILD_ARGS

echo "== 3/5 Пересоздаю контейнер =="
docker compose up -d --force-recreate

echo "== 4/5 Состояние =="
docker compose ps

echo "== 5/5 Проверяю API =="
sleep 3

if curl -fsS http://127.0.0.1:8010/telegram/health; then
    echo
    echo "Готово: сервис отвечает."
else
    echo
    echo "ВНИМАНИЕ: API не ответил. Смотрите логи:"
    echo "  docker compose logs --tail 40 serverbot"
    exit 1
fi
