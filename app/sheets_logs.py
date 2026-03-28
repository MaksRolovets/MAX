"""Логирование запросов в Google Sheets.

Таблица: timestamp | user_id | action | chat_id | result | comment
"""

from datetime import datetime, timezone, timedelta

from app import settings
from app.sheets_base import open_sheet

MSK = timezone(timedelta(hours=3))

_sheet = None


def _get_sheet():
    global _sheet
    if _sheet is None:
        _sheet = open_sheet(settings.GSHEET_LOGS_ID, tab=settings.GSHEET_LOGS_TAB)
    return _sheet


def log_request(user_id: int, action: str, chat_id: str = "",
                result: str = "", comment: str = ""):
    """Записывает лог запроса в таблицу."""
    ts = datetime.now(MSK).isoformat()
    try:
        _get_sheet().append_row(
            [ts, str(user_id), action, chat_id, result, comment],
            value_input_option="RAW",
        )
    except Exception:
        pass  # логирование не должно ронять бота
