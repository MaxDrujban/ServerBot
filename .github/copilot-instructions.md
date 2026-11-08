# Правила проекта ServerBot

## Единый стиль кода

Один и тот же приём оформляется во всём проекте одинаково. Смешивать два варианта записи в одном файле нельзя.

### Аннотации типов

Целевой стиль — современный синтаксис Python 3.12 (PEP 585 и PEP 604):

```python
def extract_incoming_message(update: dict[str, Any]) -> dict[str, Any] | None: ...
def send_message(self, user_id: int | str | None = None) -> dict[str, Any]: ...
def send_bulk_messages(self, chat_ids: list[int | str], text: str) -> list[Any]: ...
def parse_external_user(external_user: str) -> tuple[str, dict[str, int]]: ...
```

Правила:

- встроенные generic-типы вместо модуля `typing`: `dict`, `list`, `tuple`, `set` — не `Dict`, `List`, `Tuple`, `Set`;
- `X | None` вместо `Optional[X]`;
- `A | B` вместо `Union[A, B]`;
- из `typing` допустим только `Any` — у него нет встроенного аналога.

Новый код пишется сразу в этом стиле. Файлы со старым стилем (`Optional`, `Dict`, `List`, `Union` из `typing`) приводятся к целевому при любой правке рядом, отдельным массовым рефакторингом — по отдельной договорённости.

Файлы, которые ещё предстоит привести к целевому стилю:

- `services/max_service.py`
- `services/telegram_service.py`
- `services/support_service.py`
- `services/ai_service.py`
- `models/message.py`

### Логирование

- Никаких рутинных `INFO`-записей на каждый запрос, событие или шаг обработки: «получено», «обработано», «запущено», «остановлено».
- `WARNING` и `ERROR` — только для того, что требует внимания: сбои отправки, повторы, неудачная регистрация webhook.
- Текст сообщений пользователей в лог не пишем: это персональные данные.
- Секреты и токены не должны попадать в лог, включая полные URL с токеном в пути.
