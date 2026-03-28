
import os
import time
from app.logger import log_event, new_trace_id
from app.max_client import get_updates
from app.router import handle_update


def poll_updates():
    marker = None
    while True:
        trace_id = new_trace_id()
        update_types = os.getenv("MAX_UPDATE_TYPES", "message_created,message_callback,message_command")
        params = {
            "limit": 100,
            "timeout": 30,
            "types": update_types,
        }
        if marker is not None:
            params["marker"] = marker

        resp = get_updates(params, trace_id)
        data = resp.json()
        marker = data.get("marker", marker)
        updates = data.get("updates", [])

        log_event("updates_batch", trace_id, count=len(updates))
        for upd in updates:
            upd_trace = new_trace_id()
            handle_update(upd, upd_trace)

        time.sleep(0.5)


if __name__ == "__main__":
    poll_updates()

