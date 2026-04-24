"""Главный маршрутизатор обновлений — вся логика бота."""

import os
import re

from app.logger import log_event
from app.max_client import (
    send_message, answer_callback, upload_local_file, send_message_with_file,
    send_message_to_chat,
)
from app.nodes import packaging_paid
from app import settings
from app.sheets_states import set_state, get_state, clear_state
from app.sheets_messages import find_client_by_message
from app.sheets_phones import has_phone, save_phone
from app.forwarding import (
    forward_to_manager, forward_to_klo, forward_to_accountant,
    forward_to_sales, forward_manager_reply_to_client,
    forward_new_client_to_group,
)
from app.sheets_clients import (
    update_manager_for_clients, update_manager_id,
    find_client_by_inn, find_client_by_contract,
)
from app.ai_client import (
    ask_ai, parse_state_command, clear_conversation,
    classify_ident_stage, classify_contact_stage, append_conversation,
)
from app.inn_parser import extract_data
from app.klo_rotation import is_weekend

# ─── Текстовые константы промптов (обновлено по скриншоту + новые правки) ────────────────────────────────

TEXT_REQUEST_UNIVERSAL = "📝 Укажите в сообщении номер Вашего ИНН или договора, контактный телефон или e-mail по которому мы сможем с Вами связаться, а также интересующий вопрос.\nМы передадим Ваш запрос менеджеру."
TEXT_TRACKING_NO = (
    "📝 Для ускорения решения — напишите, пожалуйста, одним сообщением:\n"
    "• Ваш ИНН или номер договора\n"
    "• Телефон или e-mail (как нам с вами связаться)\n"
    "• Номер заказа (чтобы мы могли уточнить информацию)\n\n"
    "🔄 Мы передадим запрос специалисту, и он свяжется с вами совсем скоро. Спасибо!"
)
TEXT_CALLBACK_REQUEST = (
    "📞 Обратный звонок\n\n"
    "Напишите, пожалуйста, в одном сообщении:\n"
    "• ИНН или номер договора\n"
    "• Телефон или e‑mail для связи\n"
    "• Ваш вопрос или проблему (подробности приветствуются)\n\n"
    "✅ Мы передадим информацию специалисту."
)
TEXT_FEEDBACK = "⭐ **Оставить отзыв**\n\nУкажите в сообщении номер Вашего ИНН или договора, контактный телефон или e-mail по которому мы сможем с Вами связаться, и напишите отзыв. Мы передадим информацию менеджеру."
TEXT_CONTRACT_RENEWAL = (
    "📝 **Перезаключить договор**\n\n"
    "Напишите в одном сообщении:\n"
    "• Ваш ИНН или номер договора\n"
    "• Телефон или e‑mail для связи\n\n"
    "✅ Мы передадим запрос специалисту."
)
TEXT_NEW_SERVICES = (
    "✨ **Подключить услуги**\n\n"
    "Напишите, пожалуйста, в одном сообщении:\n"
    "• Ваш ИНН или номер договора\n"
    "• Телефон или e‑mail для связи\n"
    "• Какие услуги нужны\n\n"
    "✅ Мы отправим Ваш запрос специалисту."
)
TEXT_FREE_BOX_MENU = (
    "🆓 **Бесплатная упаковка**\n\n"
    "Чтобы получить бесплатную упаковку, нажмите кнопку «Указать данные» — "
    "и мы передадим ваш запрос менеджеру."
)
TEXT_FREE_BOX = (
    "🆓 **Бесплатная упаковка**\n\n"
    "Напишите, пожалуйста, в одном сообщении:\n"
    "• ИНН или номер договора\n"
    "• Телефон или e‑mail для связи\n"
    "• Какой тип упаковки и в каком количестве нужен\n\n"
    "✅ Мы передадим запрос менеджеру."
)
TEXT_REQUEST_ORDER_AND_INN = (
    "📝 Пожалуйста, напишите в одном сообщении:\n"
    "• Ваш ИНН или номер договора\n"
    "• Телефон или e-mail для связи\n"
    "• Номер заказа\n\n"
    "✅ Мы передадим ваш запрос специалисту, и он скоро свяжется с вами."
)
TEXT_REQUEST_KLO = (
    "📝 Напишите, пожалуйста, в одном сообщении:\n"
    "• Ваш ИНН или номер договора\n"
    "• Телефон или e-mail для связи\n"
    "• Что именно нужно сделать (подробности приветствуются)\n\n"
    "✅ После этого мы сразу передадим ваш запрос специалисту. Он свяжется с вами и поможет разобраться."
)
TEXT_ORDER_OTHER = (
    "❓ **Другой вопрос по заказу**\n\n"
    "Пожалуйста, напишите нам в одном сообщении:\n\n"
    "– ИНН или номер договора\n"
    "– Телефон или e-mail для связи\n"
    "– Номер заказа\n"
    "– Суть вопроса (подробности приветствуются)\n\n"
    "📨 Передадим ваш запрос специалисту. Обычно ответ приходит в течение часа."
)
TEXT_INTERNATIONAL_MENU = (
    "🌍 **ЕАЭС или международная отправка**\n\n"
    "Для оформления заказа нажмите кнопку «Указать данные» — "
    "и мы передадим ваш запрос специалисту."
)
TEXT_INTERNATIONAL = (
    "🌍 **ЕАЭС или международная отправка**\n\n"
    "Напишите, пожалуйста, в одном сообщении:\n"
    "• ИНН или номер договора\n"
    "• Телефон или e‑mail для связи\n"
    "• Маршрут, краткие параметры и тип груза\n\n"
    "✅ Мы передадим запрос специалисту."
)
TEXT_FINANCE_INVOICE = (
    "💳 **Получить счет**\n\n"
    "Напишите, пожалуйста, в одном сообщении:\n"
    "• ИНН или номер договора\n"
    "• Телефон или e‑mail для связи\n\n"
    "🔄 После этого мы передадим ваш запрос специалисту."
)
TEXT_FINANCE_QUESTION = (
    "❓ **Вопрос по счету**\n\n"
    "Напишите, пожалуйста, в одном сообщении:\n"
    "• ИНН или номер договора\n"
    "• Телефон или e‑mail для связи\n"
    "• Номер счёта\n"
    "• Ваш вопрос\n\n"
    "✅ Мы передадим всё специалисту."
)
TEXT_FINANCE_PERIOD = (
    "📝 Напишите, пожалуйста, в одном сообщении:\n"
    "• Ваш ИНН или номер договора\n"
    "• Телефон или e‑mail для связи\n"
    "• Период (например, 01.01.2025 – 31.01.2025)\n\n"
    "✅ После этого мы передадим ваш запрос менеджеру."
)

TEXT_NEED_HELP_DATE_DELIVERY = (
    "📝 Пожалуйста, напишите всё одним сообщением:\n"
    "• Ваш ИНН или номер договора\n"
    "• Контактный телефон или e-mail\n"
    "• Номер заказа — это поможет нам быстрее разобраться в ситуации\n\n"
    "🔄 Мы передадим ваш запрос специалисту, и он скоро свяжется с вами."
)

TEXT_CONFIRM_FORWARD_MANAGER = "✅ Ваш запрос будет передан менеджеру и с Вами скоро свяжутся!"
TEXT_CONTRACT = (
    "📄 **Заключить договор**\n\n"
    "Напишите, пожалуйста, в одном сообщении:\n"
    "• Название организации\n"
    "• ИНН\n"
    "• Сайт (при наличии)\n"
    "• Телефон\n\n"
    "✅ Мы передадим запрос менеджеру и свяжемся с вами."
)
TEXT_HELP_MANAGER = (
    "📝 Для связи с менеджером, пожалуйста, напишите одним сообщением:\n"
    "• ИНН или номер договора\n"
    "• Телефон или e‑mail\n\n"
    "🔄 Мы передадим ваш запрос специалисту, и он скоро свяжется с вами."
)
TEXT_REMEM_GMAIL = (
    "📝 Чтобы мы правильно передали ваш запрос менеджеру, напишите, пожалуйста, одним сообщением:\n"
    "• Ваш ИНН или номер договора\n"
    "• Телефон или e-mail для связи\n\n"
    "🔄 Мы передадим ваш запрос специалисту, и он скоро свяжется с вами."
)

