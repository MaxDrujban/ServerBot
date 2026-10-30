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

fail() {
    echo "ОШИБКА: $*" >&2
    exit 1
}

if [ ! -f .env ]; then
    echo "ОШИБКА: нет файла .env — контейнер не запустится."
    echo "Список переменных: README, раздел «Переменные окружения»."
    exit 1
fi

# Обязательные переменные: без них сервис стартует, но каналы не работают
for name in TELEGRAM_BOT_TOKEN MAX_BOT_TOKEN MAX_WEBHOOK_URL; do
    grep -qE "^[[:space:]]*$name[[:space:]]*=" .env || fail "в .env нет $name"
done

# Мост поддержки: значение по умолчанию в config.py указывает внутрь контейнера,
# поэтому отсутствие переменной почти всегда означает неработающий чат
if ! grep -qE "^[[:space:]]*SUPPORT_BRIDGE_URL[[:space:]]*=" .env; then
    echo "ВНИМАНИЕ: SUPPORT_BRIDGE_URL не задан — будет использован дефолт из config.py."
    echo "          Если SMB Monitor запущен на другом хосте, добавьте адрес явно."
fi

echo "== 1/6 Текущая ревизия =="
git rev-parse --short HEAD

echo "== 2/6 Забираю код из git =="
# Основной remote может быть недоступен (например, истёк сертификат Redmine),
# поэтому при ошибке пробуем GitHub — иначе сервер останется на старом коде
if ! git pull --ff-only; then
    echo "Не удалось обновить из upstream, пробую origin (GitHub)..."
    BRANCH="$(git branch --show-current)"
    [ -n "$BRANCH" ] || fail "не удалось определить текущую ветку"
    git fetch origin || fail "не удалось получить данные из origin"
    git merge --ff-only "origin/$BRANCH" || fail "обновление не удалось ни из upstream, ни из origin"
fi

echo "== 3/6 Ревизия после обновления =="
git rev-parse --short HEAD

echo "== 4/6 Собираю образ =="
docker compose build $BUILD_ARGS

echo "== 5/6 Пересоздаю контейнер =="
docker compose up -d --force-recreate
docker compose ps

echo "== 6/6 Проверяю готовность API =="
ready=0
for _ in $(seq 1 15); do
    if curl -fsS -m 3 http://127.0.0.1:8010/health >/dev/null 2>&1; then
        ready=1
        break
    fi
    sleep 2
done

if [ "$ready" -ne 1 ]; then
    echo
    echo "ВНИМАНИЕ: API не ответил за 30 секунд. Логи:"
    docker compose logs --tail 40 serverbot
    exit 1
fi

echo
echo "Готово: сервис отвечает."
echo "Проверка каналов (health показывает только живость процесса):"
echo "  docker compose logs --tail 20 | grep -E 'support/message|ConnectError'"
