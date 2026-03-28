"""Работа с корзиной упаковки в Google Sheets (Лист2)."""

from app import settings
from app.sheets_base import open_sheet

_sheet = None


def _get_cart_sheet():
    global _sheet
    if _sheet is None:
        _sheet = open_sheet(
            settings.GSHEET_CART_ID,
            tab=settings.GSHEET_CART_TAB,
            gid=settings.GSHEET_CART_GID,
        )
    return _sheet


def append_cart_row(user_id: int, item_id: str, name: str, price: int, quantity: int):
    sheet = _get_cart_sheet()
    sheet.append_row([user_id, item_id, name, price, quantity], value_input_option="RAW")


def _read_all_rows():
    sheet = _get_cart_sheet()
    values = sheet.get_all_values()
    if not values:
        return [], []
    header = values[0]
    rows = values[1:]
    return header, rows


def get_cart_rows(user_id: int):
    header, rows = _read_all_rows()
    if not header:
        return []

    def idx(name: str):
        try:
            return header.index(name)
        except ValueError:
            return None

    i_user = idx("user_id")
    i_item = idx("item_id")
    i_name = idx("name")
    i_price = idx("price")
    i_qty = idx("quantity")

    result = []
    for row in rows:
        if i_user is not None and len(row) > i_user and str(row[i_user]) == str(user_id):
            result.append(
                {
                    "item_id": row[i_item] if i_item is not None and len(row) > i_item else "",
                    "name": row[i_name] if i_name is not None and len(row) > i_name else "",
                    "price": int(float(row[i_price])) if i_price is not None and len(row) > i_price and row[i_price] else 0,
                    "quantity": int(float(row[i_qty])) if i_qty is not None and len(row) > i_qty and row[i_qty] else 0,
                }
            )
    return result


def delete_cart_rows(user_id: int):
    sheet = _get_cart_sheet()
    header, rows = _read_all_rows()
    if not header:
        return

    try:
        i_user = header.index("user_id")
    except ValueError:
        return

    to_delete = []
    for i, row in enumerate(rows, start=2):
        if len(row) > i_user and str(row[i_user]) == str(user_id):
            to_delete.append(i)

    for row_idx in sorted(to_delete, reverse=True):
        sheet.delete_rows(row_idx)
