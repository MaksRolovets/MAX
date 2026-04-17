"""Модуль AI-помощника через OpenRouter API."""

import json
import os
import re
import requests
from collections import defaultdict

from app import settings
from app.logger import log_event

# Загружаем системный промпт из файла
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PROMPT_PATH = os.path.join(_BASE_DIR, "prompt")

_system_prompt = ""
if os.path.exists(_PROMPT_PATH):
    with open(_PROMPT_PATH, "r", encoding="utf-8") as f:
        _system_prompt = f.read().strip()

# Дополнение к промпту — инструкция для AI по управлению состояниями бота
_STATE_INSTRUCTION = """

ВАЖНО — УПРАВЛЕНИЕ БОТОМ:
Когда ты решаешь, что нужно передать запрос менеджеру/сотруднику, ты ДОЛЖЕН добавить
в КОНЕЦ своего ответа специальный тег (клиент его не увидит):

- Передать закреплённому менеджеру (по ИНН/договору): [SET_STATE:waiting_message:ТЕМА]
- Передать в КЛО (вопросы по заказам, отследить, дата доставки): [SET_STATE:waiting_klo:ТЕМА]
- Передать бухгалтеру (счета, акты сверки, взаиморасчёты): [SET_STATE:waiting_buh:ТЕМА]
- Передать продажнику (договор, новые услуги, ЛК): [SET_STATE:waiting_pro:ТЕМА]

Где ТЕМА — краткое название темы латиницей (например: contract_renewal, order_track, feedback).

КОГДА СТАВИТЬ ТЕГ:
Ставь тег ТОЛЬКО когда ты ПРОСИШЬ клиента указать данные (ИНН, договор, номер заказа и т.д.),
которые будут переданы сотруднику. Следующее сообщение клиента после тега будет автоматически
переслано нужному сотруднику.

Пример — ты ещё НЕ собрал данные:
"Хорошо, я передам ваш запрос менеджеру. Пожалуйста, укажите ваш ИНН или номер договора одним сообщением. [SET_STATE:waiting_message:callback_request]"

КОГДА НЕ СТАВИТЬ ТЕГ:
- Если ты просто отвечаешь на вопрос или ведёшь диалог — НЕ ставь тег.
- Если ты прощаешься или спрашиваешь «чем ещё помочь?» — НЕ ставь тег.
- Если клиент говорит «спасибо», «нет вопросов», «всё» — попрощайся тепло, БЕЗ тега.

ВАЖНО: После того как запрос передан, бот автоматически вернёт клиента к тебе.
Спроси «Чем ещё могу помочь?». Если клиент говорит что вопросов нет — попрощайся:
«Рада была помочь! Ожидайте звонка от менеджера. До свидания!»
"""

# История диалогов: user_id → список сообщений
_conversations: dict[int, list[dict]] = defaultdict(list)

# Максимум сообщений в истории на пользователя
MAX_HISTORY = 20


def _get_system_prompt() -> str:
    return _system_prompt + _STATE_INSTRUCTION