# ─── Двухфазная идентификация клиента (ИНН → контакт) ───────────

TEXT_IDENTIFY_FIRST = (
    "📝 Для передачи запроса менеджеру нам нужно идентифицировать вас как "
    "клиента СДЭК.\n\n"
    "Пожалуйста, укажите **ИНН вашей компании** или **номер договора** с нами."
)
TEXT_NO_INN_REFUSE = (
    "К сожалению, этот бот обслуживает только клиентов СДЭК — "
    "юридических лиц и ИП, у которых есть договор с нами.\n\n"
    "Если вы физическое лицо, пожалуйста, обратитесь по номеру горячей линии "
    "CDEK **+7 (495) 009 04 05**.\n\n"
    "Если вы хотите заключить договор как ИП, юрлицо или самозанятый — "
    "выберите в главном меню пункт «Заключить договор».\n\n"
    "Без идентификации я не смогу передать ваш запрос менеджеру."
)
TEXT_PHYSICAL_REFUSE = (
    "Извините, не смогу вам помочь.\n\n"
    "Для физических лиц работает другой канал поддержки: "
    "**+7 (495) 009 04 05**\n"
    "https://www.cdek.ru/ru/contacts\n\n"
    "Здесь мы помогаем только компаниям-партнёрам."
)
TEXT_INN_NOT_FOUND = (
    "❗ Клиент с таким ИНН или номером договора не найден в нашей базе.\n\n"
    "Пожалуйста, проверьте правильность данных и отправьте ИНН/договор ещё раз."
)
TEXT_TERMINATE_DIFFERENT_IDENT = (
    "Вы указали разные ИНН/номера договора, и ни один из них не найден в нашей базе.\n\n"
    "К сожалению, я не могу передать ваш запрос без корректной идентификации. "
    "Если вы уверены, что работаете с нами, начните диалог заново и укажите точный "
    "ИНН или номер договора."
)
TEXT_CONTACT_AFTER_IDENT = (
    "✅ Спасибо, ваш ИНН/договор найден.\n\n"
    "Пожалуйста, одним сообщением укажите:\n"
    "1) **Контактный телефон или e-mail** для связи;\n"
    "2) Кратко — **суть вашего вопроса**, чтобы менеджер мог подготовиться."
)
TEXT_CONTACT_AFTER_IDENT_NOT_FOUND = (
    "Спасибо за уточнение данных ИНН/договора.\n\n"
    "Пожалуйста, одним сообщением укажите:\n"
    "1) **Контактный телефон или e-mail** для связи;\n"
    "2) Кратко — **суть вашего вопроса**, чтобы менеджер мог подготовиться."
)
TEXT_CONTACT_RETRY = (
    "Без контактов менеджер не сможет с вами связаться, чтобы решить вопрос.\n\n"
    "Пожалуйста, одним сообщением укажите:\n"
    "1) **Телефон или e-mail**;\n"
    "2) Кратко суть вопроса."
)
TEXT_CONTACT_FINAL = (
    "Вы не предоставили контакты для связи. К сожалению, я не могу передать заявку.\n\n"
    "Если передумаете, начните диалог заново. Спасибо за понимание."
)
TEXT_SUCCESS_FORWARDED = (
    "✅ Спасибо! Мы передадим ваш запрос специалисту, и он скоро свяжется с вами."
)

TEXT_WEEKEND_AUTOREPLY = (
    "Здравствуйте! Сейчас выходной день, и наши менеджеры работают только "
    "в будни с 09:00 до 18:00. Пожалуйста, продублируйте Ваш вопрос на "
    "почту dolgopa@cdek.ru — ответ обязательно придёт в рабочее время. "
    "Благодарим за понимание и желаем хороших выходных!"
)


# ─── Утилиты ──────────────────────────────────────────────────────


def _make_message(text: str, rows: list[list[dict]] | None = None) -> dict:
    body = {"text": text, "format": "markdown"}
    if rows:
        body["attachments"] = packaging_paid.keyboard(rows)
    return body


def _send(user_id: int, text: str, rows=None, trace_id=None):
    send_message(user_id, _make_message(text, rows), trace_id)


def _answer(callback_id: str, text: str, rows=None, trace_id=None):
    answer_callback(callback_id, {"message": _make_message(text, rows)}, trace_id)


def _ai_mode_rows() -> list[list[dict]]:
    """Стандартные кнопки под ответами AI-помощника."""
    return [
        [packaging_paid.btn_cb("📋 Показать меню", "show_menu")],
        [packaging_paid.btn_cb("❌ Закончить разговор", "stop_ai")],
    ]


def _confirm_to_client(user_id: int, trace_id=None, topic: str | None = None):
    """Подтверждение клиенту, что запрос принят."""
    if topic in ("request_klo", "need_help_cheking", "need_help"):
        text = TEXT_CONFIRM_FORWARD_MANAGER
    else:
        text = "✅ Ваш запрос принят! Менеджер свяжется с вами в ближайшее время."
    rows = [[packaging_paid.btn_cb("◀️ В главное меню", "main_menu")]]
    _send(user_id, text, rows, trace_id)


def _confirm_and_maybe_return_ai(user_id: int, from_ai: bool, trace_id=None,
                                  topic: str | None = None,
                                  client_text: str | None = None):
    """Подтверждение + возврат в AI-режим, если клиент пришёл из ИИ-помощника."""
    if from_ai:
        # Возвращаем в AI-режим — ИИ сам спросит «чем ещё помочь?»
        set_state(user_id, "ai_mode", topic="ai_assistant")
        confirm = "✅ Ваш запрос принят! Менеджер свяжется с вами в ближайшее время."
        ai_continue = "\n\nЧем ещё могу помочь? Если вопросов больше нет — нажмите кнопку ниже."
        _send(user_id, confirm + ai_continue, _ai_mode_rows(), trace_id)
        # Дозаписываем обмен в историю AI, чтобы модель не «забыла», что
        # между её прошлой репликой и следующим вопросом клиента произошла
        # передача запроса менеджеру.
        if client_text:
            append_conversation(user_id, "user", client_text)
        append_conversation(user_id, "assistant", confirm + ai_continue)
    else:
        _confirm_to_client(user_id, trace_id, topic)


# ─── Запрос телефона при первом входе ────────────────────────────

TEXT_REQUEST_CONTACT = (
    "📱 Для работы с ботом нам нужен ваш номер телефона.\n"
    "Поделитесь им, нажав кнопку ниже:"
)


def _contact_keyboard() -> list[dict]:
    return [
        {
            "type": "inline_keyboard",
            "payload": {
                "buttons": [[
                    {"type": "request_contact", "text": "📱 Поделиться контактом"}
                ]],
            },
        }
    ]


def _send_contact_request(user_id: int, trace_id=None):
    payload = {
        "text": TEXT_REQUEST_CONTACT,
        "format": "markdown",
        "attachments": _contact_keyboard(),
    }
    send_message(user_id, payload, trace_id)


def _answer_contact_request(callback_id: str, trace_id=None):
    body = {
        "message": {
            "text": TEXT_REQUEST_CONTACT,
            "format": "markdown",
            "attachments": _contact_keyboard(),
        }
    }
    answer_callback(callback_id, body, trace_id)


def _extract_phone_from_message(message: dict) -> str | None:
    """Извлекает телефон из attachment type=contact (VCF TEL:...)."""
    body = message.get("body") or {}
    atts = body.get("attachments") or message.get("attachments") or []
    for att in atts:
        if att.get("type") != "contact":
            continue
        payload = att.get("payload") or {}
        vcf = payload.get("vcf_info") or ""
        if vcf:
            m = re.search(r"TEL[^:]*:([+\d\s\-()]+)", vcf)
            if m:
                return re.sub(r"[^\d+]", "", m.group(1))
    return None


# ─── Меню ─────────────────────────────────────────────────────────


