from app.settings import USE_CART_SHEETS
from app.state import CART
from app.logger import log_event

USE_SHEETS_CART = USE_CART_SHEETS
if USE_SHEETS_CART:
    from app.google_sheets_cart import append_cart_row, get_cart_rows, delete_cart_rows

CATALOG = {
    "Внутр обрешетка": [
        {"id": "obresh_20", "name": "Обреш. до 20кг", "price": 890},
        {"id": "obresh_30", "name": "Обреш. до 30кг", "price": 1225},
        {"id": "obresh_xl", "name": "Обреш. XL", "price": 825},
        {"id": "obresh_l", "name": "Обреш. L", "price": 495},
        {"id": "obresh_m", "name": "Обреш. M", "price": 130},
        {"id": "obresh_s", "name": "Обреш. S", "price": 65},
        {"id": "obresh_xxl", "name": "Обреш. XXL", "price": 1300},
    ],
    "Воздушно-пузырчатая пленка": [
        {"id": "bubble_1", "name": "Возд.-пуз. пленка", "price": 90},
        {"id": "bubble_2", "name": "Воздуш-пузырч-я пленка мини-рулон", "price": 265},
    ],
    "Конверты": [
        {"id": "env_1", "name": "Конверт А4 картон", "price": 45},
        {"id": "env_2", "name": "Конверт А4 гофро", "price": 45},
    ],
    "Коробки": [
        {"id": "box_10kg", "name": "Кор. 10кг 40×35×28", "price": 215},
        {"id": "box_20kg", "name": "Кор. 20кг 47×40×43", "price": 275},
        {"id": "box_2kg", "name": "Кор. 2кг 34×24×10", "price": 105},
        {"id": "box_30kg", "name": "Кор. 30кг 69×39×42", "price": 330},
        {"id": "box_3kg", "name": "Кор. 3кг 24×24×21", "price": 115},
        {"id": "box_5kg", "name": "Кор. 5кг 40×24×21", "price": 130},
        {"id": "box_6kg", "name": "Кор. 6кг 36×29×7", "price": 100},
        {"id": "box_light1", "name": "Кор. Лайт1 8кг 60×40×40", "price": 220},
        {"id": "box_light2", "name": "Кор. Лайт2 4кг 40×30×30", "price": 140},
        {"id": "box_l", "name": "Кор. L 12кг 31×25×38", "price": 170},
        {"id": "box_m", "name": "Кор. M 5кг 33×25×15", "price": 150},
        {"id": "box_s", "name": "Кор. S 2кг 23×19×10", "price": 105},
        {"id": "box_xl", "name": "Кор. XL 18кг 60×35×30", "price": 255},
        {"id": "box_xs", "name": "Кор. XS 0,5кг 17×12×9", "price": 45},
        {"id": "box_xxl", "name": "Кор. XXL 35кг 80×40×40", "price": 400},
    ],
    "Пакеты": [
        {"id": "pkg_light_a1", "name": "Пакет Лайт А1", "price": 80},
        {"id": "pkg_light_a2", "name": "Пакет Лайт А2", "price": 75},
        {"id": "pkg_light_a3", "name": "Пакет Лайт А3", "price": 30},
        {"id": "pkg_light_a4", "name": "Пакет Лайт А4", "price": 25},
        {"id": "pkg_light_a5", "name": "Пакет Лайт А5", "price": 15},
        {"id": "pkg_cdek_a2", "name": "Пакет СДЭК А2", "price": 75},
        {"id": "pkg_cdek_a3", "name": "Пакет СДЭК А3", "price": 30},
        {"id": "pkg_cdek_a3_handle", "name": "Пакет СДЭК А3 с ручкой", "price": 35},
        {"id": "pkg_cdek_a4", "name": "Пакет СДЭК А4", "price": 25},
        {"id": "pkg_mayka_30", "name": "Пакет-майка 30×53", "price": 8},
        {"id": "pkg_mayka_40", "name": "Пакет-майка 40×60", "price": 17},
    ],
    "Скотч": [
        {"id": "tape_fragile", "name": "Скотч «Хрупкое»", "price": 240},
        {"id": "tape_cdek", "name": "Скотч CDEK", "price": 275},
        {"id": "tape_cdek_wide", "name": "Скотч CDEK широкий", "price": 295},
    ],
    "Стрейч пленка": [
        {"id": "stretch", "name": "Стрейч пленка", "price": 8},
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