from app.settings import USE_CART_SHEETS
from app.state import CART
from app.logger import log_event

USE_SHEETS_CART = USE_CART_SHEETS
if USE_SHEETS_CART:
    from app.google_sheets_cart import append_cart_row, get_cart_rows, delete_cart_rows

CATALOG = {
    "Вкладыши": [
        {"id": "insert_1", "name": "Вкладыш 1 бут., до 1 л", "price": 135},
    ],
    "Обрешетка": [
        {"id": "grid_1", "name": "Обреш. до 20кг", "price": 890},
        {"id": "grid_2", "name": "Обреш. до 30кг", "price": 1225},
        {"id": "grid_3", "name": "Обреш. XL", "price": 825},
        {"id": "grid_4", "name": "Обреш. L", "price": 495},
        {"id": "grid_5", "name": "Обреш. M", "price": 130},
        {"id": "grid_6", "name": "Обреш. S", "price": 65},
        {"id": "grid_7", "name": "Обреш. XXL", "price": 1300},
    ],
    "Возд.-пуз. пл.": [
        {"id": "bubble_1", "name": "Возд.-пуз. пленка", "price": 90},
        {"id": "bubble_2", "name": "Возд.-пуз. пл. мини-рулон", "price": 265},
    ],
    "Конверты": [
        {"id": "env_1", "name": "Конверт картон А4", "price": 45},
        {"id": "env_2", "name": "Конверт укр. гофро А4", "price": 45},
    ],
    "Подар. коробки": [
        {"id": "gift_1", "name": "Подар. M 5кг 33×25×15", "price": 220},
        {"id": "gift_2", "name": "Подар. S 2кг 23×19×10", "price": 195},
        {"id": "gift_3", "name": "Праздн. 25×21×10", "price": 150},
        {"id": "gift_4", "name": "Праздн. M 5кг 33×25×15", "price": 190},
    ],
    "Коробки": [
        {"id": "box_1", "name": "Кор. 10кг 40×35×28", "price": 215},
        {"id": "box_2", "name": "Кор. 20кг 47×40×43", "price": 275},
        {"id": "box_3", "name": "Кор. 2кг 34×24×10", "price": 105},
        {"id": "box_4", "name": "Кор. 30кг 69×39×42", "price": 330},
        {"id": "box_5", "name": "Кор. 3кг 24×24×21", "price": 115},
        {"id": "box_6", "name": "Кор. 5кг 40×24×21", "price": 130},
        {"id": "box_7", "name": "Кор. 6кг 36×29×7", "price": 100},
        {"id": "box_8", "name": "Кор. 1 бут. 3кг 15×14×38", "price": 50},
        {"id": "box_9", "name": "Кор. 2 бут. 4кг 29×15×39", "price": 90},
        {"id": "box_10", "name": "Кор. 3 бут. 6кг 44×15×39", "price": 135},
        {"id": "box_11", "name": "Кор. 4 бут. 8кг 30×28×39", "price": 155},
        {"id": "box_12", "name": "Кор. 6 бут. 12кг 44×28×39", "price": 185},
        {"id": "box_13", "name": "Кор. Лайт1 8кг 60×40×40", "price": 220},
        {"id": "box_14", "name": "Кор. Лайт2 4кг 40×30×30", "price": 140},
        {"id": "box_15", "name": "Кор. L 12кг 31×25×38", "price": 170},
        {"id": "box_16", "name": "Кор. M 5кг 33×25×15", "price": 150},
        {"id": "box_17", "name": "Кор. S 2кг 23×19×10", "price": 105},
        {"id": "box_18", "name": "Кор. XL 18кг 60×35×30", "price": 255},
        {"id": "box_19", "name": "Кор. XS 0,5кг 17×12×9", "price": 45},
        {"id": "box_20", "name": "Кор. XXL 35кг 80×40×40", "price": 400},
    ],
    "Мешки, плёнка": [
        {"id": "bag_1", "name": "Крафт пакет 32×35", "price": 35},
        {"id": "bag_2", "name": "Лист гофро 0,8×1,2 м", "price": 130},
        {"id": "bag_3", "name": "Мешок лам. до 100кг", "price": 195},
        {"id": "bag_4", "name": "Мешок лам. до 25кг", "price": 80},
        {"id": "bag_5", "name": "Мешок лам. до 50кг", "price": 105},
        {"id": "bag_6", "name": "Мешок лам. до 70кг", "price": 145},
    ],
    "Надув. плёнка": [
        {"id": "air_1", "name": "Надув. пл. 30×50 м", "price": 55},
        {"id": "air_2", "name": "Надув. пл. 40×50 м", "price": 70},
        {"id": "air_3", "name": "Надув. пл. 50×50 м", "price": 80},
    ],
    "Пакеты": [
        {"id": "pkg_1", "name": "Кур. Лайт А1 бел.", "price": 80},
        {"id": "pkg_2", "name": "Кур. Лайт А2 бел.", "price": 75},
        {"id": "pkg_3", "name": "Кур. Лайт А3 бел.", "price": 30},
        {"id": "pkg_4", "name": "Кур. Лайт А4 бел.", "price": 25},
        {"id": "pkg_5", "name": "Кур. Лайт А5 бел.", "price": 15},
        {"id": "pkg_6", "name": "Кур. СДЭК А2", "price": 75},
        {"id": "pkg_7", "name": "Кур. СДЭК А3", "price": 30},
        {"id": "pkg_8", "name": "Кур. СДЭК А3 + ручка", "price": 35},
        {"id": "pkg_9", "name": "Кур. СДЭК А4", "price": 25},
        {"id": "pkg_10", "name": "Пакет прор. Лама 550×550", "price": 45},
        {"id": "pkg_11", "name": "Пакет прор. СДЭК 400×500", "price": 20},
        {"id": "pkg_12", "name": "Пакет прор. СДЭК 600×500", "price": 40},
        {"id": "pkg_13", "name": "Пакет-майка 30×53", "price": 8},
        {"id": "pkg_14", "name": "Пакет-майка 40×60", "price": 17},
    ],
    "Картон": [
        {"id": "card_1", "name": "Картон пресс. «Филлер»", "price": 65},
    ],
    "Скотч": [
        {"id": "tape_1", "name": "Скотч «Хрупкое»", "price": 240},
        {"id": "tape_2", "name": "Скотч прозрачный", "price": 260},
        {"id": "tape_3", "name": "Скотч прозр. широкий", "price": 270},
        {"id": "tape_4", "name": "Скотч CDEK", "price": 275},
        {"id": "tape_5", "name": "Скотч CDEK широкий", "price": 295},
    ],
    "Стрейч": [
        {"id": "stretch_1", "name": "Стрейч плёнка", "price": 8},
        {"id": "stretch_2", "name": "Стрейч мини бел.", "price": 220},
    ],
    "Упак. бумага": [
        {"id": "paper_1", "name": "Упак. бумага крафт", "price": 65},
    ],
}


