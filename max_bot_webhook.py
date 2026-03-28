import requests
from fastapi import FastAPI, Request

API_BASE = "https://platform-api.max.ru"
TOKEN = "f9LHodD0cOLgf_0buCip0sDbatL0euGdP2f6NBNbTBx8tBc9_bXK8r5jVOKt06lDVrVCK6IIRBf_LWwnHbjh"

app = FastAPI()


def auth_headers():
    return {
        "Authorization": TOKEN,
        "Content-Type": "application/json",
    }


def btn_cb(text: str, payload: str) -> dict:
    return {"type": "callback", "text": text, "payload": payload}


def btn_link(text: str, url: str) -> dict:
    return {"type": "link", "text": text, "url": url}


def make_keyboard(rows: list[list[dict]] | None) -> list[dict] | None:
    if not rows:
        return None
    return [{"type": "inline_keyboard", "payload": {"buttons": rows}}]


def send_message(user_id: int, text: str, rows: list[list[dict]] | None = None) -> None:
    payload = {
        "text": text,
        "format": "markdown",
    }
    attachments = make_keyboard(rows)
    if attachments:
        payload["attachments"] = attachments
    requests.post(
        f"{API_BASE}/messages",
        params={"user_id": user_id},
        headers=auth_headers(),
        json=payload,
        timeout=10,
    )


def answer_callback(callback_id: str, text: str | None = None, rows: list[list[dict]] | None = None) -> None:
    body: dict = {"notification": "OK"}
    if text is not None:
        message: dict = {"text": text, "format": "markdown"}
        attachments = make_keyboard(rows)
        if attachments:
            message["attachments"] = attachments
        body["message"] = message
    requests.post(
        f"{API_BASE}/answers",
        params={"callback_id": callback_id},
        headers=auth_headers(),
        json=body,
        timeout=10,
    )


def main_menu() -> tuple[str, list[list[dict]]]:
    text = "👋 Здравствуйте! Я бот компании. Чем могу помочь?\n\nВыберите категорию вопроса:"
    rows = [
        [btn_cb("📦 Вопрос по заказу", "category_order")],
        [btn_cb("🔑 Вопрос по личному кабинету", "category_lk")],
        [btn_cb("💰 Вопрос по взаиморасчётам", "category_finance")],
        [btn_cb("📦 Заказ упаковки", "category_packaging")],
        [btn_cb("📞 Обратный звонок менеджера", "callback_request")],
        [btn_cb("✨ Подключить услуги", "new_services")],
        [btn_cb("📝 Перезаключить договор", "contract_renewal")],
        [btn_cb("📄 Заключить договор", "contract")],
        [btn_cb("⭐ Оставить отзыв", "feedback")],
    ]
    return text, rows


def create_order_menu() -> tuple[str, list[list[dict]]]:
    text = "📦 **Создание заказа**\n\nВыберите тип отправки:"
    rows = [
        [btn_cb("🇷🇺 По РФ", "create_order_rf")],
        [btn_cb("🌍 ЕАЭС или международная", "create_order_international")],
        [btn_cb("◀️ Назад", "main_menu")],
    ]
    return text, rows


def order_questions_menu() -> tuple[str, list[list[dict]]]:
    text = "📦 **Вопросы по заказу**\n\nВыберите что вас интересует:"
    rows = [
        [btn_cb("🔍 Отследить заказ", "order_track")],
        [btn_cb("📅 Назначить дату доставки", "order_date")],
        [btn_cb("✏️ Внести изменения в заказ", "order_edit")],
        [btn_cb("❓ Другой вопрос по заказу", "order_other")],
        [btn_cb("◀️ В главное меню", "main_menu")],
    ]
    return text, rows


