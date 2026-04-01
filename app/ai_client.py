"""Модуль AI-помощника через OpenRouter API."""

import os
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

Пример ответа, когда нужно собрать ИНН и передать менеджеру:
"Хорошо, я передам ваш запрос закреплённому менеджеру. Пожалуйста, укажите ваш ИНН или номер договора одним сообщением. [SET_STATE:waiting_message:callback_request]"

НЕ ставь тег, если ты просто отвечаешь на вопрос клиента или ведёшь диалог.
Ставь тег ТОЛЬКО когда ты готов попросить клиента указать ИНН/договор/данные для передачи сотруднику.
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
