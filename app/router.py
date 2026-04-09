"""Главный маршрутизатор обновлений — вся логика бота."""

import os

from app.logger import log_event
from app.max_client import send_message, answer_callback, upload_local_file, send_message_with_file
from app.nodes import packaging_paid
from app import settings
from app.sheets_states import set_state, get_state, clear_state
from app.sheets_messages import find_client_by_message
from app.forwarding import (
    forward_to_manager, forward_to_klo, forward_to_accountant,
    forward_to_sales, forward_manager_reply_to_client,
)
from app.sheets_clients import (
    update_manager_for_clients, update_manager_id,
)
from app.ai_client import ask_ai, parse_state_command, clear_conversation

# ─── Текстовые константы промптов (обновлено по скриншоту + новые правки) ────────────────────────────────

TEXT_REQUEST_UNIVERSAL = "📝 Пожалуйста, напишите данные одним сообщением.\nМы передадим ваш запрос менеджеру."
TEXT_TRACKING_NO = "📝 Напишите номер Вашего договора или ИНН, а также номер заказа одним сообщением.\nВаш запрос будет передан менеджеру и с вами скоро свяжутся!"
TEXT_CALLBACK_REQUEST = "📞 **Обратный звонок**\n\nВ сообщении укажите Ваш ИНН или номер договора, а также интересующий Вас вопрос или проблему. Мы передадим информацию менеджеру."
TEXT_FEEDBACK = "⭐ **Оставить отзыв**\n\nВ сообщении укажите номер Вашего ИНН или договора и напишите отзыв. Мы передадим информацию менеджеру."
TEXT_CONTRACT_RENEWAL = "📝 **Перезаключить договор**\n\nУкажите номер договора или ИНН, а также почту или мобильный телефон и мы передадим запрос менеджеру."
TEXT_NEW_SERVICES = "✨ **Подключить услуги**\n\nУкажите в сообщении номер Вашего договора или ИНН, а также опишите какая услуга(и) Вам требуется. Мы отправим Ваш запрос менеджеру."
TEXT_FREE_BOX = "🆓 **Бесплатная упаковка**\n\nУкажите Ваш номер ИНН или договора, почту или мобильный телефон, а также в сообщении кратко укажите потребность в количестве и типе упаковки. Мы передадим запрос менеджеру."
TEXT_REQUEST_ORDER_AND_INN = "📝 Укажите номер заказа, а также ИНН или номер договора одним сообщением.\nВаш запрос будет передан менеджеру и с вами скоро свяжутся!"
TEXT_REQUEST_KLO = "📝 Напишите ваш номер договора или ИНН, а также комментарий — какая точно помощь вам нужна?\nМы передадим запрос менеджеру."
TEXT_ORDER_OTHER = "❓ **Другой вопрос по заказу**\n\n🔢 Пожалуйста, укажите номер заказа и опишите ваш вопрос подробно одним сообщением.\nМы передадим запрос в отдел по работе с клиентами."
TEXT_INTERNATIONAL = "🌍 **ЕАЭС или международная отправка**\n\nУкажите номер вашего договора или ИНН, а также телефон.\nДополнительно в комментарии просим указать маршрут, краткие параметры и тип груза.\nМы передадим запрос менеджеру."
TEXT_FINANCE_INVOICE = "💳 **Получить счет**\n\nУкажите в сообщении Ваш ИНН или номер договора, а также контактный телефон. Мы передадим запрос менеджеру."
TEXT_FINANCE_QUESTION = "❓ **Вопрос по счету**\n\nУкажите в сообщении Ваш ИНН или номер договора, номер счета и контактный телефон, а также напишите интересующий вопрос. Мы передадим информацию менеджеру."
TEXT_FINANCE_PERIOD = (
    "📝 Укажите период (ДД.ММ.ГГГГ - ДД.ММ.ГГГГ), ваш ИНН или номер договора одним сообщением."
)

TEXT_NEED_HELP_DATE_DELIVERY = (
    "📝 Пожалуйста, укажите номер заказа, а также Ваш ИНН или номер договора для уточнения информации.\nМы передадим Ваш запрос менеджеру."
)

