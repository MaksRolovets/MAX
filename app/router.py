"""Главный маршрутизатор обновлений — вся логика бота."""

from app.logger import log_event
from app.max_client import send_message, answer_callback
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


def _confirm_to_client(user_id: int, trace_id=None):
    """Подтверждение клиенту, что запрос принят."""
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
        "Самостоятельно создайте заказ в личном кабинете:\n"
        "https://lk.cdek.ru/user/login\n\n"
        "Или укажите номер договора/ИНН и мы передадим запрос в отдел работы с клиентами."
    )
    rows = [
        [packaging_paid.btn_cb("📝 Указать договор/ИНН", "request_klo")],
        [packaging_paid.btn_cb("◀️ Назад", "category_create_order")],
    ]
    return text, rows


def _create_order_international():
    text = (
        "🌍 **ЕАЭС или международная отправка**\n\n"
        "Укажите номер договора/ИНН, телефон и комментарий."
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
        "🔍 Вы можете отследить ваш заказ по номеру, пройдя по ссылке:\n\n"
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
        "📅 Назначить дату доставки можно в личном кабинете:\n"
        "https://lk.cdek.ru/user/login\n\n"
        "Если нужна помощь — нажмите кнопку ниже."
    )
    rows = [
        [packaging_paid.btn_cb("✅ Нужна помощь", "need_help_cheking")],
        [packaging_paid.btn_cb("◀️ В главное меню", "main_menu")],
    ]
    return text, rows


def _order_edit():
    text = (
        "✏️ Внести изменения можно в ЛК: https://lk.cdek.ru/user/login\n"
        "Если заказ уже сдан, изменение даты невозможно — обратитесь к менеджеру."
    )
    rows = [
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
        "1. Перейдите: https://lk.cdek.ru/user/login\n"
        "2. Нажмите «Не помню пароль»\n"
        "3. Введите номер договора\n"
        "4. Ссылка для восстановления придёт на почту из договора\n\n"
        "Если не помните почту — нажмите кнопку ниже."
    )
    rows = [
        [packaging_paid.btn_cb("✅ Не помню почту", "remem_gmail")],
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
        [packaging_paid.btn_cb("📄 Заказать акт сверки", "finance_act")],
        [packaging_paid.btn_cb("💳 Получить счет", "finance_invoice")],
        [packaging_paid.btn_cb("❓ Вопрос по счету", "finance_question")],
        [packaging_paid.btn_cb("◀️ В главное меню", "main_menu")],
    ]
    return text, rows


def _finance_act():
    text = (
        "📄 **Акт сверки**\n\n"
        "Самостоятельно сформируйте в ЛК:\n"
        "https://lk.cdek.ru/user/login\n"
        "Документы → Запросить акт сверки\n\n"
        "Или укажите период и ИНН/договор."
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
    text = "🆓 **Бесплатная упаковка**\n\nУкажите договор/ИНН и контакт."
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
    "need_help": ("waiting_message", "need_help",
                  "📝 Пожалуйста, напишите данные одним сообщением.\nМы передадим ваш запрос менеджеру."),
    "need_help_with_contact": ("waiting_message", "need_help_with_contact",
                               "📝 Укажите номер договора/ИНН, телефон и комментарий одним сообщением."),
    "callback_request": ("waiting_message", "callback_request",
                         "📞 **Обратный звонок**\n\nУкажите ИНН/договор и ваш вопрос одним сообщением."),
    "feedback": ("waiting_message", "feedback",
                 "⭐ **Оставить отзыв**\n\nУкажите договор/ИНН и ваш отзыв одним сообщением."),
    "contract_renewal": ("waiting_message", "contract_renewal",
                         "📝 **Перезаключить договор**\n\nУкажите договор/ИНН и контакты одним сообщением."),
    "new_services": ("waiting_message", "new_services",
                     "✨ **Подключить услуги**\n\nУкажите договор/ИНН, нужные услуги и контакты одним сообщением."),
    "tracking_solved_no": ("waiting_message", "tracking_solved_no",
                           "❌ Понял. Напишите номер заказа — передадим запрос менеджеру."),
    "tracking_help_yes": ("waiting_message", "tracking_help_yes",
                          "📝 Напишите ваш вопрос одним сообщением."),
    "free_pckaiging_data": ("waiting_message", "free_pckaiging_data",
                            "📝 Укажите ИНН/договор и контакт одним сообщением."),

    # → waiting_klo (пересылка в КЛО)
    "request_klo": ("waiting_klo", "request_klo",
                    "📝 Укажите ИНН или номер договора одним сообщением."),
    "order_other": ("waiting_klo", "order_other",
                    "❓ **Другой вопрос по заказу**\n\nУкажите номер заказа и опишите вопрос."),
    "need_help_with_order": ("waiting_klo", "need_help_with_order",
                             "📝 Укажите номер заказа одним сообщением."),
    "need_help_cheking": ("waiting_klo", "need_help_cheking",
                          "📝 Укажите номер заказа одним сообщением."),

    # → waiting_buh (пересылка бухгалтеру)
    "finance_invoice": ("waiting_buh", "finance_invoice",
                        "💳 **Получить счет**\n\nУкажите ИНН/договор и контактный телефон одним сообщением."),
    "finance_question": ("waiting_buh", "finance_question",
                         "❓ **Вопрос по счету**\n\nУкажите номер счета, телефон и опишите вопрос одним сообщением."),
    "need_help_with_period": ("waiting_buh", "need_help_with_period",
                              "📝 Укажите период, ИНН/договор одним сообщением."),

    # → waiting_pro (пересылка продажнику)
    "contract": ("waiting_pro", "contract",
                 "📄 **Заключить договор**\n\nУкажите название организации, ИНН, сайт и телефон одним сообщением."),
    "need_help_manager": ("waiting_pro", "need_help_manager",
                          "📝 Укажите ИНН или номер договора одним сообщением."),
    "remem_gmail": ("waiting_pro", "remem_gmail",
                    "📝 Укажите ИНН или номер договора одним сообщением."),
}