def lk_menu() -> tuple[str, list[list[dict]]]:
    text = "🔑 **Личный кабинет**\n\nВыберите что вас интересует:"
    rows = [
        [btn_cb("🔐 Восстановить доступ", "lk_restore")],
        [btn_cb("📚 Обучение работе в ЛК", "lk_training")],
        [btn_cb("◀️ В главное меню", "main_menu")],
    ]
    return text, rows


def finance_menu() -> tuple[str, list[list[dict]]]:
    text = "💰 **Взаиморасчёты**\n\nВыберите что вас интересует:"
    rows = [
        [btn_cb("📄 Заказать акт сверки", "finance_act")],
        [btn_cb("💳 Получить счет", "finance_invoice")],
        [btn_cb("❓ Вопрос по счету", "finance_question")],
        [btn_cb("◀️ В главное меню", "main_menu")],
    ]
    return text, rows


def packaging_menu() -> tuple[str, list[list[dict]]]:
    text = "📦 **Заказ упаковки**\n\nВыберите тип:"
    rows = [
        [btn_cb("💰 Платная", "packaging_paid")],
        [btn_cb("🆓 Бесплатная", "packaging_free")],
        [btn_cb("◀️ В главное меню", "main_menu")],
    ]
    return text, rows


def get_response_for_payload(payload: str) -> tuple[str, list[list[dict]] | None]:
    if payload in ("main_menu", "menu"):
        return main_menu()

    if payload == "category_create_order":
        return create_order_menu()
    if payload == "create_order_rf":
        text = (
            "🇷🇺 **Заказ по РФ**\n\n"
            "Самостоятельно создайте заказ в личном кабинете:\n"
            "https://lk.cdek.ru/user/login\n\n"
            "Или укажите номер договора/ИНН и мы передадим запрос в отдел работы с клиентами."
        )
        rows = [
            [btn_cb("📝 Указать договор/ИНН", "request_klo")],
            [btn_cb("◀️ Назад", "category_create_order")],
        ]
        return text, rows
    if payload == "create_order_international":
        text = (
            "🌍 **ЕАЭС или международная отправка**\n\n"
            "Укажите номер договора/ИНН, телефон и комментарий."
        )
        rows = [
            [btn_cb("📝 Указать данные + комментарий", "need_help_with_contact")],
            [btn_cb("◀️ Назад", "category_create_order")],
        ]
        return text, rows

    if payload == "category_order":
        return order_questions_menu()
    if payload == "order_track":
        text = (
            "🔍 Вы можете отследить ваш заказ по номеру, пройдя по ссылке:\n\n"
            "https://www.cdek.ru/ru/tracking\n\n"
            "❓ **Вопрос решен?**"
        )
        rows = [
            [btn_cb("✅ Да", "tracking_solved_yes")],
            [btn_cb("❌ Нет", "tracking_solved_no")],
        ]
        return text, rows
    if payload == "order_date":
        text = (
            "📅 Назначить дату доставки можно в личном кабинете:\n"
            "https://lk.cdek.ru/user/login\n\n"
            "Если нужна помощь — напишите нам."
        )
        rows = [
            [btn_cb("✅ Нужна помощь", "need_help_cheking")],
            [btn_cb("◀️ В главное меню", "main_menu")],
        ]
        return text, rows
    if payload == "order_edit":
        text = (
            "✏️ Внести изменения: https://lk.cdek.ru/user/login\n"
            "Если заказ уже сдан, изменение даты невозможно — обратитесь к менеджеру."
        )
        rows = [
            [btn_cb("✅ Нужна помощь", "need_help")],
            [btn_cb("◀️ В главное меню", "main_menu")],
        ]
        return text, rows
    if payload == "order_other":
        text = (
            "❓ Другой вопрос по заказу\n\n"
            "Пожалуйста, укажите номер заказа и опишите вопрос."
        )
        rows = [[btn_cb("◀️ В главное меню", "main_menu")]]
        return text, rows

    if payload == "category_lk":
        return lk_menu()
    if payload == "lk_restore":
        text = (
            "🔐 **Восстановление доступа**\n\n"
            "1. https://lk.cdek.ru/user/login\n"
            "2. Нажмите «Не помню пароль»\n"
            "3. Введите номер договора\n"
            "4. Ссылка придет на почту из договора\n\n"
            "Если не помните почту — напишите нам."
        )
        rows = [
            [btn_cb("✅ Не помню почту", "remem_gmail")],
            [btn_cb("◀️ В главное меню", "main_menu")],
        ]
        return text, rows
    if payload == "lk_training":
        text = "📚 **Обучение работе в ЛК**\n\nМы можем отправить памятку или передать запрос менеджеру."
        rows = [
            [btn_cb("📎 Получить памятку", "get_pdf")],
            [btn_cb("👤 Помощь менеджера", "need_help")],
            [btn_cb("◀️ В главное меню", "main_menu")],
        ]
        return text, rows

    if payload == "category_finance":
        return finance_menu()
    if payload == "finance_act":
        text = (
            "📄 **Акт сверки**\n\n"
            "Самостоятельно сформируйте в ЛК:\n"
            "https://lk.cdek.ru/user/login\n"
            "Документы → Запросить акт сверки\n\n"
            "Или укажите период и ИНН/договор."
        )
        rows = [
            [btn_cb("📝 Указать период", "need_help_with_period")],
            [btn_cb("◀️ В главное меню", "main_menu")],
        ]
        return text, rows
    if payload == "finance_invoice":
        text = "💳 **Получить счет**\n\nУкажите ИНН/договор и контактный телефон."
        rows = [[btn_cb("◀️ В главное меню", "main_menu")]]
        return text, rows
    if payload == "finance_question":
        text = "❓ **Вопрос по счету**\n\nУкажите номер счета и телефон, опишите вопрос."
        rows = [
            [btn_cb("📝 Задать вопрос", "need_help")],
            [btn_cb("◀️ В главное меню", "main_menu")],
        ]
        return text, rows

    if payload == "category_packaging":
        return packaging_menu()
    if payload == "packaging_paid":
        text = "💰 **Платная упаковка**\n\nВыберите категорию или товар."
        rows = [
            [btn_cb("📦 Категории", "cat_list")],
            [btn_cb("◀️ В главное меню", "main_menu")],
        ]
        return text, rows
    if payload == "packaging_free":
        text = "🆓 **Бесплатная упаковка**\n\nУкажите договор/ИНН и контакт."
        rows = [
            [btn_cb("📝 Указать данные", "free_pckaiging_data")],
            [btn_cb("◀️ В главное меню", "main_menu")],
        ]
        return text, rows

    if payload.startswith("cat_"):
        category = payload.replace("cat_", "")
        text = f"📦 Категория: **{category}**\n\nВыберите товар (тест)."
        rows = [
            [btn_cb("🔹 Товар 1", "item_demo_1")],
            [btn_cb("🔹 Товар 2", "item_demo_2")],
            [btn_cb("◀️ Назад", "packaging_paid")],
        ]
        return text, rows
    if payload.startswith("item_"):
        item_id = payload.replace("item_", "")
        text = f"📦 Товар: **{item_id}**\n\nКоличество: 1"
        rows = [
            [btn_cb("➖", f"dec:{item_id}:1"), btn_cb("1", "noop"), btn_cb("➕", f"inc:{item_id}:1")],
            [btn_cb("✅ Добавить в корзину", f"add:{item_id}:1")],
            [btn_cb("◀️ Назад", "packaging_paid")],
        ]
        return text, rows
    if payload.startswith("inc:") or payload.startswith("dec:"):
        text = "🔁 Количество обновлено (тест без БД)."
        rows = [[btn_cb("◀️ Назад", "packaging_paid")]]
        return text, rows
    if payload.startswith("add:"):
        text = "✅ Товар добавлен в корзину (тест без БД)."
        rows = [
            [btn_cb("🛒 Просмотр корзины", "seek_cart")],
            [btn_cb("📦 Продолжить выбор", "packaging_paid")],
        ]
        return text, rows
    if payload == "seek_cart":
        text = "🛒 Корзина пуста (в тестовом режиме без БД)."
        rows = [
            [btn_cb("📦 В каталог", "packaging_paid")],
            [btn_cb("◀️ В главное меню", "main_menu")],
        ]
        return text, rows
    if payload == "clear_cart":
        text = "🧹 Корзина очищена (тест)."
        rows = [[btn_cb("◀️ В главное меню", "main_menu")]]
        return text, rows
    if payload == "checkout":
        text = "✅ Заказ оформлен (тест). Менеджер свяжется с вами."
        rows = [[btn_cb("◀️ В главное меню", "main_menu")]]
        return text, rows

    if payload == "contract":
        text = (
            "📝 **Заключить договор**\n\n"
            "Укажите название организации, ИНН, сайт и телефон."
        )
        rows = [[btn_cb("◀️ В главное меню", "main_menu")]]
        return text, rows
    if payload == "contract_renewal":
        text = "📝 **Перезаключить договор**\n\nУкажите договор/ИНН и контакты."
        rows = [[btn_cb("◀️ В главное меню", "main_menu")]]
        return text, rows
    if payload == "callback_request":
        text = "📞 **Обратный звонок**\n\nУкажите ИНН/договор и ваш вопрос."
        rows = [[btn_cb("◀️ В главное меню", "main_menu")]]
        return text, rows
    if payload == "new_services":
        text = "✨ **Подключить услуги**\n\nУкажите договор/ИНН и контакты."
        rows = [[btn_cb("◀️ В главное меню", "main_menu")]]
        return text, rows
    if payload == "feedback":
        text = "⭐ **Оставить отзыв**\n\nУкажите договор/ИНН и ваш отзыв."
        rows = [[btn_cb("◀️ В главное меню", "main_menu")]]
        return text, rows

    if payload in ("need_help", "need_help_with_contact", "need_help_with_period", "need_help_with_order"):
        text = "📝 Пожалуйста, напишите данные одним сообщением. Мы передадим ваш запрос менеджеру."
        rows = [[btn_cb("◀️ В главное меню", "main_menu")]]
        return text, rows

    if payload == "tracking_solved_yes":
        text = "✅ Отлично! Если появятся вопросы — обращайтесь."
        rows = [[btn_cb("◀️ В главное меню", "main_menu")]]
        return text, rows
    if payload == "tracking_solved_no":
        text = "❌ Понял. Напишите номер заказа — передадим запрос менеджеру."
        rows = [[btn_cb("◀️ В главное меню", "main_menu")]]
        return text, rows

    if payload == "get_pdf":
        text = "📎 Памятка будет отправлена позже. (тест без файлов)"
        rows = [[btn_cb("◀️ В главное меню", "main_menu")]]
        return text, rows

    if payload == "remem_gmail":
        text = "📝 Укажите ИНН или номер договора одним сообщением."
        rows = [[btn_cb("◀️ В главное меню", "main_menu")]]
        return text, rows

    return f"Получен callback: `{payload}`", [[btn_cb("◀️ В главное меню", "main_menu")]]


@app.post("/max/webhook")
async def max_webhook(request: Request):
    update = await request.json()
    update_type = update.get("update_type")

    if update_type == "message_created":
        message = update.get("message", {})
        sender = message.get("sender", {})
        user_id = sender.get("user_id")
        if user_id:
            text, rows = main_menu()
            send_message(user_id, text, rows)

    elif update_type == "message_callback":
        callback = update.get("callback", {})
        callback_id = callback.get("callback_id")
        payload_value = callback.get("payload", "")
        if callback_id:
            text, rows = get_response_for_payload(payload_value)
            answer_callback(callback_id, text, rows)

    return {"ok": True}
