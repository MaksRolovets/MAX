import os

BASE_DIR = r"E:\MAX"
DEFAULT_SA_PATH = os.getenv("GOOGLE_SA_JSON_PATH") or os.path.join(BASE_DIR, "secrets", "google_sa.json")

GSHEET_CART_ID = os.getenv("GSHEET_CART_ID") or "1lN1TtjXnpJJhP-SEfETWK-nPumFKoLHNpllLWkuUSkI"
GSHEET_CART_GID = os.getenv("GSHEET_CART_GID") or "132342150"
GSHEET_CART_TAB = os.getenv("GSHEET_CART_TAB") or "Лист2"

_use_cart = os.getenv("USE_CART_SHEETS")
if _use_cart is None:
    _use_cart = "1"
USE_CART_SHEETS = _use_cart == "1"

MAX_UPDATE_TYPES = os.getenv("MAX_UPDATE_TYPES") or "message_created,message_callback,message_command"
