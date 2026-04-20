"""Пересылка сообщений менеджерам и обратно клиентам."""

from app import settings
from app.logger import log_event
from app.max_client import send_message, send_message_to_chat
from app.inn_parser import extract_data
from app.klo_rotation import get_klo_user_id
from app.sheets_clients import find_client_by_inn, find_client_by_contract, find_manager_id
from app.sheets_phones import get_phone
from app.sheets_messages import save_message_map
from app.sheets_logs import log_request

# Человекочитаемые названия тем
TOPIC_LABELS = {
    "category_order": "Вопрос по заказу",
    "order_track": "Отследить заказ",
    "order_date": "Назначить дату доставки",
    "order_edit": "Внести изменения в заказ",
    "order_other": "Другой вопрос по заказу",
    "category_lk": "Личный кабинет",
    "lk_restore": "Восстановить доступ ЛК",
    "lk_training": "Обучение ЛК",
    "category_finance": "Взаиморасчёты",
    "finance_act": "Акт сверки",
    "finance_invoice": "Получить счет",
    "finance_question": "Вопрос по счету",
    "category_packaging": "Упаковка",
    "packaging_paid": "Платная упаковка",
    "packaging_free": "Бесплатная упаковка",
    "free_pckaiging_data": "Бесплатная упаковка (данные)",
    "contract": "Заключить договор",
    "contract_renewal": "Перезаключить договор",
    "callback_request": "Обратный звонок",
    "new_services": "Подключить услуги",
    "feedback": "Отзыв",
    "need_help": "Нужна помощь",
    "need_help_with_contact": "Помощь (контакт)",
    "need_help_with_period": "Помощь (период)",
    "need_help_with_order": "Помощь (заказ)",
    "need_help_cheking": "Дата доставки — помощь",
    "need_help_manager": "Помощь менеджера",
    "tracking_solved_no": "Трекинг не решён",
    "tracking_help_yes": "Помощь с трекингом",
    "remem_gmail": "Не помнит почту",
    "request_klo": "Запрос в КЛО",
    "checkout": "Оформление заказа упаковки",
}


def _parse_response(resp):
    """Извлекает msg_id и chat_id из ответа MAX API."""
    msg_id = ""
    chat_id = ""
    try:
        data = resp.json() if hasattr(resp, "json") else resp
        msg = data.get("message", {})
        msg_id = msg.get("body", {}).get("mid") or \
                 msg.get("mid") or \
                 data.get("mid") or data.get("id") or ""
        chat_id = msg.get("recipient", {}).get("chat_id", "")
    except:
        pass
    return msg_id, chat_id


def _format_manager_message(user_id: int, user_name: str, topic: str,
                            text: str, phone: str | None) -> str:
    """Форматирует сообщение для менеджера."""
    source = TOPIC_LABELS.get(topic, topic or "Неизвестно")
    phone_str = f"+{phone}" if phone else "не указан"

    return (
        f"📩 **Новый запрос от клиента**\n\n"
        f"📌 Источник: {source}\n"
        f"👤 Клиент: {user_name}\n"
        f"🆔 ID: {user_id}\n"
        f"📞 Телефон: {phone_str}\n\n"
        f"💬 Сообщение:\n{text}"
    )


def _fallback_to_group(user_id: int, payload: dict, reason: str,
                        trace_id: str | None = None) -> bool:
    """Отправляет payload в резервную группу (GENERAL_CHAT_ID) с пометкой причины.

    Возвращает True, если группа настроена и сообщение ушло.
    """
    chat_id = settings.GENERAL_CHAT_ID
    if not chat_id:
        log_event("fallback_group_not_configured", trace_id,
                  user_id=user_id, reason=reason)
        return False

    # Добавляем причину попадания в резерв — чтобы операторы в группе
    # понимали, почему запрос пришёл сюда, а не менеджеру.
    group_payload = dict(payload)
    prefix = f"⚠️ *Резервный канал — {reason}*\n\n"
    group_payload["text"] = prefix + payload.get("text", "")

    resp = send_message_to_chat(chat_id, group_payload, trace_id)
    msg_id, _ = _parse_response(resp)
    if msg_id:
        save_message_map(str(msg_id), user_id, manager_chat_id=str(chat_id))
    log_event("forwarded_to_group", trace_id,
              chat_id=chat_id, user_id=user_id, reason=reason)
    return True


