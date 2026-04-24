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
  Сюда идут вопросы существующего клиента: ЛК (восстановление доступа, обучение),
  перезаключение договора, подключение новых услуг, обратный звонок, отзыв, прочее.
- Передать в КЛО (вопросы по заказам, отследить, дата доставки, изменения в заказе): [SET_STATE:waiting_klo:ТЕМА]
- Передать бухгалтеру (счета, акты сверки, взаиморасчёты): [SET_STATE:waiting_buh:ТЕМА]
- Передать продажнику — ТОЛЬКО для заключения НОВОГО договора (клиент ещё не работает с СДЭК): [SET_STATE:waiting_pro:ТЕМА]

Где ТЕМА — краткое название темы латиницей (например: contract_renewal, order_track, feedback).

КРИТИЧЕСКИ ВАЖНО — ТЫ НЕ ПРОСИШЬ ИНН И КОНТАКТ САМ:
После того как ты поставил тег [SET_STATE:...], бот автоматически САМ спросит у клиента
сначала ИНН/договор, потом (если клиент найден в базе) — контакт. Поэтому в сообщении
с тегом НЕ проси ИНН/договор/телефон/e-mail. Просто скажи коротко: «Хорошо, передам ваш
запрос специалисту» — и ставь тег. Бот всё остальное соберёт сам.

Пример правильного сообщения с тегом:
"Хорошо, я передам ваш запрос менеджеру. [SET_STATE:waiting_message:callback_request]"

Пример НЕПРАВИЛЬНОГО (так делать НЕЛЬЗЯ):
"Укажите ваш ИНН и телефон, я передам менеджеру. [SET_STATE:...]" ← НЕ ПРОСИ ДАННЫЕ САМ.

КОГДА СТАВИТЬ ТЕГ:
Ставь тег как только ты понял, что вопрос требует передачи сотруднику и клиент согласен.
Сразу, одним сообщением — без просьбы прислать ИНН/контакт.

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

        # Сохраняем ответ AI в историю БЕЗ тега SET_STATE — он только
        # смущает модель в следующих вызовах.
        clean_text = re.sub(r'\s*\[SET_STATE:\w+:\w+\]\s*', ' ', ai_text).strip()
        _conversations[user_id].append({"role": "assistant", "content": clean_text})

        log_event("ai_response", trace_id, user_id=user_id,
                  response=ai_text[:300])
        return ai_text

    except Exception as e:
        log_event("ai_error", trace_id, user_id=user_id, error=str(e)[:200])
        return ""


def clear_conversation(user_id: int):
    """Очищает историю диалога пользователя."""
    _conversations.pop(user_id, None)


def append_conversation(user_id: int, role: str, content: str) -> None:
    """Добавляет запись в историю диалога без вызова модели.

    Используется, когда между обычными репликами AI произошёл «побочный»
    обмен (например, клиент прислал ИНН и бот переслал запрос менеджеру)
    и AI нужно сохранить цельный контекст для следующей реплики.
    """
    _conversations[user_id].append({"role": role, "content": content})
    if len(_conversations[user_id]) > MAX_HISTORY:
        _conversations[user_id] = _conversations[user_id][-MAX_HISTORY:]


def _call_classifier(prompt: str, trace_id: str | None = None,
                     event_name: str = "ai_classify") -> dict | None:
    """Универсальный вызов модели с JSON-ответом. None при ошибке."""
    if not settings.OPENROUTER_API_KEY:
        return None
    try:
        resp = requests.post(
            f"{settings.OPENROUTER_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.OPENROUTER_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 80,
                "temperature": 0,
            },
            timeout=10,
        )
        resp.raise_for_status()
        answer = resp.json()["choices"][0]["message"]["content"].strip()
        answer = re.sub(r"```(?:json)?|```", "", answer).strip()
        log_event(event_name, trace_id, answer=answer[:200])
        return json.loads(answer)
    except Exception as e:
        log_event(f"{event_name}_error", trace_id, error=str(e)[:200])
        return None


