"""Управление состояниями пользователей через Google Sheets.

Таблица user_states: user_id | state | order_number | inn | comment | manager_id | topic | timestamp
"""

from datetime import datetime, timezone, timedelta

from app import settings
from app.sheets_base import open_sheet

MSK = timezone(timedelta(hours=3))

_sheet = None


def _get_sheet():
    global _sheet
    if _sheet is None:
        _sheet = open_sheet(settings.GSHEET_STATES_ID, tab=settings.GSHEET_STATES_TAB)
    return _sheet


def _idx(header: list, name: str):
    name_l = name.lower()
    for i, h in enumerate(header):
        h_str = str(h).strip()
        if not h_str:
            continue
        h_l = h_str.lower()
        if h_l == name_l or name_l in h_l:
            return i
    return None


def _find_user_row(sheet, user_id: int) -> int | None:
    values = sheet.get_all_values()
    if not values:
        return None

    header = values[0]
    rows = values[1:]
    i_uid = _idx(header, "user_id")
    if i_uid is None:
        i_uid = 0

    for idx, row in enumerate(rows, start=2):
        if len(row) > i_uid and str(row[i_uid]) == str(user_id):
            return idx
    return None


def set_state(user_id: int, state: str, topic: str = "", comment: str = "",
              inn: str = "", order_number: str = "", manager_id: str = ""):
    """Upsert состояние пользователя (если есть — обновляем строку, иначе append)."""
    ts = datetime.now(MSK).isoformat()
    row = [str(user_id), state, order_number, inn, comment, manager_id, topic, ts]

    sheet = _get_sheet()
    row_idx = None
    try:
        row_idx = _find_user_row(sheet, user_id)
    except Exception:
        row_idx = None

    if row_idx:
        sheet.update(f"A{row_idx}:H{row_idx}", [row], value_input_option="RAW")
        return

    sheet.append_row(row, value_input_option="RAW")


def get_state(user_id: int) -> dict | None:
    """Возвращает последнее состояние пользователя (по timestamp desc)."""
    sheet = _get_sheet()
    values = sheet.get_all_values()
    if not values:
        return None

    header = values[0]
    rows = values[1:]

    i_uid = _idx(header, "user_id")
    i_state = _idx(header, "state")
    i_order = _idx(header, "order_number")
    i_inn = _idx(header, "inn")
    i_comment = _idx(header, "comment")
    i_mgr = _idx(header, "manager_id")
    i_topic = _idx(header, "topic")
    i_ts = _idx(header, "timestamp")

    # Fallback to default column positions if headers are missing or mismatched.
    if i_uid is None or i_state is None:
        defaults = {
            "user_id": 0,
            "state": 1,
            "order_number": 2,
            "inn": 3,
            "comment": 4,
            "manager_id": 5,
            "topic": 6,
            "timestamp": 7,
        }
        if i_uid is None:
            i_uid = defaults["user_id"]
        if i_state is None:
            i_state = defaults["state"]
        if i_order is None:
            i_order = defaults["order_number"]
        if i_inn is None:
            i_inn = defaults["inn"]
        if i_comment is None:
            i_comment = defaults["comment"]
        if i_mgr is None:
            i_mgr = defaults["manager_id"]
        if i_topic is None:
            i_topic = defaults["topic"]
        if i_ts is None:
            i_ts = defaults["timestamp"]

    user_rows = []
    for row in rows:
        if i_uid is not None and len(row) > i_uid and str(row[i_uid]) == str(user_id):
            user_rows.append(row)

    if not user_rows:
        return None

    # Сортируем по timestamp desc и берём последнюю
    if i_ts is not None:
        user_rows.sort(key=lambda r: r[i_ts] if len(r) > i_ts else "", reverse=True)

    latest = user_rows[0]

    def val(i):
        return latest[i] if i is not None and len(latest) > i else ""

    return {
        "user_id": val(i_uid),
        "state": val(i_state),
        "order_number": val(i_order),
        "inn": val(i_inn),
        "comment": val(i_comment),
        "manager_id": val(i_mgr),
        "topic": val(i_topic),
        "timestamp": val(i_ts),
    }


def clear_state(user_id: int):
    """Сбрасывает состояние пользователя в 'none'."""
    set_state(user_id, "none")