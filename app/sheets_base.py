"""Общая база для работы с Google Sheets — единая авторизация."""

import json
import os

import gspread
from google.oauth2.service_account import Credentials

from app import settings
from app.logger import log_event

_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

_gc = None


def _load_creds() -> Credentials:
    raw = os.getenv("GOOGLE_SA_JSON")
    path = os.getenv("GOOGLE_SA_JSON_PATH") or settings.DEFAULT_SA_PATH

    # Логируем только факт/путь, без содержимого ключа.
    log_event(
        "google_creds_resolved",
        path=path,
        has_env=bool(raw),
        file_exists=os.path.exists(path) if path else False,
    )

    if raw:
        info = json.loads(raw)
    elif path and os.path.exists(path):
        with open(path, "r", encoding="utf-8-sig") as f:
            info = json.load(f)
    else:
        raise RuntimeError("GOOGLE_SA_JSON or GOOGLE_SA_JSON_PATH is not set")

    return Credentials.from_service_account_info(info, scopes=_SCOPES)


def get_client() -> gspread.Client:
    global _gc
    if _gc is None:
        _gc = gspread.authorize(_load_creds())
    return _gc


def open_sheet(sheet_id: str, tab: str | None = None, gid: str | None = None):
    gc = get_client()
    sh = gc.open_by_key(sheet_id)
    if gid:
        return sh.get_worksheet_by_id(int(gid))
    if tab:
        return sh.worksheet(tab)
    return sh.sheet1