def _main_menu():
    text = "👋 Здравствуйте! Я бот компании. Чем могу помочь?\n\nВыберите категорию вопроса:"
    rows = [
        [packaging_paid.btn_cb("📦 Создать заказ", "category_create_order")],
        [packaging_paid.btn_cb("📦 Вопрос по заказу", "category_order")],
        [packaging_paid.btn_cb("🔑 Вопрос по личному кабинету", "category_lk")],
        [packaging_paid.btn_cb("💰 Вопрос по взаиморасчётам", "category_finance")],
        [packaging_paid.btn_cb("📦 Заказ упаковки", "category_packaging")],
        [packaging_paid.btn_cb("📞 Обратный звонок менеджера", "callback_request")],
        [packaging_paid.btn_cb("✨ Подключить услуги", "new_services")],
        [packaging_paid.btn_cb("📝 Перезаключить договор", "contract_renewal")],
        [packaging_paid.btn_cb("📄 Заключить договор", "contract")],
        [packaging_paid.btn_cb("⭐ Оставить отзыв", "feedback")],
        [packaging_paid.btn_cb("🤖 Помощь виртуального помощника", "start_ai")],
    ]
    return text, rows


# ─── Обработчики callback_data ────────────────────────────────────
# Каждый обработчик принимает (callback_id, user_id, trace_id)
# и возвращает None (сам отвечает) или (text, rows) для ответа.

def _get_user_name(update: dict) -> str:
    """Извлекает имя пользователя из update."""
    for key in ("callback", "message", "command"):
        obj = update.get(key, {})
        sender = obj.get("sender") or obj.get("user") or obj.get("from") or {}
        name = sender.get("name") or sender.get("first_name") or ""
        if name:
            return name
    return "Клиент"


def _user_id_from_callback(callback: dict) -> int | None:
    """MAX присылает нажимающего в callback.sender; user/from тоже проверяем."""
    sender = callback.get("sender") or {}
    raw = sender.get("user_id")
    if raw is None:
        who = callback.get("user") or callback.get("from") or {}
        raw = who.get("user_id") if isinstance(who, dict) else None
    if raw is None:
        raw = callback.get("user_id")
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


# ── Создание заказа ──

def _create_order_menu():
    text = "📦 **Создание заказа**\n\nВыберите тип отправки:"
    rows = [
        [packaging_paid.btn_cb("🇷🇺 По РФ", "create_order_rf")],
        [packaging_paid.btn_cb("🌍 ЕАЭС или международная", "create_order_international")],
        [packaging_paid.btn_cb("◀️ Назад", "main_menu")],
    ]
    return text, rows


def _create_order_rf():
    text = (
        "🇷🇺 **Заказ по РФ**\n\n"
        "Попробуйте удобный Личный кабинет: создайте заказ сами за пару минут.\n"
        "Перейти: https://lk.cdek.ru/user/login\n\n"
        "Нужна помощь? Кнопка «Указать договор/ИНН» — передадим запрос специалисту."
    )
    rows = [
        [packaging_paid.btn_cb("📝 Указать договор/ИНН", "request_klo")],
        [packaging_paid.btn_cb("◀️ Назад", "category_create_order")],
    ]
    return text, rows


def _create_order_international():
    text = TEXT_INTERNATIONAL_MENU
    rows = [
        [packaging_paid.btn_cb("📝 Указать данные", "need_help_with_contact")],
        [packaging_paid.btn_cb("◀️ Назад", "category_create_order")],
    ]
    return text, rows


# ── Вопросы по заказу ──

def _order_menu():
    text = "📦 **Вопросы по заказу**\n\nВыберите что вас интересует:"
    rows = [
        [packaging_paid.btn_cb("🔍 Отследить заказ", "order_track")],
        [packaging_paid.btn_cb("📅 Назначить дату доставки", "order_date")],
        [packaging_paid.btn_cb("✏️ Внести изменения в заказ", "order_edit")],
        [packaging_paid.btn_cb("❓ Другой вопрос по заказу", "order_other")],
        [packaging_paid.btn_cb("◀️ В главное меню", "main_menu")],
    ]
    return text, rows


def _order_track():
    text = (
        "🔍 Вы можете отследить ваш заказ в личном кабинете по его трек-номеру, пройдя по ссылке:\n\n"
        "https://www.cdek.ru/ru/tracking\n\n"
        "❓ **Вопрос решен?**"
    )
    rows = [
        [packaging_paid.btn_cb("✅ Да", "tracking_solved_yes")],
        [packaging_paid.btn_cb("❌ Нет", "tracking_solved_no")],
    ]
    return text, rows


def _order_date():
    text = (
        "📅 Назначить дату доставки можно в личном кабинете по ссылке\n"
        "https://lk.cdek.ru/user/login\n"
        "Войдите в личный кабинет и выберите там удобную дату.\n\n"
        "Если нужна помощь — нажмите кнопку «Нужна помощь» и напишите нам."
    )
    rows = [
        [packaging_paid.btn_cb("✅ Вопрос решён", "tracking_solved_yes")],
        [packaging_paid.btn_cb("✅ Нужна помощь", "need_help_cheking")],
        [packaging_paid.btn_cb("◀️ В главное меню", "main_menu")],
    ]
    return text, rows


def _order_edit():
    text = (
        "✏️ **Внести изменения**\n\n"
        "Внести изменения: https://lk.cdek.ru/user/login\n\n"
        "Войдите в личный кабинет и отредактируйте заказ в меню «Список заказов».\n"
        "Если Ваш заказ уже сдан на отправку, то корректировка даты доставки "
        "в личном кабинете невозможна, и Вам следует обратиться к менеджеру.\n\n"
        "Если нужна помощь — выберите ниже в меню «нужна помощь» и укажите номер заказа, "
        "и мы передадим специалисту."
    )
    rows = [
        [packaging_paid.btn_cb("✅ Вопрос решен", "tracking_solved_yes")],  # добавлена кнопка по ТЗ
        [packaging_paid.btn_cb("✅ Нужна помощь", "need_help")],
        [packaging_paid.btn_cb("◀️ В главное меню", "main_menu")],
    ]
    return text, rows


# ── Личный кабинет ──

def _lk_menu():
    text = "🔑 **Личный кабинет**\n\nВыберите что вас интересует:"
    rows = [
        [packaging_paid.btn_cb("🔐 Восстановить доступ", "lk_restore")],
        [packaging_paid.btn_cb("📚 Обучение работе в ЛК", "lk_training")],
        [packaging_paid.btn_cb("◀️ В главное меню", "main_menu")],
    ]
    return text, rows


def _lk_restore():
    text = (
        "🔐 **Восстановление доступа**\n\n"
        "1. Перейдите по ссылке https://lk.cdek.ru/user/login\n"
        '2. Нажмите **«Не помню пароль»**\n'
        "3. Введите Ваш номер договора\n"
        "4. Ссылка придет на электронную почту указанную в договоре\n\n"
        "❓ Не приходит письмо или забыли почту? Нажмите кнопку «Написать нам»."
    )
    rows = [
        [packaging_paid.btn_cb("✉️ Написать нам", "remem_gmail")],
        [packaging_paid.btn_cb("◀️ В главное меню", "main_menu")],
    ]
    return text, rows


def _lk_training():
    text = (
        "📘 **Обучение работе в Личном кабинете**\n\n"
        "Чтобы вам было комфортно разобраться в личном кабинете, мы подготовили "
        "полезную памятку. А если останутся вопросы — всегда рядом менеджер, "
        "который поможет.\n\n"
        "Выберите, что вам удобнее:"
    )
    rows = [
        [packaging_paid.btn_cb("📎 Получить памятку", "get_pdf")],
        [packaging_paid.btn_cb("👤 Помощь менеджера", "need_help_manager")],
        [packaging_paid.btn_cb("◀️ В главное меню", "main_menu")],
    ]
    return text, rows


# ── Финансы ──

def _finance_menu():
    text = "💰 **Взаиморасчёты**\n\nВыберите что вас интересует:"
    rows = [
        [packaging_paid.btn_cb("📄 Акт сверки", "finance_act")],
        [packaging_paid.btn_cb("💳 Получить счет", "finance_invoice")],
        [packaging_paid.btn_cb("❓ Вопрос по счету", "finance_question")],
        [packaging_paid.btn_cb("◀️ В главное меню", "main_menu")],
    ]
    return text, rows