def btn_cb(text: str, payload: str) -> dict:
    return {"type": "callback", "text": text, "payload": payload}


def keyboard(rows: list[list[dict]]):
    return [{"type": "inline_keyboard", "payload": {"buttons": rows}}]


def _find_item(item_id: str):
    for category, goods in CATALOG.items():
        for g in goods:
            if g["id"] == item_id:
                return {**g, "category": category}
    return None


def categories_menu():
    rows = []
    categories = sorted(CATALOG.keys(), key=str.casefold)

    for i in range(0, len(categories), 2):
        row = [btn_cb(f"📦 {categories[i]}", f"cat_{categories[i]}")]
        if i + 1 < len(categories):
            row.append(btn_cb(f"📦 {categories[i+1]}", f"cat_{categories[i+1]}"))
        rows.append(row)

    rows.append([btn_cb("🛒 Корзина", "seek_cart")])
    rows.append([btn_cb("◀️ Назад", "category_packaging")])
    return "💰 **Платная упаковка**\n\nВыберите категорию:", rows


def items_menu(category: str):
    goods = CATALOG.get(category)
    if not goods:
        return "❌ Категория не найдена.", [[btn_cb("◀️ Назад", "packaging_paid")]]
    goods_sorted = sorted(goods, key=lambda g: g["name"].casefold())
    rows = [[btn_cb(f"{g['name']} — {g['price']} руб.", f"item_{g['id']}")] for g in goods_sorted]
    rows.append([btn_cb("◀️ Назад к категориям", "packaging_paid")])
    return f"{category}\nВыберите товар:", rows


