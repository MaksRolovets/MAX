import os
import requests

from app.logger import log_event

API_BASE = os.getenv("MAX_API_BASE", "https://platform-api.max.ru")

TOKEN = os.getenv("MAX_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("MAX_BOT_TOKEN is not set. Set it as an environment variable.")


def _headers():
    return {
        "Authorization": TOKEN,
        "Content-Type": "application/json",
    }


def send_message(user_id: int, payload: dict, trace_id: str | None = None):
    log_event("http_request", trace_id, method="POST", path="/messages", user_id=user_id)
    resp = requests.post(
        f"{API_BASE}/messages",
        params={"user_id": user_id},
        headers=_headers(),
        json=payload,
        timeout=10,
    )
    log_event("http_response", trace_id, status=resp.status_code, body=resp.text[:500])
    return resp


def answer_callback(callback_id: str, body: dict, trace_id: str | None = None):
    log_event("http_request", trace_id, method="POST", path="/answers", callback_id=callback_id)
    resp = requests.post(
        f"{API_BASE}/answers",
        params={"callback_id": callback_id},
        headers=_headers(),
        json=body,
        timeout=10,
    )
    log_event("http_response", trace_id, status=resp.status_code, body=resp.text[:500])
    return resp


def get_updates(params: dict, trace_id: str | None = None):
    log_event("http_request", trace_id, method="GET", path="/updates", params=params)
    resp = requests.get(
        f"{API_BASE}/updates",
        params=params,
        headers={"Authorization": TOKEN},
        timeout=40,
    )
    log_event("http_response", trace_id, status=resp.status_code, body=resp.text[:500])
    return resp