def forward_to_manager(user_id: int, user_name: str, text: str,
                       topic: str, trace_id: str | None = None):
    """Основная логика пересылки — ищет менеджера по ИНН/договору, пересылает."""
    phone = None
    try:
        phone = get_phone(user_id)
    except Exception:
        pass

    msg_text = _format_manager_message(user_id, user_name, topic, text, phone)
    payload = {"text": msg_text, "format": "markdown"}

    # Парсим ИНН/договор из текста
    parsed = extract_data(text)
    inn = parsed.get("inn")
    contract = parsed.get("contract")

    # Ищем клиента и его менеджера
    client = None
    if inn:
        try:
            client = find_client_by_inn(inn)
        except Exception:
            pass
    if not client and contract:
        try:
            client = find_client_by_contract(contract)
        except Exception:
            pass

    manager_max_id = None
    if client and client.get("manager_name"):
        try:
            manager_max_id = find_manager_id(client["manager_name"])
        except Exception:
            pass

    result = "no_manager"
    if manager_max_id:
        resp = send_message(manager_max_id, payload, trace_id)
        # Сохраняем связку для ответа менеджера
        msg_id, manager_chat_id = _parse_response(resp)
        if msg_id:
            save_message_map(str(msg_id), user_id,
                             manager_chat_id=str(manager_chat_id))
        result = "forwarded"
    else:
        # Менеджер не найден (нет клиента в таблице или не указан) — уводим
        # запрос в резервную группу, чтобы он не потерялся.
        reason = "менеджер не найден по ИНН/договору"
        if _fallback_to_group(user_id, payload, reason, trace_id):
            result = "forwarded_group"
        else:
            log_event("forward_to_manager_lost", trace_id,
                      user_id=user_id, topic=topic,
                      inn=inn, contract=contract)

    # Логируем
    try:
        log_request(user_id, topic, result=result, comment=text[:200])
    except Exception:
        pass


def forward_to_klo(user_id: int, user_name: str, text: str,
                   topic: str, trace_id: str | None = None):
    """Пересылает запрос в КЛО (отдел работы с клиентами)."""
    phone = None
    try:
        phone = get_phone(user_id)
    except Exception:
        pass

    msg_text = _format_manager_message(user_id, user_name, topic, text, phone)
    payload = {"text": msg_text, "format": "markdown"}

    klo_id = get_klo_user_id()
    result = "no_klo"
    if klo_id:
        resp = send_message(klo_id, payload, trace_id)
        msg_id, klo_chat_id = _parse_response(resp)
        if msg_id:
            save_message_map(str(msg_id), user_id,
                             manager_chat_id=str(klo_chat_id))
        result = "forwarded_klo"
        log_event("forwarded_to_klo", trace_id, klo_id=klo_id, user_id=user_id)
    else:
        if _fallback_to_group(user_id, payload, "КЛО не настроен", trace_id):
            result = "forwarded_group"

    try:
        log_request(user_id, topic, result=result, comment=text[:200])
    except Exception:
        pass


def forward_to_accountant(user_id: int, user_name: str, text: str,
                          topic: str, trace_id: str | None = None):
    """Пересылает запрос бухгалтеру (обоим)."""
    phone = None
    try:
        phone = get_phone(user_id)
    except Exception:
        pass

    msg_text = _format_manager_message(user_id, user_name, topic, text, phone)
    payload = {"text": msg_text, "format": "markdown"}

    sent_any = False
    for acc_id in (settings.ACCOUNTANT_USER_ID, settings.ACCOUNTANT2_USER_ID):
        if acc_id:
            resp = send_message(acc_id, payload, trace_id)
            msg_id, acc_chat_id = _parse_response(resp)
            if msg_id:
                save_message_map(str(msg_id), user_id,
                                 manager_chat_id=str(acc_chat_id))
            sent_any = True
    if sent_any:
        log_event("forwarded_to_accountant", trace_id, user_id=user_id)
    else:
        _fallback_to_group(user_id, payload, "бухгалтер не настроен", trace_id)


def forward_to_sales(user_id: int, user_name: str, text: str,
                     topic: str, trace_id: str | None = None):
    """Пересылает запрос продажнику."""
    phone = None
    try:
        phone = get_phone(user_id)
    except Exception:
        pass

    msg_text = _format_manager_message(user_id, user_name, topic, text, phone)
    payload = {"text": msg_text, "format": "markdown"}

    if settings.SALES_USER_ID:
        resp = send_message(settings.SALES_USER_ID, payload, trace_id)
        msg_id, sales_chat_id = _parse_response(resp)
        if msg_id:
            save_message_map(str(msg_id), user_id,
                             manager_chat_id=str(sales_chat_id))
        log_event("forwarded_to_sales", trace_id, user_id=user_id)
    else:
        _fallback_to_group(user_id, payload, "продажник не настроен", trace_id)


def forward_manager_reply_to_client(client_user_id: int, manager_text: str,
                                    trace_id: str | None = None):
    """Пересылает ответ менеджера клиенту."""
    payload = {
        "text": f"💬 **Ответ от менеджера:**\n\n{manager_text}",
        "format": "markdown",
    }
    send_message(client_user_id, payload, trace_id)
    log_event("manager_reply_forwarded", trace_id, client_user_id=client_user_id)