def _finance_act():
    text = (
        "📄 **Акт сверки**\n\n"
        "Самостоятельно запросить акт сверки можно в личном кабинете:\n"
        "https://lk.cdek.ru/user/login\n"
        'Раздел «Документы» → «Запросить акт сверки»\n\n'
        "Не получается? Нажмите кнопку «Указать период» — и мы поможем."
    )
    rows = [
        [packaging_paid.btn_cb("📝 Указать период", "need_help_with_period")],
        [packaging_paid.btn_cb("◀️ В главное меню", "main_menu")],
    ]
    return text, rows


# ── Упаковка ──

def _packaging_menu():
    text = "📦 **Заказ упаковки**\n\nВыберите тип:"
    rows = [
        [packaging_paid.btn_cb("💰 Платная", "packaging_paid")],
        [packaging_paid.btn_cb("🆓 Бесплатная", "packaging_free")],
        [packaging_paid.btn_cb("◀️ В главное меню", "main_menu")],
    ]
    return text, rows


def _packaging_free():
    text = TEXT_FREE_BOX_MENU
    rows = [
        [packaging_paid.btn_cb("📝 Указать данные", "free_pckaiging_data")],
        [packaging_paid.btn_cb("◀️ В главное меню", "main_menu")],
    ]
    return text, rows


# ── Таблица маршрутизации callback → (text, rows) ──

SIMPLE_CALLBACKS = {
    # Создание заказа
    "category_create_order": _create_order_menu,
    "create_order_rf": _create_order_rf,
    "create_order_international": _create_order_international,

    # Вопросы по заказу
    "category_order": _order_menu,
    "order_track": _order_track,
    "order_date": _order_date,
    "order_edit": _order_edit,

    # ЛК
    "category_lk": _lk_menu,
    "lk_restore": _lk_restore,
    "lk_training": _lk_training,

    # Финансы
    "category_finance": _finance_menu,
    "finance_act": _finance_act,

    # Упаковка
    "category_packaging": _packaging_menu,
    "packaging_free": _packaging_free,
}


# ── Callbacks, которые устанавливают состояние и просят текст ──

# Формат: callback_data → (state, topic, prompt_text)
# Для всех waiting_message/waiting_klo/waiting_buh используем единый первый
# шаг — запрос ИНН/договора. Далее флоу разбит на фазы ident → contact
# в обработчике текста (см. _handle_text_message). waiting_pro оставлен
# как есть: у новых клиентов ИНН в базе быть не может.
STATE_CALLBACKS = {
    # → waiting_message (пересылка закреплённому менеджеру через ИНН-поиск)
    "need_help_with_contact": ("waiting_message", "need_help_with_contact", TEXT_IDENTIFY_FIRST),
    "callback_request": ("waiting_message", "callback_request", TEXT_IDENTIFY_FIRST),
    "feedback": ("waiting_message", "feedback", TEXT_IDENTIFY_FIRST),
    "contract_renewal": ("waiting_message", "contract_renewal", TEXT_IDENTIFY_FIRST),
    "new_services": ("waiting_message", "new_services", TEXT_IDENTIFY_FIRST),
    "tracking_help_yes": ("waiting_message", "tracking_help_yes", TEXT_IDENTIFY_FIRST),
    "free_pckaiging_data": ("waiting_message", "free_pckaiging_data", TEXT_IDENTIFY_FIRST),
    # → waiting_klo (пересылка в КЛО)
    "request_klo": ("waiting_klo", "request_klo", TEXT_IDENTIFY_FIRST),
    "order_other": ("waiting_klo", "order_other", TEXT_IDENTIFY_FIRST),
    "need_help": ("waiting_klo", "order_edit", TEXT_IDENTIFY_FIRST),
    "need_help_with_order": ("waiting_klo", "order_edit", TEXT_IDENTIFY_FIRST),
    "need_help_cheking": ("waiting_klo", "order_date", TEXT_IDENTIFY_FIRST),
    "tracking_solved_no": ("waiting_klo", "order_track", TEXT_IDENTIFY_FIRST),

    # → waiting_buh (пересылка бухгалтеру)
    "finance_invoice": ("waiting_buh", "finance_invoice", TEXT_IDENTIFY_FIRST),
    "finance_question": ("waiting_buh", "finance_question", TEXT_IDENTIFY_FIRST),
    "need_help_with_period": ("waiting_buh", "need_help_with_period", TEXT_IDENTIFY_FIRST),

    # → waiting_pro (продажнику — ТОЛЬКО заключение нового договора).
    # Тут проверки по базе НЕТ — у нового клиента ИНН в базе и не должно быть.
    "contract": ("waiting_pro", "contract", TEXT_CONTRACT),

    # → waiting_message (закреплённый менеджер по ИНН): ЛК-вопросы
    # существующих клиентов — восстановление доступа и обучение.
    "need_help_manager": ("waiting_message", "need_help_manager", TEXT_IDENTIFY_FIRST),
    "remem_gmail": ("waiting_message", "remem_gmail", TEXT_IDENTIFY_FIRST),
}

# Состояния, где применяется двухфазная идентификация ident → contact.
# waiting_pro сюда не входит.
IDENT_CONTACT_STATES = ("waiting_message", "waiting_klo", "waiting_buh")

# ── Разделение присланного клиентом текста на контакт и комментарий ──

_EMAIL_EXTRACT_RE = re.compile(r"[\w.+\-]+@[\w\-]+\.[a-zA-Z]{2,}")
# Последовательность «телефонных» символов: +, цифры, скобки, дефисы,
# пробелы. Требуем минимум 7 цифр.
_PHONE_EXTRACT_RE = re.compile(r"(?:[+()\-\s\d]){7,}")
# Строчные префиксы, которые часто пишут перед контактом: «тел.:», «email:»
_CONTACT_PREFIX_RE = re.compile(
    r"^\s*(?:тел(?:\.|ефон)?\s*[:.\-]?\s*|e-?mail\s*[:.\-]?\s*|почта\s*[:.\-]?\s*|контакт\s*[:.\-]?\s*)",
    re.IGNORECASE,
)


def _extract_contact_and_comment(text: str) -> tuple[str, str]:
    """Разделяет сообщение клиента на (contact, comment).

    - Ищет e-mail и/или «телефонную» подстроку (7+ цифр со скобками/дефисами)
    - Удаляет их из текста; то, что осталось, чистит от «тел.:»/«email:»
      и знаков препинания по краям → это comment
    - Возвращает пустую строку, если соответствующая часть не найдена
    """
    contacts: list[str] = []
    remaining = text

    for m in _EMAIL_EXTRACT_RE.findall(remaining):
        contacts.append(m.strip())
    remaining = _EMAIL_EXTRACT_RE.sub(" ", remaining)

    phone_match = _PHONE_EXTRACT_RE.search(remaining)
    if phone_match:
        # Проверим, что внутри найденного куска реально 7+ цифр —
        # иначе regex мог захватить просто знаки препинания.
        raw = phone_match.group(0)
        digits_only = re.sub(r"\D", "", raw)
        if len(digits_only) >= 7:
            contacts.append(re.sub(r"\s+", " ", raw).strip(" -"))
            remaining = remaining[:phone_match.start()] + " " + remaining[phone_match.end():]

    contact = ", ".join(c for c in contacts if c)

    # Чистим оставшийся комментарий — убираем служебные ярлыки,
    # оставшиеся без значения (т.к. значение уже унесли в contact).
    comment = re.sub(r"\s+", " ", remaining).strip()
    comment = _CONTACT_PREFIX_RE.sub("", comment).strip()
    comment = re.sub(
        r"\b(?:тел(?:\.|ефон)?|e-?mail|почта|контакт)\s*[:.\-]?\s*"
        r"(?=[\s;,.]|$)",
        " ",
        comment,
        flags=re.IGNORECASE,
    )
    comment = re.sub(r"\s+", " ", comment).strip(".,;:— -")
    return contact, comment

