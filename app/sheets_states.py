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


def set_state(user_id: int, state: str, topic: str = "", comment: str = "",
              inn: str = "", order_number: str = "", manager_id: str = ""):
    """Добавляет новую строку состояния (append, не update — как в n8n)."""
    ts = datetime.now(MSK).isoformat()
    _get_sheet().append_row(
        [str(user_id), state, order_number, inn, comment, manager_id, topic, ts],
        value_input_option="RAW",
    )


def get_state(user_id: int) -> dict | None:
    """Возвращает последнее состояние пользователя (по timestamp desc)."""
    sheet = _get_sheet()
    values = sheet.get_all_values()
    if not values:
        return None

    header = values[0]
    rows = values[1:]

    def idx(name: str):
        try:
            return header.index(name)
        except ValueError:
            return None

    i_uid = idx("user_id")
    i_state = idx("state")
    i_order = idx("order_number")
    i_inn = idx("inn")
    i_comment = idx("comment")
    i_mgr = idx("manager_id")
    i_topic = idx("topic")
    i_ts = idx("timestamp")

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