TEXT_CONFIRM_FORWARD_MANAGER = "✅ Ваш запрос будет передан менеджеру и с Вами скоро свяжутся!"
TEXT_CONTRACT = "📄 **Заключить договор**\n\nУкажите название организации, ИНН, сайт и телефон одним сообщением. Мы передадим Ваш запрос менеджеру и свяжемся с Вами."
TEXT_HELP_MANAGER = "📝 Укажите Ваш ИНН или номер договора одним сообщением, а также контактный телефон. Мы передадим запрос менеджеру."
TEXT_REMEM_GMAIL = "📝 Укажите Ваш ИНН или номер договора одним сообщением, а также контактный телефон. Мы передадим запрос менеджеру."


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


def _confirm_to_client(user_id: int, trace_id=None, topic: str | None = None):
    """Подтверждение клиенту, что запрос принят."""
    if topic in ("request_klo", "need_help_cheking", "need_help"):
        text = TEXT_CONFIRM_FORWARD_MANAGER
    else:
        text = "✅ Ваш запрос принят! Менеджер свяжется с вами в ближайшее время."
    rows = [[packaging_paid.btn_cb("◀️ В главное меню", "main_menu")]]
    _send(user_id, text, rows, trace_id)


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
        "Самостоятельно за несколько минут создайте заказ в личном кабинете:\n"
        "https://lk.cdek.ru/user/login\n\n"
        "Или укажите ваш номер договора или ИНН и мы передадим запрос в отдел работы с клиентами."
    )
    rows = [
        [packaging_paid.btn_cb("📝 Указать договор/ИНН", "request_klo")],
        [packaging_paid.btn_cb("◀️ Назад", "category_create_order")],
    ]
    return text, rows


def _create_order_international():
    text = (
        "🌍 **ЕАЭС или международная отправка**\n\n"
        "Укажите номер вашего договора или ИНН, а также телефон.\n"
        "Дополнительно в комментарии просим указать маршрут, краткие параметры и тип груза.\n"
        "Мы передадим запрос менеджеру."
    )
    rows = [
        [packaging_paid.btn_cb("📝 Указать данные + комментарий", "need_help_with_contact")],
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
        "📅 Назначить дату доставки можно в личном кабинете по ссылке https://lk.cdek.ru/user/login\n"
        "Войдите в личный кабинет и выберите там удобную дату.\n"
        "Если нужна помощь — напишите нам."
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
        "и мы передадим запрос в отдел по работе с клиентами."
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
        "Если не помните почту — напишите нам."
    )
    rows = [
        [packaging_paid.btn_cb("✉️ Написать нам", "remem_gmail")],
        [packaging_paid.btn_cb("◀️ В главное меню", "main_menu")],
    ]
    return text, rows


def _lk_training():
    text = "📚 **Обучение работе в ЛК**\n\nМы можем отправить памятку или передать запрос менеджеру."
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
        "Самостоятельно сформируйте в личном кабинете:\n"
        "https://lk.cdek.ru/user/login\n"
        'Раздел **«Документы»** → **«Запросить акт сверки»**\n\n'
        "Или укажите период (ДД.ММ.ГГГГ - ДД.ММ.ГГГГ), ваш ИНН или номер договора, "
        "и мы передадим ваш запрос менеджеру."
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
    text = TEXT_FREE_BOX
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
STATE_CALLBACKS = {
    # → waiting_message (пересылка менеджеру через ИНН-поиск)
    "need_help": ("waiting_message", "need_help", TEXT_REQUEST_ORDER_AND_INN),
    "need_help_with_contact": ("waiting_message", "need_help_with_contact", TEXT_INTERNATIONAL),
    "callback_request": ("waiting_message", "callback_request", TEXT_CALLBACK_REQUEST),
    "feedback": ("waiting_message", "feedback", TEXT_FEEDBACK),
    "contract_renewal": ("waiting_message", "contract_renewal", TEXT_CONTRACT_RENEWAL),
    "new_services": ("waiting_message", "new_services", TEXT_NEW_SERVICES),
    "tracking_solved_no": ("waiting_message", "tracking_solved_no", TEXT_TRACKING_NO),
    "tracking_help_yes": ("waiting_message", "tracking_help_yes", TEXT_REQUEST_UNIVERSAL),
    "free_pckaiging_data": ("waiting_message", "free_pckaiging_data", TEXT_FREE_BOX),
    # → waiting_klo (пересылка в КЛО)
    "request_klo": ("waiting_klo", "request_klo", TEXT_REQUEST_KLO),
    "order_other": ("waiting_klo", "order_other", TEXT_ORDER_OTHER),
    "need_help_with_order": ("waiting_klo", "need_help_with_order", TEXT_REQUEST_ORDER_AND_INN),
    "need_help_cheking": ("waiting_klo", "need_help_cheking", TEXT_NEED_HELP_DATE_DELIVERY),

    # → waiting_buh (пересылка бухгалтеру)
    "finance_invoice": ("waiting_buh", "finance_invoice", TEXT_FINANCE_INVOICE),
    "finance_question": ("waiting_buh", "finance_question", TEXT_FINANCE_QUESTION),
    "need_help_with_period": ("waiting_buh", "need_help_with_period", TEXT_FINANCE_PERIOD),

    # → waiting_pro (пересылка продажнику)
    "contract": ("waiting_pro", "contract", TEXT_CONTRACT),
    "need_help_manager": ("waiting_pro", "need_help_manager", TEXT_HELP_MANAGER),
    "remem_gmail": ("waiting_pro", "remem_gmail", TEXT_REMEM_GMAIL),
}

