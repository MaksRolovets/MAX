"""Карта сообщений: связка manager_message_id ↔ client для ответов менеджера.

Таблица: manager_message_id | client_user_id | client_chat_id | manager_chat_id | timestamp
"""

from datetime import datetime, timezone, timedelta

from app import settings
from app.sheets_base import open_sheet

MSK = timezone(timedelta(hours=3))

_sheet = None


def _get_sheet():
    global _sheet
    if _sheet is None:
        _sheet = open_sheet(settings.GSHEET_MSGMAP_ID, tab=settings.GSHEET_MSGMAP_TAB)
    return _sheet


def save_message_map(manager_message_id: str, client_user_id: int,
                     client_chat_id: str = "", manager_chat_id: str = ""):
    """Сохраняет связку сообщения менеджера с клиентом."""
    ts = datetime.now(MSK).isoformat()
    _get_sheet().append_row(
        [str(manager_message_id), str(client_user_id), str(client_chat_id),
         str(manager_chat_id), ts],
        value_input_option="RAW",
    )


def find_client_by_message(manager_message_id: str) -> dict | None:
    """Ищет клиента по ID сообщения, на которое ответил менеджер."""
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

    i_msg = idx("manager_message_id")
    i_client = idx("client_user_id")
    i_chat = idx("client_chat_id")

    for row in values[1:]:
        row_msg = row[i_msg] if i_msg is not None and len(row) > i_msg else ""
        if str(row_msg).strip() == str(manager_message_id).strip():
            return {
                "client_user_id": int(float(row[i_client])) if i_client is not None and len(row) > i_client and row[i_client] else 0,
                "client_chat_id": row[i_chat] if i_chat is not None and len(row) > i_chat else "",
            }
    return None