def ask_ai(user_id: int, text: str, trace_id: str | None = None) -> str:
    """Отправляет сообщение пользователя в AI и возвращает ответ."""
    if not settings.OPENROUTER_API_KEY:
        log_event("ai_skip", trace_id, reason="no_api_key")
        return ""

    # Добавляем сообщение пользователя в историю
    _conversations[user_id].append({"role": "user", "content": text})

    # Обрезаем историю
    if len(_conversations[user_id]) > MAX_HISTORY:
        _conversations[user_id] = _conversations[user_id][-MAX_HISTORY:]

    messages = [
        {"role": "system", "content": _get_system_prompt()},
        *_conversations[user_id],
    ]

    try:
        log_event("ai_request", trace_id, user_id=user_id, model=settings.OPENROUTER_MODEL)
        resp = requests.post(
            f"{settings.OPENROUTER_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.OPENROUTER_MODEL,
                "messages": messages,
                "max_tokens": 1024,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        ai_text = data["choices"][0]["message"]["content"].strip()

        # Сохраняем ответ AI в историю
        _conversations[user_id].append({"role": "assistant", "content": ai_text})

        log_event("ai_response", trace_id, user_id=user_id,
                  response=ai_text[:300])
        return ai_text

    except Exception as e:
        log_event("ai_error", trace_id, user_id=user_id, error=str(e)[:200])
        return ""


def clear_conversation(user_id: int):
    """Очищает историю диалога пользователя."""
    _conversations.pop(user_id, None)


def validate_client_data(text: str, trace_id: str | None = None) -> dict:
    """AI-анализатор сообщения клиента: есть ли ИНН/договор и контактный телефон/e-mail.

    Returns:
        {
            "has_identifier": bool,   # ИНН или номер договора
            "has_contact": bool,      # телефон или e-mail
            "missing": list[str],     # "identifier" и/или "contact"
        }

    Если AI недоступен — считаем данные валидными (пересылаем сотруднику),
    чтобы не блокировать клиентов при сбое нейронки.
    """
    ai = _ai_validate(text, trace_id) if settings.OPENROUTER_API_KEY else None

    if ai is None:
        log_event("validate_client_data_fallback", trace_id, user_text=text[:150])
        return {"has_identifier": True, "has_contact": True, "missing": []}

    has_identifier = bool(ai.get("has_identifier", False))
    has_contact = bool(ai.get("has_contact", False))

    missing: list[str] = []
    if not has_identifier:
        missing.append("identifier")
    if not has_contact:
        missing.append("contact")

    return {
        "has_identifier": has_identifier,
        "has_contact": has_contact,
        "missing": missing,
    }


def _ai_validate(text: str, trace_id: str | None = None) -> dict | None:
    """AI-валидатор: просим модель вернуть JSON с двумя булевыми флагами."""
    try:
        resp = requests.post(
            f"{settings.OPENROUTER_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.OPENROUTER_MODEL,
                "messages": [{
                    "role": "user",
                    "content": (
                        "Проанализируй сообщение клиента службы поддержки.\n\n"
                        "Определи две вещи:\n"
                        "• has_identifier — true, если клиент указал ИНН "
                        "(10 или 12 цифр) или номер договора (цифры или "
                        "буквенно-цифровой код). false, если отказывается "
                        "(\"не помню\", \"нет ИНН\") или данных нет.\n"
                        "• has_contact — true, если указан контактный телефон "
                        "или e-mail. false иначе.\n\n"
                        f"Сообщение клиента: «{text}»\n\n"
                        "Ответь СТРОГО одним JSON без пояснений:\n"
                        '{"has_identifier": true, "has_contact": false}'
                    ),
                }],
                "max_tokens": 60,
                "temperature": 0,
            },
            timeout=10,
        )
        resp.raise_for_status()
        answer = resp.json()["choices"][0]["message"]["content"].strip()
        log_event("validate_client_data_ai", trace_id, answer=answer[:150])
        answer = re.sub(r"```(?:json)?|```", "", answer).strip()
        data = json.loads(answer)
        return {
            "has_identifier": bool(data.get("has_identifier", False)),
            "has_contact": bool(data.get("has_contact", False)),
        }
    except Exception as e:
        log_event("validate_client_data_ai_error", trace_id, error=str(e)[:200])
        return None


def parse_state_command(ai_response: str) -> tuple[str, str | None, str | None]:
    """Парсит ответ AI: извлекает тег SET_STATE и возвращает (чистый текст, state, topic).

    Возвращает:
        (clean_text, state, topic) — если тег найден
        (original_text, None, None) — если тега нет
    """
    import re
    match = re.search(r'\[SET_STATE:(\w+):(\w+)\]', ai_response)
    if match:
        state = match.group(1)
        topic = match.group(2)
        clean = ai_response[:match.start()].rstrip()
        return clean, state, topic
    return ai_response, None, None