# ─── Обработка callback-ов ─────────────────────────────────────────


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
            "🤖 **Виртуальный помощник**\n\n"
            "Здравствуйте! Я виртуальный помощник компании СДЭК.\n"
            "Задайте ваш вопрос, и я постараюсь помочь.\n\n"
            "Чтобы завершить разговор, нажмите кнопку ниже."
        )
        rows = [[packaging_paid.btn_cb("❌ Закончить разговор", "stop_ai")]]
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

    # 3) Callback-формы (режим ожидания ввода)
    if payload in STATE_CALLBACKS:
        state, topic, prompt_text = STATE_CALLBACKS[payload]
        if user_id is not None:
            try:
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
        # Корзина → оформление: формируем текст корзины, просим ИНН
        uid = user_id if user_id is not None else 0
        if user_id is None:
            log_event("callback_no_user_id", trace_id, payload=payload)
        cart_text, _ = packaging_paid.view_cart(uid)
        if user_id is not None:
            set_state(user_id, "waiting_klo", topic="checkout", comment=cart_text)
        text = "📝 Пожалуйста, напишите ваш ИНН одним сообщением."
        rows = [[packaging_paid.btn_cb("◀️ В главное меню", "main_menu")]]
        _answer(callback_id, text, rows, trace_id)
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

    # Команда /start → главное меню
    if text.strip().lower() in ("/start", "/menu", "start", "начать"):
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

    # Проверяем, есть ли ответ менеджера (reply на сообщение бота)
    link = message.get("link") or message.get("reply_to") or {}
    linked_mid = link.get("mid") or link.get("message_id") or ""
    if linked_mid:
        try:
            client_info = find_client_by_message(str(linked_mid))
            if client_info and client_info.get("client_user_id"):
                forward_manager_reply_to_client(client_info["client_user_id"], text, trace_id)
                return
        except Exception:
            pass

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
                      [[packaging_paid.btn_cb("❌ Закончить разговор", "stop_ai")]],
                      trace_id)
                return

            clean_text, ai_state, ai_topic = parse_state_command(ai_response)

            if ai_state and ai_topic:
                # AI решил передать запрос сотруднику — выходим из ai_mode
                set_state(user_id, ai_state, topic=ai_topic)
                _send(user_id, clean_text, trace_id=trace_id)
            else:
                # Обычный ответ AI — кнопка завершения всегда внизу
                rows = [[packaging_paid.btn_cb("❌ Закончить разговор", "stop_ai")]]
                _send(user_id, clean_text, rows, trace_id)
            return

        # ── Обычные состояния: пересылка ──
        clear_state(user_id)

        if state == "waiting_message":
            forward_to_manager(user_id, user_name, text, topic, trace_id)
            _confirm_to_client(user_id, trace_id, topic=topic)
            return

        if state == "waiting_klo":
            # Если это checkout — добавляем текст корзины
            full_text = text
            if topic == "checkout" and prev_comment:
                full_text = f"{prev_comment}\n\nИНН/Договор: {text}"
            forward_to_klo(user_id, user_name, full_text, topic, trace_id)
            _confirm_to_client(user_id, trace_id, topic=topic)
            # Если это checkout — очищаем корзину
            if topic == "checkout":
                try:
                    packaging_paid.clear_cart(user_id)
                except Exception:
                    pass
            return

        if state == "waiting_buh":
            forward_to_accountant(user_id, user_name, text, topic, trace_id)
            _confirm_to_client(user_id, trace_id, topic=topic)
            return

        if state == "waiting_pro":
            forward_to_sales(user_id, user_name, text, topic, trace_id)
            _confirm_to_client(user_id, trace_id, topic=topic)
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