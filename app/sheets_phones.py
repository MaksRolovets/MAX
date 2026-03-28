"""Хранение телефонных номеров пользователей в Google Sheets.

Таблица: user_id | number
"""

from app import settings
from app.sheets_base import open_sheet

_sheet = None


def _get_sheet():
    global _sheet
    if _sheet is None:
        _sheet = open_sheet(settings.GSHEET_PHONES_ID, tab=settings.GSHEET_PHONES_TAB)
    return _sheet


def get_phone(user_id: int) -> str | None:
    """Возвращает телефон пользователя или None."""
    sheet = _get_sheet()
    values = sheet.get_all_values()
    if not values:
        return None

    header = values[0]

    def idx(name: str):
        for i, h in enumerate(header):
            if name.lower() in h.lower():
                return i
        return None

    i_uid = idx("user_id") or idx("tg_id")
    i_num = idx("number")

    for row in values[1:]:
        row_uid = row[i_uid] if i_uid is not None and len(row) > i_uid else ""
        if str(row_uid).strip() == str(user_id):
            return row[i_num] if i_num is not None and len(row) > i_num else None
    return None


def has_phone(user_id: int) -> bool:
    return get_phone(user_id) is not None


def save_phone(user_id: int, phone: str):
    """Сохраняет телефон. Если уже есть — не дублирует."""
    if has_phone(user_id):
        return
    _get_sheet().append_row([str(user_id), phone], value_input_option="RAW")