# ─── Обработка callback-ов ─────────────────────────────────────────


def _handle_manager_action(update: dict, callback_id: str,
                           payload: str, trace_id: str):
    """Обработчик кнопок «Взял в работу» / «Решено» на карточке менеджера.

    payload: mgr_ack:<client_user_id> | mgr_done:<client_user_id>
    — клиенту шлём авто-уведомление,
    — карточку менеджера обновляем: убираем нажатую кнопку и приписываем
      статус с именем менеджера.
    """
    callback = update.get("callback", {})
    sender = callback.get("sender") or callback.get("user") or {}
    manager_name = (sender.get("name") or sender.get("first_name")
                    or "Менеджер")

    action, _, client_id_str = payload.partition(":")
    try:
        client_user_id = int(client_id_str)
    except (TypeError, ValueError):
        log_event("mgr_action_bad_payload", trace_id, payload=payload)
        return

    # Оригинальный текст карточки — чтобы при обновлении дописать статус,
    # а не потерять форматированный блок с данными клиента.
    orig_body = (update.get("message") or {}).get("body") or {}
    orig_text = orig_body.get("text") or ""

    if action == "mgr_ack":
        try:
            send_message(client_user_id, {
                "text": "👨‍💼 Специалист взял ваш запрос в работу и скоро с Вами свяжется.",
                "format": "markdown",
            }, trace_id)
        except Exception as e:
            log_event("mgr_ack_client_error", trace_id, error=str(e))

        new_text = orig_text + f"\n\n✅ В работе: {manager_name}"
        # Кнопку «Взял» убираем, «Решено» оставляем.
        rows = [[packaging_paid.btn_cb(
            "✔️ Решено", f"mgr_done:{client_user_id}")]]
        _answer(callback_id, new_text, rows, trace_id)
        log_event("mgr_ack", trace_id,
                  manager=manager_name, client_user_id=client_user_id)
        return

    if action == "mgr_done":
        try:
            send_message(client_user_id, {
                "text": (
                    "✅ Ваш запрос закрыт.\n"
                    "Если остались вопросы — создайте новый запрос. "
                    "Для этого просто продолжите диалог: напишите мне "
                    "что-нибудь прямо сейчас."
                ),
                "format": "markdown",
            }, trace_id)
        except Exception as e:
            log_event("mgr_done_client_error", trace_id, error=str(e))

        new_text = orig_text + f"\n\n✔️ Решено: {manager_name}"
        body = {"text": new_text, "format": "markdown", "attachments": []}
        answer_callback(callback_id, {"message": body}, trace_id)
        log_event("mgr_done", trace_id,
                  manager=manager_name, client_user_id=client_user_id)
        return


def _handle_callback(update: dict, trace_id: str):
    callback = update.get("callback", {})
    callback_id = callback.get("callback_id")
    payload = callback.get("payload", "")
    user_id = _user_id_from_callback(callback)

    # Диагностика проблем с callback-ветками на сервере
    try:
        log_event(
            "callback_received",
            trace_id,
            callback_id=callback_id,
            payload=payload,
            user_id=user_id,
            update=bool(update.get("update_type")),
        )
    except Exception:
        pass

    if not callback_id:
        log_event("skip", trace_id, reason="no_callback_id")
        return

    # ── Действия менеджера над карточкой клиента («Взял в работу» / «Решено»)
    # Идут ДО phone-gate'а: у менеджеров телефон обычно не сохранён.
    if payload.startswith("mgr_ack:") or payload.startswith("mgr_done:"):
        _handle_manager_action(update, callback_id, payload, trace_id)
        return

    # ── Гейт: если у пользователя нет телефона — просим поделиться ──
    if user_id is not None:
        try:
            if not has_phone(user_id):
                _answer_contact_request(callback_id, trace_id)
                return
        except Exception as e:
            log_event("has_phone_error", trace_id, error=str(e))

    # 1) Главное меню
    if payload in ("main_menu", "menu"):
        if user_id is not None:
            clear_conversation(user_id)
            try:
                clear_state(user_id)
            except Exception:
                pass
        text, rows = _main_menu()
        _answer(callback_id, text, rows, trace_id)
        return

    # 1.1) Включить режим AI-помощника
    if payload == "start_ai":
        if user_id is not None:
            try:
                set_state(user_id, "ai_mode", topic="ai_assistant")
            except Exception as e:
                log_event("set_state_error", trace_id, error=str(e), payload=payload)
            clear_conversation(user_id)
        text = (
            "🤖 **Виртуальный помощник СДЭК**\n\n"
            "Здравствуйте! Я виртуальный помощник компании СДЭК.\n"
            "Задайте ваш вопрос текстом — и я постараюсь помочь.\n\n"
            "Если удобнее выбрать пункт из списка — нажмите «📋 Показать меню»."
        )
        _answer(callback_id, text, _ai_mode_rows(), trace_id)
        return

    # 1.1.1) Показать меню, не выходя из AI-режима
    if payload == "show_menu":
        text, rows = _main_menu()
        _answer(callback_id, text, rows, trace_id)
        return

    # 1.2) Выключить режим AI-помощника
    if payload == "stop_ai":
        if user_id is not None:
            clear_conversation(user_id)
            try:
                clear_state(user_id)
            except Exception:
                pass
        text, rows = _main_menu()
        _answer(callback_id, text, rows, trace_id)
        return

    # 2) Простые callback-ы (меню → подменю)
    if payload in SIMPLE_CALLBACKS:
        text, rows = SIMPLE_CALLBACKS[payload]()
        _answer(callback_id, text, rows, trace_id)
        return

    # 3) Callback-формы (режим ожидания ввода).
    # Для waiting_message/waiting_klo/waiting_buh сразу стартуем с фазы ident
    # (manager_id="ident"), чтобы обработчик текста знал, где мы находимся.
    # waiting_pro — старый флоу, фаз нет.
    if payload in STATE_CALLBACKS:
        state, topic, prompt_text = STATE_CALLBACKS[payload]
        if user_id is not None:
            try:
                if state in IDENT_CONTACT_STATES:
                    set_state(user_id, state, topic=topic,
                              manager_id="ident", order_number="0", inn="")
                else:
                    set_state(user_id, state, topic=topic)
            except Exception as e:
                log_event("set_state_error", trace_id, error=str(e), payload=payload)
        else:
            log_event("callback_no_user_id", trace_id, payload=payload)
        back_text, back_payload = ("◀️ В главное меню", "main_menu")
        rows = [[packaging_paid.btn_cb(back_text, back_payload)]]
        _answer(callback_id, prompt_text, rows, trace_id)
        return

    # 4) «Вопрос решён — да»
    if payload == "tracking_solved_yes":
        text = "✅ Отлично! Если появятся вопросы — обращайтесь."
        rows = [[packaging_paid.btn_cb("◀️ В главное меню", "main_menu")]]
        _answer(callback_id, text, rows, trace_id)
        return

    # 5) PDF памятка
    if payload == "get_pdf":
        rows = [
            [packaging_paid.btn_cb("✅ Вопрос решен", "tracking_solved_yes")],  # добавлена по ТЗ
            [packaging_paid.btn_cb("◀️ В главное меню", "main_menu")]
        ]
        pdf_path = settings.LK_MEMO_PDF_PATH
        if user_id is not None and os.path.isfile(pdf_path):
            # Сначала ответ на callback — потом долгая загрузка на CDN (иначе таймауты клиента)
            #_answer(callback_id, "📎 Загружаю памятку, несколько секунд…", rows, trace_id)
            token = upload_local_file(pdf_path, trace_id)
            if token:
                last = send_message_with_file(
                    user_id,
                    "📎 **Памятка по работе в ЛК**",
                    token,
                    rows,
                    trace_id,
                )
                try:
                    ok = last is not None and last.status_code == 200
                    body = last.json() if ok else {}
                    if body.get("code") == "attachment.not.ready":
                        ok = False
                except Exception:
                    ok = last is not None and last.status_code == 200
                if not ok:
                    fallback = (
                        "📎 Не удалось отправить файл. Положите PDF по пути из настройки "
                        "**LK_MEMO_PDF_PATH** и попробуйте снова."
                    )
                    _send(user_id, fallback, rows, trace_id)
            else:
                _send(
                    user_id,
                    "📎 **Памятка по работе в ЛК**\n\n"
                    "Не удалось загрузить файл на сервер. Проверьте сеть или попробуйте позже.",
                    rows,
                    trace_id,
                )
        else:
            if user_id is None:
                log_event("callback_no_user_id", trace_id, payload=payload)
            text = (
                "📎 **Памятка по работе в ЛК**\n\n"
                f"Добавьте файл PDF в `{pdf_path}` (или задайте переменную **LK_MEMO_PDF_PATH**)."
            )
            _answer(callback_id, text, rows, trace_id)
        return

    # ── Каталог платной упаковки ──

    if payload == "packaging_paid":
        text, rows = packaging_paid.categories_menu()
        _answer(callback_id, text, rows, trace_id)
        return

    if payload.startswith("cat_"):
        category = payload[4:]
        text, rows = packaging_paid.items_menu(category)
        _answer(callback_id, text, rows, trace_id)
        return

    if payload.startswith("item_"):
        item_id = payload[5:]
        text, rows = packaging_paid.item_card(item_id, 1)
        _answer(callback_id, text, rows, trace_id)
        return

    if payload.startswith("inc:") or payload.startswith("dec:"):
        parts = payload.split(":")
        action = parts[0]
        item_id = parts[1] if len(parts) > 1 else ""
        qty = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 1
        text, rows = packaging_paid.adjust_qty(item_id, qty, action)
        _answer(callback_id, text, rows, trace_id)
        return

    if payload.startswith("add:"):
        parts = payload.split(":")
        item_id = parts[1] if len(parts) > 1 else ""
        qty = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 1
        uid = user_id if user_id is not None else 0
        if user_id is None:
            log_event("callback_no_user_id", trace_id, payload=payload)
        text, rows = packaging_paid.add_to_cart(uid, item_id, qty)
        _answer(callback_id, text, rows, trace_id)
        return

    if payload == "seek_cart":
        uid = user_id if user_id is not None else 0
        if user_id is None:
            log_event("callback_no_user_id", trace_id, payload=payload)
        text, rows = packaging_paid.view_cart(uid)
        _answer(callback_id, text, rows, trace_id)
        return

    if payload == "clear_cart":
        uid = user_id if user_id is not None else 0
        if user_id is None:
            log_event("callback_no_user_id", trace_id, payload=payload)
        text, rows = packaging_paid.clear_cart(uid)
        _answer(callback_id, text, rows, trace_id)
        return

    if payload == "checkout":
        # Корзина → оформление: формируем текст корзины, просим ИНН (фаза ident).
        # Текст корзины сохраняем в comment с префиксом `cart:`, чтобы отличать
        # его от флага `from_ai`. В фазе contact подхватим обратно.
        uid = user_id if user_id is not None else 0
        if user_id is None:
            log_event("callback_no_user_id", trace_id, payload=payload)
        cart_text, _ = packaging_paid.view_cart(uid)
        if user_id is not None:
            set_state(user_id, "waiting_klo", topic="checkout",
                      comment=f"cart:{cart_text}", manager_id="ident",
                      order_number="0", inn="")
        rows = [[packaging_paid.btn_cb("◀️ В главное меню", "main_menu")]]
        _answer(callback_id, TEXT_IDENTIFY_FIRST, rows, trace_id)
        return

    if payload == "noop":
        return

    # ── Неизвестный callback ──
    log_event("unknown_callback", trace_id, payload=payload)
    text = f"Получен запрос: `{payload}`"
    rows = [[packaging_paid.btn_cb("◀️ В главное меню", "main_menu")]]
    _answer(callback_id, text, rows, trace_id)