# ─── Обработка callback-ов ─────────────────────────────────────────


def _handle_callback(update: dict, trace_id: str):
    callback = update.get("callback", {})
    callback_id = callback.get("callback_id")
    payload = callback.get("payload", "")
    user_obj = callback.get("user") or callback.get("from") or {}
    user_id = user_obj.get("user_id") or callback.get("user_id")

    if not callback_id:
        log_event("skip", trace_id, reason="no_callback_id")
        return

    # 1) Главное меню
    if payload in ("main_menu", "menu"):
        text, rows = _main_menu()
        _answer(callback_id, text, rows, trace_id)
        return

    # 2) Простые callback-ы (меню → подменю)
    if payload in SIMPLE_CALLBACKS:
        text, rows = SIMPLE_CALLBACKS[payload]()
        _answer(callback_id, text, rows, trace_id)
        return

    # 3) Callback-ы, которые устанавливают состояние
    if payload in STATE_CALLBACKS:
        state, topic, prompt_text = STATE_CALLBACKS[payload]
        if user_id:
            set_state(user_id, state, topic=topic)
        rows = [[packaging_paid.btn_cb("◀️ В главное меню", "main_menu")]]
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
        # В MAX нет встроенной отправки файлов через answer_callback.
        # Отправляем ссылку или текст-заглушку. Заменить на реальную ссылку на файл.
        text = (
            "📎 **Памятка по работе в ЛК**\n\n"
            "Скачайте памятку по ссылке:\n"
            "https://drive.google.com/file/d/REPLACE_ME_PDF_FILE_ID/view\n\n"
            "Если возникнут вопросы — обращайтесь!"
        )
        rows = [[packaging_paid.btn_cb("◀️ В главное меню", "main_menu")]]
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
        text, rows = packaging_paid.add_to_cart(user_id or 0, item_id, qty)
        _answer(callback_id, text, rows, trace_id)
        return

    if payload == "seek_cart":
        text, rows = packaging_paid.view_cart(user_id or 0)
        _answer(callback_id, text, rows, trace_id)
        return

    if payload == "clear_cart":
        text, rows = packaging_paid.clear_cart(user_id or 0)
        _answer(callback_id, text, rows, trace_id)
        return

    if payload == "checkout":
        # Корзина → оформление: формируем текст корзины, просим ИНН
        cart_text, _ = packaging_paid.view_cart(user_id or 0)
        if user_id:
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

        # ── Обычные состояния: пересылка ──
        clear_state(user_id)

        if state == "waiting_message":
            forward_to_manager(user_id, user_name, text, topic, trace_id)
            _confirm_to_client(user_id, trace_id)
            return

        if state == "waiting_klo":
            # Если это checkout — добавляем текст корзины
            full_text = text
            if topic == "checkout" and prev_comment:
                full_text = f"{prev_comment}\n\nИНН/Договор: {text}"
            forward_to_klo(user_id, user_name, full_text, topic, trace_id)
            _confirm_to_client(user_id, trace_id)
            # Если это checkout — очищаем корзину
            if topic == "checkout":
                try:
                    packaging_paid.clear_cart(user_id)
                except Exception:
                    pass
            return

        if state == "waiting_buh":
            forward_to_accountant(user_id, user_name, text, topic, trace_id)
            _confirm_to_client(user_id, trace_id)
            return

        if state == "waiting_pro":
            forward_to_sales(user_id, user_name, text, topic, trace_id)
            _confirm_to_client(user_id, trace_id)
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
