"""Пересылка сообщений менеджерам и обратно клиентам."""

from app import settings
from app.logger import log_event
from app.max_client import send_message, send_message_to_chat
from app.inn_parser import extract_data
from app.klo_rotation import get_klo_user_id
from app.nodes.packaging_paid import btn_cb, keyboard
from app.sheets_clients import find_client_by_inn, find_client_by_contract, find_manager_id
from app.sheets_phones import get_phone
from app.sheets_messages import save_message_map
from app.sheets_logs import log_request


def _manager_actions(client_user_id: int) -> list:
    """Клавиатура «Взял в работу / Решено» под карточкой менеджера."""
    return keyboard([
        [btn_cb("✅ Взял в работу", f"mgr_ack:{client_user_id}")],
        [btn_cb("✔️ Решено", f"mgr_done:{client_user_id}")],
    ])

# Человекочитаемые названия тем
TOPIC_LABELS = {
    # Заказы
    "category_order": "Вопрос по заказу",
    "order_track": "Отследить заказ",
    "track_order": "Отследить заказ",        # частая «перевёрнутая» вариация от ИИ
    "order_date": "Назначить дату доставки",
    "order_edit": "Внести изменения в заказ",
    "order_other": "Другой вопрос по заказу",
    # Создание заказа
    "create_order_rf": "Создать заказ (РФ)",
    "create_order_international": "Создать заказ (международный)",
    "request_klo": "Создать заказ (РФ) — данные",
    "need_help_with_contact": "Создать заказ (международный) — данные",
    # ЛК
    "category_lk": "Личный кабинет",
    "lk_restore": "Восстановить доступ ЛК",
    "lk_training": "Обучение ЛК",
    "remem_gmail": "Восстановление ЛК — не помнит почту",
    "need_help_manager": "Обучение ЛК — помощь менеджера",
    # Финансы
    "category_finance": "Взаиморасчёты",
    "finance_act": "Акт сверки",
    "finance_invoice": "Получить счёт",
    "finance_question": "Вопрос по счёту",
    "need_help_with_period": "Акт сверки — период",
    # Упаковка
    "category_packaging": "Упаковка",
    "packaging_paid": "Платная упаковка",
    "packaging_free": "Бесплатная упаковка",
    "free_pckaiging_data": "Бесплатная упаковка — данные",
    "checkout": "Оформление заказа упаковки",
    # Общее
    "contract": "Заключить договор",
    "contract_renewal": "Перезаключить договор",
    "callback_request": "Обратный звонок",
    "new_services": "Подключить услуги",
    "feedback": "Отзыв",
    # Устаревшие — оставляем как fallback, чтобы не уходило сырой латиницей
    "need_help": "Нужна помощь",
    "need_help_with_order": "Помощь с заказом",
    "need_help_cheking": "Дата доставки — помощь",
    "tracking_solved_no": "Отследить заказ",
    "tracking_help_yes": "Помощь с трекингом",
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
                            text: str, phone: str | None,
                            counterparty: str | None = None) -> str:
    """Форматирует сообщение для менеджера.

    Если clients-таблица нашла контрагента по ИНН/договору — добавляем
    строку «Контрагент», чтобы менеджер сразу понимал, с кем работать.
    """
    source = TOPIC_LABELS.get(topic, topic or "Неизвестно")
    phone_str = f"+{phone}" if phone else "не указан"

    lines = [
        "📩 **Новый запрос от клиента**",
        "",
        f"📌 Источник: {source}",
    ]
    if counterparty:
        lines.append(f"🏢 Контрагент: {counterparty}")
    lines.extend([
        f"👤 Клиент: {user_name}",
        f"🆔 ID: {user_id}",
        f"📞 Телефон: {phone_str}",
        "",
        f"💬 Сообщение:\n{text}",
    ])
    return "\n".join(lines)