def item_card(item_id: str, qty: int = 1):
    item = _find_item(item_id)
    if not item:
        return "❌ Товар не найден.", [[btn_cb("◀️ Назад", "packaging_paid")]]

    rows = [
        [btn_cb("➖", f"dec:{item_id}:{qty}"), btn_cb(str(qty), "noop"), btn_cb("➕", f"inc:{item_id}:{qty}")],
        [btn_cb("✅ Добавить в корзину", f"add:{item_id}:{qty}")],
        [btn_cb("◀️ Назад", f"cat_{item['category']}")],
    ]

    text = f"📦 **{item['name']}**\n💰 Цена: {item['price']} руб.\n\nКоличество: {qty}"
    return text, rows


def adjust_qty(item_id: str, qty: int, action: str):
    if action == "inc":
        qty += 1
    elif action == "dec":
        qty = max(1, qty - 1)
    return item_card(item_id, qty)


def _aggregate(rows: list[dict]):
    cart = {}
    for row in rows:
        item_id = row.get("item_id")
        if not item_id:
            continue
        entry = cart.get(item_id, {"name": row.get("name", ""), "price": row.get("price", 0), "qty": 0})
        entry["qty"] += int(row.get("quantity") or 0)
        cart[item_id] = entry
    return cart


def add_to_cart(user_id: int, item_id: str, qty: int):
    item = _find_item(item_id)
    if not item:
        return "❌ Товар не найден.", [[btn_cb("◀️ В главное меню", "main_menu")]]

    try:
        if USE_SHEETS_CART:
            append_cart_row(user_id, item_id, item["name"], item["price"], qty)
        else:
            user_cart = CART[user_id]
            entry = user_cart.get(item_id, {"name": item["name"], "price": item["price"], "qty": 0})
            entry["qty"] += qty
            user_cart[item_id] = entry
    except Exception as e:
        log_event(
            "add_to_cart_error",
            user_id=user_id,
            item_id=item_id,
            qty=qty,
            error=str(e)[:300],
        )
        return "❌ Не удалось добавить в корзину. Попробуйте позже.", [[btn_cb("◀️ В главное меню", "main_menu")]]

    text = f"✅ *{item['name']}* добавлен в корзину (количество: {qty})."
    rows = [
        [btn_cb("🛒 Перейти в корзину", "seek_cart"), btn_cb("📦 Продолжить выбор", "packaging_paid")]
    ]
    return text, rows


def view_cart(user_id: int):
    if USE_SHEETS_CART:
        rows = get_cart_rows(user_id)
        cart = _aggregate(rows)
    else:
        cart = {k: v for k, v in CART.get(user_id, {}).items()}

    if not cart:
        return "🛒 **Ваша корзина пуста**", [[btn_cb("📦 В каталог", "packaging_paid")]]

    total = 0
    lines = ["🛒 **Ваша корзина:**", ""]
    for entry in cart.values():
        line_total = entry["qty"] * entry["price"]
        total += line_total
        lines.append(f"📦 {entry['name']}")
        lines.append(f"   {entry['qty']} шт × {entry['price']} руб = **{line_total} руб**")
    lines.append("")
    lines.append(f"**Итого: {total} руб**")

    rows = [
        [btn_cb("✅ Оформить заказ", "checkout")],
        [btn_cb("🗑️ Очистить корзину", "clear_cart")],
        [btn_cb("📦 Продолжить выбор", "packaging_paid")],
    ]
    return "\n".join(lines), rows


def clear_cart(user_id: int):
    if USE_SHEETS_CART:
        delete_cart_rows(user_id)
    else:
        CART[user_id] = {}
    return "🧹 Корзина очищена.", [[btn_cb("◀️ В главное меню", "main_menu")]]



