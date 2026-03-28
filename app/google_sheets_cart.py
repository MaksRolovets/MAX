import json
import os

from app import settings

import gspread
from google.oauth2.service_account import Credentials

_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

_client = None
_sheet = None


def _load_creds():
    raw = os.getenv("GOOGLE_SA_JSON")
    path = os.getenv("GOOGLE_SA_JSON_PATH") or settings.DEFAULT_SA_PATH

    if raw:
        info = json.loads(raw)
    elif path:
        with open(path, "r", encoding="utf-8-sig") as f:
            info = json.load(f)
    else:
        raise RuntimeError("GOOGLE_SA_JSON or GOOGLE_SA_JSON_PATH is not set")

    return Credentials.from_service_account_info(info, scopes=_SCOPES)


def _get_cart_sheet():
    global _client, _sheet
    if _sheet is not None:
        return _sheet

    sheet_id = os.getenv("GSHEET_CART_ID") or settings.GSHEET_CART_ID
    gid = os.getenv("GSHEET_CART_GID") or settings.GSHEET_CART_GID
    tab = os.getenv("GSHEET_CART_TAB") or settings.GSHEET_CART_TAB

    if not sheet_id:
        raise RuntimeError("GSHEET_CART_ID is not set")

    creds = _load_creds()
    _client = gspread.authorize(creds)
    sh = _client.open_by_key(sheet_id)

    if gid:
        _sheet = sh.get_worksheet_by_id(int(gid))
    elif tab:
        _sheet = sh.worksheet(tab)
    else:
        _sheet = sh.sheet1

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

    # Collect row numbers (1-based in Sheets) to delete
    to_delete = []
    for i, row in enumerate(rows, start=2):
        if len(row) > i_user and str(row[i_user]) == str(user_id):
            to_delete.append(i)

    for row_idx in sorted(to_delete, reverse=True):
        sheet.delete_rows(row_idx)