def classify_ident_stage(text: str, trace_id: str | None = None) -> dict:
    """Фаза идентификации: что клиент прислал в ответ на запрос ИНН/договора.

    Returns:
        {
            "has_identifier": bool,   # в тексте есть ИНН (10/12 цифр) или номер договора
            "category": "physical_person" | "no_identifier" | "normal",
        }

    category:
      - "physical_person" — клиент явно сказал, что он физлицо / у него нет ИП/ООО
        / нет бизнеса / нет договора. Бот отказывает и даёт горячую линию.
      - "no_identifier" — клиент сказал, что ИНН/договора нет или не помнит,
        без явного указания физлица. Бот предлагает «Заключить договор»
        и закрывает диалог.
      - "normal" — либо клиент прислал ИНН/договор, либо просто прислал
        невнятный/пустой текст (бот переспросит).

    При недоступности AI — безопасный дефолт: has_identifier=False, category="normal"
    (бот переспросит, не терминирует диалог ошибочно).
    """
    prompt = (
        "Ты классификатор сообщения клиента, который в ответ на просьбу "
        "указать ИНН или номер договора прислал текст.\n\n"
        "Верни JSON с двумя полями:\n"
        "1) has_identifier (bool):\n"
        "   true ТОЛЬКО если в сообщении есть фактические цифры ИНН "
        "(10 или 12 цифр подряд) ИЛИ номер договора (буквенно-цифровой код "
        "вроде IM-DLP4-215, ИМ91231255297, SZ-LBS2-21, ДЛП-123 и т.п.).\n"
        "   Упоминание слова «ИНН» или «договор» без самих цифр — false.\n\n"
        "2) category: одно из «physical_person» | «no_identifier» | «normal»:\n"
        "   - «physical_person» — клиент явно пишет, что он физлицо, "
        "физическое лицо, у него нет ИП, нет ООО, нет юрлица, нет бизнеса, "
        "не самозанятый, «я обычный человек», «у меня нет договора с вами».\n"
        "   - «no_identifier» — клиент пишет, что ИНН/договора нет, не помнит, "
        "не знает, «не могу найти», БЕЗ явного указания, что он физлицо.\n"
        "   - «normal» — любой другой случай, включая когда клиент прислал "
        "ИНН/договор, или прислал что-то невнятное/не по теме.\n\n"
        f"Сообщение клиента: «{text}»\n\n"
        "Ответь СТРОГО одним JSON без markdown:\n"
        '{"has_identifier": false, "category": "normal"}'
    )
    ai = _call_classifier(prompt, trace_id, event_name="classify_ident")
    if ai is None:
        log_event("classify_ident_fallback", trace_id, user_text=text[:150])
        return {"has_identifier": False, "category": "normal"}
    cat = ai.get("category", "normal")
    if cat not in ("physical_person", "no_identifier", "normal"):
        cat = "normal"
    return {
        "has_identifier": bool(ai.get("has_identifier", False)),
        "category": cat,
    }


_EMAIL_RE = re.compile(r"[\w.+\-]+@[\w\-]+\.[a-zA-Z]{2,}")


def _detect_contact_local(text: str) -> str | None:
    """Локальная детекция контакта без AI.

    Возвращает 'email' | 'phone' | None. Телефон = 7+ цифр после удаления
    всех не-цифр (это покрывает форматы `+7 (999) 123-45-67`, `89991234567`,
    «тел 89991234567» и т.п.). E-mail — стандартный regex.
    """
    if _EMAIL_RE.search(text):
        return "email"
    digits = re.sub(r"\D", "", text)
    if len(digits) >= 7:
        return "phone"
    return None


_REFUSAL_KEYWORDS = (
    "не хочу", "не дам", "не дадим", "не буду", "не укажу",
    "нет телефона", "нет номера", "нет почты", "нет e-mail", "нет емейла",
    "зачем вам", "зачем это", "никакого номера", "ничего не дам",
    "почта не нужна", "без этого", "не надо", "без контакт",
)


def _detect_refusal_local(text: str) -> bool:
    """Детекция явного отказа от контакта по ключевым фразам."""
    t = text.lower()
    return any(kw in t for kw in _REFUSAL_KEYWORDS)


def classify_contact_stage(text: str, trace_id: str | None = None) -> dict:
    """Фаза контакта: прислал ли клиент телефон/e-mail или отказался.

    Returns:
        {
            "has_contact": bool,      # в тексте есть номер телефона или e-mail
            "refuses_contact": bool,  # клиент явно отказался давать контакт
        }

    Стратегия:
      1. Сначала локально проверяем контакт (regex) — быстро, без сети,
         устойчиво к таймаутам OpenRouter. Если контакт найден — сразу True.
      2. Если локально контакта нет — просим AI определить, отказ это
         или просто не по теме. При недоступности AI — падаем к
         локальной детекции отказа по ключевым словам.
    """
    kind = _detect_contact_local(text)
    if kind:
        log_event("classify_contact_local_hit", trace_id,
                  kind=kind, user_text=text[:100])
        return {"has_contact": True, "refuses_contact": False}

    prompt = (
        "Ты классификатор сообщения клиента, которого только что попросили "
        "прислать контактный телефон или e-mail. В сообщении ТОЧНО нет "
        "ни телефона, ни e-mail (это уже проверено). Нужно понять — "
        "клиент ОТКАЗЫВАЕТСЯ давать контакт или просто написал что-то не по теме.\n\n"
        "Верни JSON с одним полем:\n"
        "refuses_contact (bool):\n"
        "   true если клиент явно отказался: «нет телефона», «не хочу давать», "
        "«не дам», «зачем вам», «никакого номера», «ничего не дам», "
        "«почта не нужна», «давайте без этого».\n"
        "   false если клиент просто написал что-то не по теме без явного отказа.\n\n"
        f"Сообщение клиента: «{text}»\n\n"
        "Ответь СТРОГО одним JSON без markdown:\n"
        '{"refuses_contact": false}'
    )
    ai = _call_classifier(prompt, trace_id, event_name="classify_contact")
    if ai is None:
        refused = _detect_refusal_local(text)
        log_event("classify_contact_fallback", trace_id,
                  user_text=text[:150], local_refused=refused)
        return {"has_contact": False, "refuses_contact": refused}
    return {
        "has_contact": False,  # локальная проверка выше вернула False
        "refuses_contact": bool(ai.get("refuses_contact", False)),
    }


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
