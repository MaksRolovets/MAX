import json
import os
from datetime import datetime, timezone

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
    path = os.getenv("GOOGLE_SA_JSON_PATH")

    if raw:
        info = json.loads(raw)
    elif path:
        with open(path, "r", encoding="utf-8") as f:
            info = json.load(f)
    else:
        raise RuntimeError("GOOGLE_SA_JSON or GOOGLE_SA_JSON_PATH is not set")

    return Credentials.from_service_account_info(info, scopes=_SCOPES)


def _get_sheet():
    global _client, _sheet
    if _sheet is not None:
        return _sheet

    sheet_id = os.getenv("GSHEET_ID")
    tab = os.getenv("GSHEET_TAB", "logs")
    if not sheet_id:
        raise RuntimeError("GSHEET_ID is not set")

    creds = _load_creds()
    _client = gspread.authorize(creds)
    _sheet = _client.open_by_key(sheet_id).worksheet(tab)
    return _sheet


def append_log(record: dict):
    sheet = _get_sheet()
    ts = datetime.now(timezone.utc).isoformat()
    event = record.get("event")
    trace_id = record.get("trace_id")
    node = record.get("node")
    payload = json.dumps(record, ensure_ascii=False)
    sheet.append_row([ts, event, trace_id, node, payload], value_input_option="RAW")
