from app.settings import USE_CART_SHEETS
from app.state import CART

USE_SHEETS_CART = USE_CART_SHEETS
if USE_SHEETS_CART:
    from app.google_sheets_cart import append_cart_row, get_cart_rows, delete_cart_rows

CATALOG = {
    "Вкладыши": [
        {"id": "insert_1", "name": "Вкладыш для 1 бутылки (до 1 л.)", "price": 135},
    ],
    "Внутр обрешетка": [
        {"id": "grid_1", "name": "Внутр обрешетка «Коробка Вес до 20кг»", "price": 890},
        {"id": "grid_2", "name": "Внутр обрешетка «Коробка Вес до 30кг»", "price": 1225},
        {"id": "grid_3", "name": "Внутр обрешетка «Коробка XL»", "price": 825},
        {"id": "grid_4", "name": "Внутр обрешетка для коробки «L»", "price": 495},
        {"id": "grid_5", "name": "Внутр обрешетка для коробки «M»", "price": 130},
        {"id": "grid_6", "name": "Внутр обрешетка для коробки «S»", "price": 65},
        {"id": "grid_7", "name": "Внутр обрешетка для Коробки XXL", "price": 1300},
    ],
    "Воздушно-пузырчатая пленка": [
        {"id": "bubble_1", "name": "Воздушно-пузырчатая пленка", "price": 90},
        {"id": "bubble_2", "name": "Воздушно-пузырчатая пленка мини-рулон", "price": 265},
    ],
    "Конверты": [
        {"id": "env_1", "name": "Конверт (картон, А4)", "price": 45},
        {"id": "env_2", "name": "Конверт укреплённый (гофрокартон, А4)", "price": 45},
    ],
    "Подарочные коробки": [
        {"id": "gift_1", "name": "Коробка \"Подарочная\" M (5кг 33х25х15см)", "price": 220},
        {"id": "gift_2", "name": "Коробка \"Подарочная\" S (2кг 23х19х10см)", "price": 195},
        {"id": "gift_3", "name": "Коробка \"Праздничная\" (25х21х10см)", "price": 150},
        {"id": "gift_4", "name": "Коробка \"Праздничная\" M (5кг 33х25х15см)", "price": 190},
    ],
    "Коробки": [
        {"id": "box_1", "name": "Коробка Вес до 10кг (40х35х28см)", "price": 215},
        {"id": "box_2", "name": "Коробка Вес до 20кг (47х40х43см)", "price": 275},
        {"id": "box_3", "name": "Коробка Вес до 2кг (34х24х10см)", "price": 105},
        {"id": "box_4", "name": "Коробка Вес до 30кг (69х39х42см)", "price": 330},
        {"id": "box_5", "name": "Коробка Вес до 3кг (24х24х21см)", "price": 115},
        {"id": "box_6", "name": "Коробка Вес до 5кг (40х24х21см)", "price": 130},
        {"id": "box_7", "name": "Коробка Вес до 6кг (6кг 36х29х7см)", "price": 100},
        {"id": "box_8", "name": "Коробка для 1 бутылки (3кг 15х14х38см)", "price": 50},
        {"id": "box_9", "name": "Коробка для 2-х бутылок (4кг 29х15х39см)", "price": 90},
        {"id": "box_10", "name": "Коробка для 3-х бутылок (6кг 44х15х39см)", "price": 135},
        {"id": "box_11", "name": "Коробка для 4-х бутылок (8кг 30х28х39см)", "price": 155},
        {"id": "box_12", "name": "Коробка для 6-ти бутылок (12кг 44х28х39см)", "price": 185},
        {"id": "box_13", "name": "Коробка Лайт 1 (8кг 60х40х40см)", "price": 220},
        {"id": "box_14", "name": "Коробка Лайт 2 (4кг 40х30х30см)", "price": 140},
        {"id": "box_15", "name": "Коробка L (12кг 31х25х38см)", "price": 170},
        {"id": "box_16", "name": "Коробка M (5кг 33х25х15см)", "price": 150},
        {"id": "box_17", "name": "Коробка S (2кг 23х19х10см)", "price": 105},
        {"id": "box_18", "name": "Коробка XL (18кг 60х35х30см)", "price": 255},
        {"id": "box_19", "name": "Коробка XS (0,5кг 17х12х9см)", "price": 45},
        {"id": "box_20", "name": "Коробка XXL (35кг 80х40х40см)", "price": 400},
    ],
    "Мешки и пленки": [
        {"id": "bag_1", "name": "Крафт пакет 32х35см", "price": 35},
        {"id": "bag_2", "name": "Листовой гофрокартон (0,8х1,2м)", "price": 130},
        {"id": "bag_3", "name": "Мешок ламинированный (до 100 кг)", "price": 195},
        {"id": "bag_4", "name": "Мешок ламинированный (до 25 кг)", "price": 80},
        {"id": "bag_5", "name": "Мешок ламинированный (до 50 кг)", "price": 105},
        {"id": "bag_6", "name": "Мешок ламинированный (до 70 кг)", "price": 145},
    ],
    "Надувная пленка": [
        {"id": "air_1", "name": "Надувная пленка с обр. кл., 30см х 50м", "price": 55},
        {"id": "air_2", "name": "Надувная пленка с обр. кл., 40см х 50м", "price": 70},
        {"id": "air_3", "name": "Надувная пленка с обр. кл., 50см х 50м", "price": 80},
    ],
    "Пакеты": [
        {"id": "pkg_1", "name": "Пакет курьерский «Лайт» А1 (белый)", "price": 80},
        {"id": "pkg_2", "name": "Пакет курьерский «Лайт» А2 (белый)", "price": 75},
        {"id": "pkg_3", "name": "Пакет курьерский «Лайт» А3 (белый)", "price": 30},
        {"id": "pkg_4", "name": "Пакет курьерский «Лайт» А4 (белый)", "price": 25},
        {"id": "pkg_5", "name": "Пакет курьерский «Лайт» А5 (белый)", "price": 15},
        {"id": "pkg_6", "name": "Пакет курьерский СДЭК А2", "price": 75},
        {"id": "pkg_7", "name": "Пакет курьерский СДЭК А3", "price": 30},
        {"id": "pkg_8", "name": "Пакет курьерский СДЭК А3 с ручкой", "price": 35},
        {"id": "pkg_9", "name": "Пакет курьерский СДЭК А4", "price": 25},
        {"id": "pkg_10", "name": "Пакет c прорубной ручкой Лама (550х550мм)", "price": 45},
        {"id": "pkg_11", "name": "Пакет c прорубной ручкой СДЭК (400х500мм)", "price": 20},
        {"id": "pkg_12", "name": "Пакет c прорубной ручкой СДЭК (600х500мм)", "price": 40},
        {"id": "pkg_13", "name": "Пакет-майка 30х53", "price": 8},
        {"id": "pkg_14", "name": "Пакет-майка 40х60", "price": 17},
    ],
    "Картон": [
        {"id": "card_1", "name": "Прессованный картон «Филлер»", "price": 65},
    ],
    "Скотч": [
        {"id": "tape_1", "name": "Скотч «Осторожно хрупкое»", "price": 240},
        {"id": "tape_2", "name": "Скотч прозрачный", "price": 260},
        {"id": "tape_3", "name": "Скотч прозрачный широкий", "price": 270},
        {"id": "tape_4", "name": "Скотч с логотипом CDEK", "price": 275},
        {"id": "tape_5", "name": "Скотч с логотипом CDEK широкий", "price": 295},
    ],
    "Стрейч пленка": [
        {"id": "stretch_1", "name": "Стрейч пленка", "price": 8},
        {"id": "stretch_2", "name": "Стрейч пленка мини-рулон (белая)", "price": 220},
    ],
    "Упаковочная бумага": [
        {"id": "paper_1", "name": "Упаковочная бумага (крафт)", "price": 65},
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

    if USE_SHEETS_CART:
        append_cart_row(user_id, item_id, item["name"], item["price"], qty)
    else:
        user_cart = CART[user_id]
        entry = user_cart.get(item_id, {"name": item["name"], "price": item["price"], "qty": 0})
        entry["qty"] += qty
        user_cart[item_id] = entry

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