def _lookup_client(text: str) -> dict | None:
    """Пробует найти клиента в таблице клиентов по ИНН или номеру договора
    из произвольного текста. Возвращает словарь клиента либо None."""
    parsed = extract_data(text)
    inn = parsed.get("inn")
    contract = parsed.get("contract")

    client = None
    if inn:
        try:
            client = find_client_by_inn(inn)
        except Exception:
            client = None
    if not client and contract:
        try:
            client = find_client_by_contract(contract)
        except Exception:
            client = None
    return client


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

    client = _lookup_client(text)
    counterparty = (client or {}).get("name") or None
    manager_name = (client or {}).get("manager_name") or ""

    msg_text = _format_manager_message(user_id, user_name, topic, text,
                                        phone, counterparty=counterparty)
    payload = {"text": msg_text, "format": "markdown",
               "attachments": _manager_actions(user_id)}

    manager_max_id = None
    lookup_error = ""
    if client and manager_name:
        try:
            manager_max_id = find_manager_id(manager_name)
        except Exception as e:
            lookup_error = str(e)[:200]

    # Детальная диагностика: ровно где потеряли маршрут
    log_event("manager_resolve", trace_id,
              user_id=user_id,
              client_found=bool(client),
              counterparty=counterparty or "",
              manager_name=manager_name,
              manager_max_id=manager_max_id,
              lookup_error=lookup_error)

    result = "no_manager"
    if manager_max_id:
        resp = send_message(manager_max_id, payload, trace_id)
        msg_id, manager_chat_id = _parse_response(resp)
        if msg_id:
            save_message_map(str(msg_id), user_id,
                             manager_chat_id=str(manager_chat_id))
        result = "forwarded"
    else:
        # Подробная причина — пригодится в лог-группе и в логах.
        if not client:
            reason = "клиент не найден в таблице по ИНН/договору"
        elif not manager_name:
            reason = f"у клиента «{counterparty}» не указан менеджер продаж"
        elif lookup_error:
            reason = f"ошибка поиска MAX ID менеджера «{manager_name}»: {lookup_error}"
        else:
            reason = f"в таблице менеджеров нет MAX ID для «{manager_name}»"
        if _fallback_to_group(user_id, payload, reason, trace_id):
            result = "forwarded_group"
        else:
            log_event("forward_to_manager_lost", trace_id,
                      user_id=user_id, topic=topic)

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

    counterparty = (_lookup_client(text) or {}).get("name") or None
    msg_text = _format_manager_message(user_id, user_name, topic, text,
                                        phone, counterparty=counterparty)
    payload = {"text": msg_text, "format": "markdown",
               "attachments": _manager_actions(user_id)}

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

    counterparty = (_lookup_client(text) or {}).get("name") or None
    msg_text = _format_manager_message(user_id, user_name, topic, text,
                                        phone, counterparty=counterparty)
    payload = {"text": msg_text, "format": "markdown",
               "attachments": _manager_actions(user_id)}

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

    counterparty = (_lookup_client(text) or {}).get("name") or None
    msg_text = _format_manager_message(user_id, user_name, topic, text,
                                        phone, counterparty=counterparty)
    payload = {"text": msg_text, "format": "markdown",
               "attachments": _manager_actions(user_id)}

    if settings.SALES_USER_ID:
        resp = send_message(settings.SALES_USER_ID, payload, trace_id)
        msg_id, sales_chat_id = _parse_response(resp)
        if msg_id:
            save_message_map(str(msg_id), user_id,
                             manager_chat_id=str(sales_chat_id))
        log_event("forwarded_to_sales", trace_id, user_id=user_id)
    else:
        _fallback_to_group(user_id, payload, "продажник не настроен", trace_id)


def forward_new_client_to_group(user_id: int, user_name: str, text: str,
                                 topic: str, trace_id: str | None = None) -> bool:
    """Клиент подтвердил ИНН/договор (повторил то же значение), но его нет
    в базе — возможно, это новый клиент, которого ещё не внесли. Уводим
    запрос в резервную группу, чтобы дежурные разобрались.

    Возвращает True, если группа настроена и сообщение ушло.
    """
    phone = None
    try:
        phone = get_phone(user_id)
    except Exception:
        pass

    msg_text = _format_manager_message(user_id, user_name, topic, text, phone)
    payload = {"text": msg_text, "format": "markdown",
               "attachments": _manager_actions(user_id)}

    reason = "ИНН/договор подтверждён клиентом, но в базе не найден (возможно новый клиент)"
    sent = _fallback_to_group(user_id, payload, reason, trace_id)
    if not sent:
        log_event("new_client_not_sent", trace_id, user_id=user_id, topic=topic)

    try:
        log_request(user_id, topic,
                    result="new_client_group" if sent else "new_client_lost",
                    comment=text[:200])
    except Exception:
        pass
    return sent


def forward_manager_reply_to_client(client_user_id: int, manager_text: str,
                                    trace_id: str | None = None):
    """Пересылает ответ менеджера клиенту."""
    payload = {
        "text": f"💬 **Ответ от менеджера:**\n\n{manager_text}",
        "format": "markdown",
    }
    send_message(client_user_id, payload, trace_id)
    log_event("manager_reply_forwarded", trace_id, client_user_id=client_user_id)
