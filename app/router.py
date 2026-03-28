from app.logger import log_event
from app.max_client import send_message, answer_callback
from app.nodes import packaging_paid


def _make_message(text: str, rows: list[list[dict]] | None):
    body = {
        "text": text,
        "format": "markdown",
    }
    if rows:
        body["attachments"] = packaging_paid.keyboard(rows)
    return body


def _node_start(trace_id: str, name: str, **data):
    log_event("node_start", trace_id, node=name, **data)


def _node_end(trace_id: str, name: str, **data):
    log_event("node_end", trace_id, node=name, **data)


def _main_menu():
    text = "👋 Здравствуйте! Я бот компании. Чем могу помочь?\n\nВыберите категорию вопроса:"
    rows = [
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


def _lk_menu():
    text = "🔑 **Личный кабинет**\n\nВыберите что вас интересует:"
    rows = [
        [packaging_paid.btn_cb("🔐 Восстановить доступ", "lk_restore")],
        [packaging_paid.btn_cb("📚 Обучение работе в ЛК", "lk_training")],
        [packaging_paid.btn_cb("◀️ В главное меню", "main_menu")],
    ]
    return text, rows


def _finance_menu():
    text = "💰 **Взаиморасчёты**\n\nВыберите что вас интересует:"
    rows = [
        [packaging_paid.btn_cb("📄 Заказать акт сверки", "finance_act")],
        [packaging_paid.btn_cb("💳 Получить счет", "finance_invoice")],
        [packaging_paid.btn_cb("❓ Вопрос по счету", "finance_question")],
        [packaging_paid.btn_cb("◀️ В главное меню", "main_menu")],
    ]
    return text, rows


def handle_update(update: dict, trace_id: str):
    update_type = update.get("update_type")
    log_event("update_received", trace_id, update_type=update_type)

    if update_type in ("message_created", "message_command"):
        message = update.get("message") or update.get("command") or {}
        sender = message.get("sender") or update.get("sender") or {}
        user_id = sender.get("user_id") or message.get("user_id") or update.get("user_id")
        if not user_id:
            log_event("skip", trace_id, reason="no_user_id")
            return

        text, rows = _main_menu()
        _node_start(trace_id, "Главное меню")
        send_message(user_id, _make_message(text, rows), trace_id)
        _node_end(trace_id, "Главное меню")
        return

    if update_type != "message_callback":
        log_event("skip", trace_id, reason="unsupported_update_type")
        return

    callback = update.get("callback", {})
    callback_id = callback.get("callback_id")
    payload = callback.get("payload", "")
    user_id = callback.get("user", {}).get("user_id") or callback.get("from", {}).get("user_id")

    if not callback_id:
        log_event("skip", trace_id, reason="no_callback_id")
        return

    if payload in ("main_menu", "menu"):
        text, rows = _main_menu()
        _node_start(trace_id, "Главное меню")
        answer_callback(callback_id, {"message": _make_message(text, rows)}, trace_id)
        _node_end(trace_id, "Главное меню")
        return

    if payload == "category_order":
        text, rows = _order_menu()
        _node_start(trace_id, "Подменю: Заказы")
        answer_callback(callback_id, {"message": _make_message(text, rows)}, trace_id)
        _node_end(trace_id, "Подменю: Заказы")
        return

    if payload == "category_lk":
        text, rows = _lk_menu()
        _node_start(trace_id, "Подменю: ЛК")
        answer_callback(callback_id, {"message": _make_message(text, rows)}, trace_id)
        _node_end(trace_id, "Подменю: ЛК")
        return

    if payload == "category_finance":
        text, rows = _finance_menu()
        _node_start(trace_id, "Подменю: Финансы")
        answer_callback(callback_id, {"message": _make_message(text, rows)}, trace_id)
        _node_end(trace_id, "Подменю: Финансы")
        return

    if payload == "category_packaging":
        _node_start(trace_id, "Подменю: Упаковка")
        text = "📦 **Заказ упаковки**\n\nВыберите тип:"
        rows = [
            [packaging_paid.btn_cb("💰 Платная", "packaging_paid")],
            [packaging_paid.btn_cb("🆓 Бесплатная", "packaging_free")],
            [packaging_paid.btn_cb("◀️ В главное меню", "main_menu")],
        ]
        answer_callback(callback_id, {"message": _make_message(text, rows)}, trace_id)
        _node_end(trace_id, "Подменю: Упаковка")
        return

    if payload == "packaging_paid":
        _node_start(trace_id, "Каталог товаров")
        text, rows = packaging_paid.categories_menu()
        _node_end(trace_id, "Каталог товаров")

        _node_start(trace_id, "формирование ответа")
        body = {"message": _make_message(text, rows)}
        _node_end(trace_id, "формирование ответа")

        _node_start(trace_id, "Отправка категорий")
        answer_callback(callback_id, body, trace_id)
        _node_end(trace_id, "Отправка категорий")
        return

    if payload.startswith("cat_"):
        category = payload.replace("cat_", "")
        _node_start(trace_id, "Категория", category=category)
        _node_end(trace_id, "Категория", category=category)

        _node_start(trace_id, "Товары категории", category=category)
        text, rows = packaging_paid.items_menu(category)
        _node_end(trace_id, "Товары категории", category=category)

        _node_start(trace_id, "Товары категории1", category=category)
        answer_callback(callback_id, {"message": _make_message(text, rows)}, trace_id)
        _node_end(trace_id, "Товары категории1", category=category)
        return

    if payload.startswith("item_"):
        item_id = payload.replace("item_", "")
        _node_start(trace_id, "Управление карточкой", item_id=item_id)
        text, rows = packaging_paid.item_card(item_id, 1)
        _node_end(trace_id, "Управление карточкой", item_id=item_id)

        _node_start(trace_id, "Карточка товара1", item_id=item_id)
        answer_callback(callback_id, {"message": _make_message(text, rows)}, trace_id)
        _node_end(trace_id, "Карточка товара1", item_id=item_id)
        return

    if payload.startswith("inc:") or payload.startswith("dec:"):
        parts = payload.split(":")
        action = parts[0]
        item_id = parts[1] if len(parts) > 1 else ""
        qty = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 1

        _node_start(trace_id, "Управление карточкой", item_id=item_id, action=action, qty=qty)
        text, rows = packaging_paid.adjust_qty(item_id, qty, action)
        _node_end(trace_id, "Управление карточкой", item_id=item_id, action=action, qty=qty)

        _node_start(trace_id, "Карточка товара2", item_id=item_id)
        answer_callback(callback_id, {"message": _make_message(text, rows)}, trace_id)
        _node_end(trace_id, "Карточка товара2", item_id=item_id)
        return

    if payload.startswith("add:"):
        parts = payload.split(":")
        item_id = parts[1] if len(parts) > 1 else ""
        qty = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 1

        _node_start(trace_id, "Определение количества", item_id=item_id, qty=qty)
        text, rows = packaging_paid.add_to_cart(user_id or 0, item_id, qty)
        _node_end(trace_id, "Определение количества", item_id=item_id, qty=qty)

        _node_start(trace_id, "Append row in sheet12", item_id=item_id, qty=qty)
        _node_end(trace_id, "Append row in sheet12", item_id=item_id, qty=qty)

        _node_start(trace_id, "Send a text message", item_id=item_id)
        answer_callback(callback_id, {"message": _make_message(text, rows)}, trace_id)
        _node_end(trace_id, "Send a text message", item_id=item_id)
        return

    if payload == "seek_cart":
        _node_start(trace_id, "Get row(s) in sheet1")
        _node_end(trace_id, "Get row(s) in sheet1")

        _node_start(trace_id, "Преобразователь строк")
        text, rows = packaging_paid.view_cart(user_id or 0)
        _node_end(trace_id, "Преобразователь строк")

        _node_start(trace_id, "Просмотр корзины")
        _node_end(trace_id, "Просмотр корзины")

        _node_start(trace_id, "Send a text message1")
        answer_callback(callback_id, {"message": _make_message(text, rows)}, trace_id)
        _node_end(trace_id, "Send a text message1")
        return

    if payload == "clear_cart":
        _node_start(trace_id, "Get row(s) in sheet3")
        _node_end(trace_id, "Get row(s) in sheet3")

        _node_start(trace_id, "преобразователь строки")
        _node_end(trace_id, "преобразователь строки")

        _node_start(trace_id, "Delete rows or columns from sheet")
        text, rows = packaging_paid.clear_cart(user_id or 0)
        _node_end(trace_id, "Delete rows or columns from sheet")

        _node_start(trace_id, "Send a text message2")
        answer_callback(callback_id, {"message": _make_message(text, rows)}, trace_id)
        _node_end(trace_id, "Send a text message2")
        return

    if payload == "checkout":
        _node_start(trace_id, "Append row in sheet13")
        _node_end(trace_id, "Append row in sheet13")

        _node_start(trace_id, "Ответ: Запрос данных (универсальный)2")
        text = "📝 Пожалуйста, напишите ваш ИНН одним сообщением."
        rows = [[packaging_paid.btn_cb("◀️ В главное меню", "main_menu")]]
        answer_callback(callback_id, {"message": _make_message(text, rows)}, trace_id)
        _node_end(trace_id, "Ответ: Запрос данных (универсальный)2")
        return

    _node_start(trace_id, "unknown_callback", payload=payload)
    answer_callback(
        callback_id,
        {"message": _make_message(f"Получен callback: `{payload}`", [[packaging_paid.btn_cb("◀️ В главное меню", "main_menu")]])},
        trace_id,
    )
    _node_end(trace_id, "unknown_callback")


