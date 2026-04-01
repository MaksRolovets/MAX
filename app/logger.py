import json
import os
import sys
import time
import uuid

# Fix Windows console encoding for emoji/unicode
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

LOG_PATH = os.getenv("MAX_LOG_PATH", os.path.join(
    os.getenv("MAX_BASE_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "logs", "max-dev.log.jsonl",
))
LOG_TO_STDOUT = os.getenv("LOG_TO_STDOUT", "1") == "1"
LOG_TO_SHEETS = os.getenv("LOG_TO_SHEETS", "0") == "1"


def new_trace_id() -> str:
    return uuid.uuid4().hex


def _mask(value):
    if isinstance(value, str) and len(value) > 6:
        return value[:3] + "***" + value[-3:]
    return value


def log_event(event: str, trace_id: str | None = None, **data) -> None:
    record = {
        "ts": int(time.time() * 1000),
        "event": event,
        "trace_id": trace_id,
    }
    for k, v in data.items():
        if k.lower() in ("token", "authorization", "auth"):
            record[k] = _mask(v)
        else:
            record[k] = v

    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    line = json.dumps(record, ensure_ascii=False)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")

    if LOG_TO_STDOUT:
        try:
            print(line, flush=True)
        except UnicodeEncodeError:
            print(line.encode("ascii", errors="replace").decode("ascii"), flush=True)

    if LOG_TO_SHEETS:
        try:
            from app.google_sheets import append_log
            append_log(record)
        except Exception as e:
            err = {"event": "sheets_error", "error": str(e)}
            if LOG_TO_STDOUT:
                print(json.dumps(err, ensure_ascii=False), flush=True)
