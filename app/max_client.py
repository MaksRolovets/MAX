import os
import time
import requests

from dotenv import load_dotenv

from app.logger import log_event

# Load .env from repo root if present (so MAX_BOT_TOKEN is available).
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DOTENV_PATH = os.getenv('DOTENV_PATH') or os.path.join(_BASE_DIR, '.env')
load_dotenv(_DOTENV_PATH, override=True)

API_BASE = os.getenv("MAX_API_BASE", "https://platform-api.max.ru")

TOKEN = os.getenv("MAX_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("MAX_BOT_TOKEN is not set. Set it as an environment variable.")

# (connect, read) — короткий read=10 с даёт ReadTimeout на /answers и /messages при задержках API/SSL
_HTTP_TIMEOUT = (
    int(os.getenv("MAX_HTTP_CONNECT_TIMEOUT", "30")),
    int(os.getenv("MAX_HTTP_READ_TIMEOUT", "90")),
)
_UPDATES_TIMEOUT = int(os.getenv("MAX_UPDATES_TIMEOUT", "45"))


def _headers():
    return {
        "Authorization": TOKEN,
        "Content-Type": "application/json",
    }


def _auth_headers():
    """Только токен — для multipart POST на upload URL (нельзя слать Content-Type: json)."""
    return {"Authorization": TOKEN}


def send_message(user_id: int, payload: dict, trace_id: str | None = None):
    log_event("http_request", trace_id, method="POST", path="/messages", user_id=user_id)
    resp = requests.post(
        f"{API_BASE}/messages",
        params={"user_id": user_id},
        headers=_headers(),
        json=payload,
        timeout=_HTTP_TIMEOUT,
    )
    log_event("http_response", trace_id, status=resp.status_code, body=resp.text[:500])
    return resp


def send_message_to_chat(chat_id: int, payload: dict, trace_id: str | None = None):
    """POST /messages?chat_id=... — отправка в групповой чат/канал."""
    log_event("http_request", trace_id, method="POST", path="/messages", chat_id=chat_id)
    resp = requests.post(
        f"{API_BASE}/messages",
        params={"chat_id": chat_id},
        headers=_headers(),
        json=payload,
        timeout=_HTTP_TIMEOUT,
    )
    log_event("http_response", trace_id, status=resp.status_code, body=resp.text[:500])
    return resp


def upload_local_file(local_path: str, trace_id: str | None = None) -> str | None:
    """POST /uploads → загрузка файла по url → token для вложения type=file."""
    if not os.path.isfile(local_path):
        log_event("upload_error", trace_id, error="file_not_found", path=local_path)
        return None
    try:
        r = requests.post(
            f"{API_BASE}/uploads",
            params={"type": "file"},
            headers=_headers(),
            timeout=_HTTP_TIMEOUT,
        )
        log_event("http_response", trace_id, status=r.status_code, body=r.text[:400])
        r.raise_for_status()
        upload_url = r.json().get("url")
        if not upload_url:
            return None
        fname = os.path.basename(local_path) or "file.pdf"
        mime = "application/pdf" if fname.lower().endswith(".pdf") else "application/octet-stream"
        with open(local_path, "rb") as f:
            # Важно: не передавать Content-Type: application/json — иначе multipart ломается,
            # CDN отвечает 406 upload.error «No file name in request».
            r2 = requests.post(
                upload_url,
                headers=_auth_headers(),
                files={"data": (fname, f, mime)},
                timeout=(30, 180),
            )
        log_event("http_response", trace_id, status=r2.status_code, body=r2.text[:400])
        r2.raise_for_status()
        token = r2.json().get("token")
        if not token:
            log_event("upload_error", trace_id, error="no_token_in_response")
        return token
    except Exception as e:
        log_event("upload_error", trace_id, error=str(e)[:300])
        return None


def send_message_with_file(
    user_id: int,
    text: str,
    file_token: str,
    rows: list | None = None,
    trace_id: str | None = None,
):
    """Сообщение с вложением file; при необходимости — inline-клавиатура."""
    from app.nodes import packaging_paid as _pp

    attachments: list = [{"type": "file", "payload": {"token": file_token}}]
    if rows:
        attachments.extend(_pp.keyboard(rows))
    payload = {"text": text, "format": "markdown", "attachments": attachments}

    last = None
    for attempt in range(6):
        if attempt:
            time.sleep(1.0 + attempt * 0.5)
        last = send_message(user_id, payload, trace_id)
        if last.status_code != 200:
            continue
        try:
            data = last.json()
            if data.get("code") == "attachment.not.ready":
                log_event("attachment_not_ready", trace_id, attempt=attempt)
                continue
        except Exception:
            pass
        return last
    return last


def answer_callback(callback_id: str, body: dict, trace_id: str | None = None):
    log_event("http_request", trace_id, method="POST", path="/answers", callback_id=callback_id)
    resp = requests.post(
        f"{API_BASE}/answers",
        params={"callback_id": callback_id},
        headers=_headers(),
        json=body,
        timeout=_HTTP_TIMEOUT,
    )
    log_event("http_response", trace_id, status=resp.status_code, body=resp.text[:500])
    return resp


def get_updates(params: dict, trace_id: str | None = None):
    log_event("http_request", trace_id, method="GET", path="/updates", params=params)
    resp = requests.get(
        f"{API_BASE}/updates",
        params=params,
        headers={"Authorization": TOKEN},
        timeout=_UPDATES_TIMEOUT,
    )
    log_event("http_response", trace_id, status=resp.status_code, body=resp.text[:500])
    return resp