# ─── Обработка текстовых сообщений ────────────────────────────────


def _handle_text_message(update: dict, trace_id: str):
    message = update.get("message") or update.get("command") or {}
    sender = message.get("sender") or update.get("sender") or {}
    user_id = sender.get("user_id") or message.get("user_id") or update.get("user_id")
    user_name = sender.get("name") or sender.get("first_name") or "Клиент"
    text = message.get("body", {}).get("text", "") or message.get("text", "")

    if not user_id:
        log_event("skip", trace_id, reason="no_user_id")
        return

    # ── /chat_id — утилита для получения chat_id текущего чата.
    # Идёт ДО phone-gate'а, чтобы работала в группах, где у бота нет
    # «телефона» отправителя.
    if text.strip().lower() == "/chat_id":
        recipient = message.get("recipient") or {}
        chat_id = recipient.get("chat_id")
        chat_type = recipient.get("chat_type", "unknown")
        reply_text = (
            f"🆔 `chat_id`: `{chat_id}`\n"
            f"📂 `chat_type`: `{chat_type}`\n"
            f"👤 `user_id` отправителя: `{user_id}`"
        )
        reply_payload = {"text": reply_text, "format": "markdown"}
        if chat_type in ("chat", "channel") and chat_id:
            send_message_to_chat(chat_id, reply_payload, trace_id)
        else:
            send_message(user_id, reply_payload, trace_id)
        log_event("chat_id_queried", trace_id,
                  chat_id=chat_id, chat_type=chat_type, user_id=user_id)
        return

    # ── Приём поделённого контакта (request_contact кнопка) ──
    phone = _extract_phone_from_message(message)
    if phone:
        try:
            save_phone(user_id, phone)
            log_event("phone_saved", trace_id, user_id=user_id)
        except Exception as e:
            log_event("save_phone_error", trace_id, error=str(e))
        _send(user_id, "✅ Спасибо! Номер сохранён.", trace_id=trace_id)
        # После сохранения телефона сразу в AI-режим
        try:
            set_state(user_id, "ai_mode", topic="ai_assistant")
        except Exception as e:
            log_event("set_state_error", trace_id, error=str(e))
        clear_conversation(user_id)
        welcome = (
            "🤖 **Виртуальный помощник СДЭК**\n\n"
            "Здравствуйте! Я виртуальный помощник компании СДЭК.\n"
            "Задайте ваш вопрос текстом — и я постараюсь помочь.\n\n"
            "Если удобнее выбрать пункт из списка — нажмите «📋 Показать меню»."
        )
        _send(user_id, welcome, _ai_mode_rows(), trace_id)
        return

    # ── Гейт: у пользователя ещё нет телефона — просим поделиться ──
    try:
        if not has_phone(user_id):
            _send_contact_request(user_id, trace_id)
            return
    except Exception as e:
        log_event("has_phone_error", trace_id, error=str(e))

    # Команда /start / начать → сразу в AI-режим (меню всегда доступно кнопкой)
    cmd = text.strip().lower()
    if cmd in ("/start", "start", "начать"):
        try:
            set_state(user_id, "ai_mode", topic="ai_assistant")
        except Exception as e:
            log_event("set_state_error", trace_id, error=str(e))
        clear_conversation(user_id)
        welcome = (
            "🤖 **Виртуальный помощник СДЭК**\n\n"
            "Здравствуйте! Я виртуальный помощник компании СДЭК.\n"
            "Задайте ваш вопрос текстом — и я постараюсь помочь.\n\n"
            "Если удобнее выбрать пункт из списка — нажмите «📋 Показать меню»."
        )
        _send(user_id, welcome, _ai_mode_rows(), trace_id)
        return

    # /menu → старое поведение: показать главное меню напрямую
    if cmd == "/menu":
        t, rows = _main_menu()
        _send(user_id, t, rows, trace_id)
        return

    # Админ-команда: /change_manager
    if text.strip().lower() == "/change_manager":
        if user_id == settings.ADMIN_USER_ID:
            set_state(user_id, "admin_waiting_old", topic="change_manager")
            _send(user_id, "📞 Введите имя **старого** менеджера:", trace_id=trace_id)
        else:
            _send(user_id, "⛔ У вас нет прав для этой команды.", trace_id=trace_id)
        return

    # Проверяем, есть ли ответ менеджера (reply на сообщение бота).
    # В MAX API mid исходного сообщения лежит в одном из двух мест:
    #   1) message.link.message.mid  (link.type == "reply" | "forward")
    #   2) message.body.reply_to     (строка — только для reply)
    # См. max_schemes.go → LinkedMessage, MessageBody.
    body = message.get("body") or {}
    link = message.get("link") or {}
    linked_msg = link.get("message") or {}
    linked_mid = (
        linked_msg.get("mid")
        or body.get("reply_to")
        or link.get("mid")              # на всякий — если API всё же пришлёт плоско
        or ""
    )
    log_event("reply_check", trace_id,
              user_id=user_id,
              has_link=bool(link),
              link_type=link.get("type", ""),
              linked_mid=linked_mid,
              body_reply_to=body.get("reply_to", ""))
    if linked_mid:
        try:
            client_info = find_client_by_message(str(linked_mid))
            if client_info and client_info.get("client_user_id"):
                forward_manager_reply_to_client(
                    client_info["client_user_id"], text, trace_id)
                log_event("reply_forwarded", trace_id,
                          linked_mid=linked_mid,
                          client_user_id=client_info["client_user_id"])
                return
            log_event("reply_map_miss", trace_id, linked_mid=linked_mid)
        except Exception as e:
            log_event("reply_lookup_error", trace_id,
                      error=str(e), linked_mid=linked_mid)

    # Проверяем состояние пользователя
    try:
        state_data = get_state(user_id)
    except Exception:
        state_data = None

    if state_data and state_data.get("state") not in (None, "", "none"):
        state = state_data["state"]
        topic = state_data.get("topic", "")
        prev_comment = state_data.get("comment", "")

        # ── Admin: смена менеджера ──
        if state == "admin_waiting_old":
            set_state(user_id, "admin_waiting_new", topic="change_manager",
                      comment=f"old:{text.strip()}")
            _send(user_id, "📞 Введите имя **нового** менеджера:", trace_id=trace_id)
            return

        if state == "admin_waiting_new":
            old_name = prev_comment.replace("old:", "")
            set_state(user_id, "admin_waiting_new_id", topic="change_manager",
                      comment=f"old:{old_name}|new:{text.strip()}")
            _send(user_id, "📞 Введите **MAX user ID** нового менеджера:", trace_id=trace_id)
            return

        if state == "admin_waiting_new_id":
            parts = prev_comment.split("|")
            old_name = parts[0].replace("old:", "") if len(parts) > 0 else ""
            new_name = parts[1].replace("new:", "") if len(parts) > 1 else ""
            new_id = text.strip()

            count = 0
            try:
                count = update_manager_for_clients(old_name, new_name)
                update_manager_id(new_name, new_id)
            except Exception as e:
                _send(user_id, f"❌ Ошибка: {e}", trace_id=trace_id)
                clear_state(user_id)
                return

            clear_state(user_id)
            _send(user_id,
                  f"✅ Готово!\n\n"
                  f"Менеджер **{old_name}** заменён на **{new_name}** (ID: {new_id}).\n"
                  f"Обновлено клиентов: **{count}**",
                  trace_id=trace_id)
            return

        # ── Режим AI-помощника ──
        if state == "ai_mode":
            ai_response = ask_ai(user_id, text, trace_id)
            if not ai_response:
                _send(user_id, "Извините, помощник временно недоступен. Попробуйте позже.",
                      _ai_mode_rows(), trace_id)
                return

            clean_text, ai_state, ai_topic = parse_state_command(ai_response)

            if ai_state and ai_topic:
                # AI решил передать запрос сотруднику — выходим из ai_mode.
                # Помечаем comment="from_ai", чтобы после пересылки вернуть в ai_mode.
                # Сбрасываем фазу двухфазной идентификации к ident с чистыми
                # счётчиком и накопителем ИНН — бот сам дальше спросит ИНН
                # и контакт через TEXT_IDENTIFY_FIRST. waiting_pro проверку
                # в базе не делает, но для единообразия тоже сбрасываем.
                if ai_state in IDENT_CONTACT_STATES:
                    set_state(user_id, ai_state, topic=ai_topic,
                              comment="from_ai",
                              manager_id="ident", order_number="0", inn="")
                else:
                    set_state(user_id, ai_state, topic=ai_topic,
                              comment="from_ai")
                # Если AI сам не попросил ИНН — добавляем единый запрос
                # от бота (шаг 1 спецификации).
                msg = clean_text.strip()
                if ai_state in IDENT_CONTACT_STATES and "ИНН" not in msg.upper():
                    msg = f"{msg}\n\n{TEXT_IDENTIFY_FIRST}" if msg else TEXT_IDENTIFY_FIRST
                _send(user_id, msg, trace_id=trace_id)
            else:
                # Обычный ответ AI — кнопка завершения всегда внизу
                rows = _ai_mode_rows()
                _send(user_id, clean_text, rows, trace_id)
            return

        # ── Обычные состояния: пересылка ──
        # comment хранит:
        #   - "from_ai"       — клиент пришёл из AI-режима (после пересылки вернуть)
        #   - "cart:<text>"   — для checkout в waiting_klo хранит текст корзины
        #   - ""              — обычный заход по кнопке
        from_ai = prev_comment == "from_ai"
        cart_text = prev_comment[5:] if prev_comment.startswith("cart:") else ""

        menu_rows = [[packaging_paid.btn_cb("◀️ В главное меню", "main_menu")]]

        # waiting_pro (Заключить договор) — БЕЗ проверки по базе.
        # У нового клиента ИНН в клиентской таблице быть не должно.
        # Просто принимаем текст и отправляем продажнику.
        if state == "waiting_pro":
            clear_state(user_id)
            if is_weekend():
                log_event("weekend_autoreply", trace_id,
                          user_id=user_id, state=state, topic=topic)
                _send(user_id, TEXT_WEEKEND_AUTOREPLY, menu_rows, trace_id)
                return
            forward_to_sales(user_id, user_name, text, topic, trace_id)
            _confirm_and_maybe_return_ai(user_id, from_ai, trace_id,
                                          topic, client_text=text)
            return

        # Двухфазная идентификация: ident → contact (или contact_escalate).
        if state in IDENT_CONTACT_STATES:
            phase = (state_data.get("manager_id") or "ident").strip() or "ident"
            try:
                retry = int(state_data.get("order_number") or "0")
            except (TypeError, ValueError):
                retry = 0
            prev_ident = (state_data.get("inn") or "").strip()

            # ── Фаза ident: ждём ИНН/договор ──
            if phase == "ident":
                data = extract_data(text)
                inn_val = (data.get("inn") or "").strip()
                contract_val = (data.get("contract") or "").strip()
                ident_val = inn_val or contract_val

                if ident_val:
                    client = None
                    try:
                        if inn_val:
                            client = find_client_by_inn(inn_val)
                        elif contract_val:
                            client = find_client_by_contract(contract_val)
                    except Exception as e:
                        log_event("client_lookup_error", trace_id, error=str(e))

                    if client:
                        # Нашли клиента — переходим к сбору контакта.
                        try:
                            set_state(user_id, state, topic=topic,
                                      comment=prev_comment,
                                      manager_id="contact",
                                      order_number="0",
                                      inn=ident_val)
                        except Exception as e:
                            log_event("set_state_error", trace_id, error=str(e))
                        log_event("ident_found", trace_id,
                                  user_id=user_id, state=state, topic=topic,
                                  ident=ident_val,
                                  manager_name=client.get("manager_name", ""))
                        _send(user_id, TEXT_CONTACT_AFTER_IDENT, menu_rows, trace_id)
                        return

                    # Ident есть, но в базе не найден.
                    if prev_ident and prev_ident == ident_val:
                        # Повтор того же значения — возможно новый клиент.
                        # Переходим к сбору контакта для общего чата.
                        try:
                            set_state(user_id, state, topic=topic,
                                      comment=prev_comment,
                                      manager_id="contact_escalate",
                                      order_number="0",
                                      inn=ident_val)
                        except Exception as e:
                            log_event("set_state_error", trace_id, error=str(e))
                        log_event("ident_repeat_not_found", trace_id,
                                  user_id=user_id, state=state, topic=topic,
                                  ident=ident_val)
                        _send(user_id, TEXT_CONTACT_AFTER_IDENT_NOT_FOUND,
                              menu_rows, trace_id)
                        return

                    if prev_ident and prev_ident != ident_val:
                        # Клиент прислал другой ИНН/договор и снова не найден.
                        clear_state(user_id)
                        log_event("ident_terminated_different", trace_id,
                                  user_id=user_id, state=state, topic=topic,
                                  prev_ident=prev_ident, new_ident=ident_val)
                        _send(user_id, TEXT_TERMINATE_DIFFERENT_IDENT,
                              menu_rows, trace_id)
                        return

                    # Первый ввод, не найден — просим проверить.
                    try:
                        set_state(user_id, state, topic=topic,
                                  comment=prev_comment,
                                  manager_id="ident",
                                  order_number="1",
                                  inn=ident_val)
                    except Exception as e:
                        log_event("set_state_error", trace_id, error=str(e))
                    log_event("ident_not_found_first", trace_id,
                              user_id=user_id, state=state, topic=topic,
                              ident=ident_val)
                    _send(user_id, TEXT_INN_NOT_FOUND, menu_rows, trace_id)
                    return

                # В тексте нет цифр ИНН/номера договора — смотрим,
                # что именно клиент написал: физлицо / нет ИНН / шум.
                cls = classify_ident_stage(text, trace_id)
                category = cls.get("category", "normal")

                if category == "physical_person":
                    clear_state(user_id)
                    log_event("ident_physical_person", trace_id,
                              user_id=user_id, state=state, topic=topic)
                    _send(user_id, TEXT_PHYSICAL_REFUSE, menu_rows, trace_id)
                    return

                if category == "no_identifier":
                    clear_state(user_id)
                    log_event("ident_no_identifier", trace_id,
                              user_id=user_id, state=state, topic=topic)
                    _send(user_id, TEXT_NO_INN_REFUSE, menu_rows, trace_id)
                    return

                # normal — просто невалидный ответ, переспросим.
                # Два таких подряд — обрыв.
                retry += 1
                if retry >= 2:
                    clear_state(user_id)
                    log_event("ident_terminated_silence", trace_id,
                              user_id=user_id, state=state, topic=topic,
                              retry=retry)
                    _send(user_id, TEXT_TERMINATE_DIFFERENT_IDENT,
                          menu_rows, trace_id)
                    return
                try:
                    set_state(user_id, state, topic=topic,
                              comment=prev_comment,
                              manager_id="ident",
                              order_number=str(retry),
                              inn=prev_ident)
                except Exception as e:
                    log_event("set_state_error", trace_id, error=str(e))
                log_event("ident_retry", trace_id,
                          user_id=user_id, state=state, topic=topic,
                          retry=retry)
                _send(user_id, TEXT_IDENTIFY_FIRST, menu_rows, trace_id)
                return

            # ── Фаза contact / contact_escalate: ждём контакт ──
            if phase in ("contact", "contact_escalate"):
                cls = classify_contact_stage(text, trace_id)

                if cls.get("has_contact"):
                    # Собрали всё — пересылаем по целевому каналу.
                    # Находим клиента по подтверждённому prev_ident, чтобы
                    # передать имя контрагента явно — не полагаясь на повторный
                    # парсинг текста в forwarding.py.
                    client_info = None
                    try:
                        if prev_ident.isdigit() and len(prev_ident) in (10, 12):
                            client_info = find_client_by_inn(prev_ident)
                        else:
                            client_info = find_client_by_contract(prev_ident)
                            if not client_info and prev_ident.isdigit():
                                client_info = find_client_by_inn(prev_ident)
                    except Exception as e:
                        log_event("client_lookup_on_send_error", trace_id,
                                  error=str(e))
                    counterparty_name = (client_info or {}).get("name") or None

                    # Разделяем сообщение клиента на контакт и комментарий
                    # — менеджеру приходит структурированно.
                    contact_val, comment_val = _extract_contact_and_comment(text)
                    fwd_lines = [f"ИНН/Договор: {prev_ident}"]
                    if contact_val:
                        fwd_lines.append(f"Контакт: {contact_val}")
                    else:
                        # regex в классификаторе сработал, но extract не нашёл —
                        # подстрахуемся, отдав сырой текст как контакт.
                        fwd_lines.append(f"Контакт: {text}")
                    if comment_val:
                        fwd_lines.append(f"Комментарий клиента: {comment_val}")
                    forwarded = "\n".join(fwd_lines)
                    if cart_text:
                        forwarded = f"{cart_text}\n\n{forwarded}"

                    clear_state(user_id)

                    # Выходные — автоответ (КЛО работает, остальные — нет).
                    if is_weekend() and state in ("waiting_message", "waiting_buh"):
                        log_event("weekend_autoreply", trace_id,
                                  user_id=user_id, state=state, topic=topic)
                        _send(user_id, TEXT_WEEKEND_AUTOREPLY, menu_rows, trace_id)
                        return

                    if phase == "contact_escalate":
                        # ИНН клиентом подтверждён, но в базе нет — в общий чат.
                        forward_new_client_to_group(user_id, user_name,
                                                     forwarded, topic, trace_id,
                                                     counterparty=counterparty_name)
                    elif state == "waiting_message":
                        forward_to_manager(user_id, user_name,
                                           forwarded, topic, trace_id,
                                           counterparty=counterparty_name)
                    elif state == "waiting_klo":
                        forward_to_klo(user_id, user_name,
                                       forwarded, topic, trace_id,
                                       counterparty=counterparty_name)
                        if topic == "checkout":
                            try:
                                packaging_paid.clear_cart(user_id)
                            except Exception:
                                pass
                    elif state == "waiting_buh":
                        forward_to_accountant(user_id, user_name,
                                              forwarded, topic, trace_id,
                                              counterparty=counterparty_name)

                    _confirm_and_maybe_return_ai(user_id, from_ai, trace_id,
                                                  topic, client_text=text)
                    return

                # Контакт не прислали: явный отказ ИЛИ просто не по теме.
                retry += 1
                if cls.get("refuses_contact") or retry >= 3:
                    clear_state(user_id)
                    log_event("contact_terminated", trace_id,
                              user_id=user_id, state=state, topic=topic,
                              phase=phase, retry=retry,
                              refused=bool(cls.get("refuses_contact")))
                    _send(user_id, TEXT_CONTACT_FINAL, menu_rows, trace_id)
                    return

                try:
                    set_state(user_id, state, topic=topic,
                              comment=prev_comment,
                              manager_id=phase,
                              order_number=str(retry),
                              inn=prev_ident)
                except Exception as e:
                    log_event("set_state_error", trace_id, error=str(e))
                log_event("contact_retry", trace_id,
                          user_id=user_id, state=state, topic=topic,
                          phase=phase, retry=retry)
                _send(user_id, TEXT_CONTACT_RETRY, menu_rows, trace_id)
                return

            # Неизвестная фаза — сбрасываем в ident и начинаем заново.
            log_event("phase_reset", trace_id,
                      user_id=user_id, state=state, phase=phase)
            try:
                set_state(user_id, state, topic=topic,
                          comment=prev_comment,
                          manager_id="ident", order_number="0", inn="")
            except Exception:
                pass
            _send(user_id, TEXT_IDENTIFY_FIRST, menu_rows, trace_id)
            return
            return

    # Нет состояния и не команда → показываем главное меню
    t, rows = _main_menu()
    _send(user_id, t, rows, trace_id)


# ─── Главная точка входа ──────────────────────────────────────────


def handle_update(update: dict, trace_id: str):
    update_type = update.get("update_type")
    log_event("update_received", trace_id, update_type=update_type)

    if update_type == "message_callback":
        _handle_callback(update, trace_id)
        return

    if update_type in ("message_created", "message_command"):
        _handle_text_message(update, trace_id)
        return

    log_event("skip", trace_id, reason="unsupported_update_type", update_type=update_type)