import os

# ── Пути ──────────────────────────────────────────────────────────
BASE_DIR = os.getenv("MAX_BASE_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_SA_PATH = os.getenv("GOOGLE_SA_JSON_PATH") or os.path.join(BASE_DIR, "secrets", "google_sa.json")

# ── Google Sheets ID ──────────────────────────────────────────────
# Корзина (каталог Лист1, корзина Лист2)
GSHEET_CART_ID = os.getenv("GSHEET_CART_ID") or "1lN1TtjXnpJJhP-SEfETWK-nPumFKoLHNpllLWkuUSkI"
GSHEET_CART_GID = os.getenv("GSHEET_CART_GID") or "132342150"
GSHEET_CART_TAB = os.getenv("GSHEET_CART_TAB") or "Лист2"

# Состояния пользователей
GSHEET_STATES_ID = os.getenv("GSHEET_STATES_ID") or "REPLACE_ME_STATES_SHEET_ID"
GSHEET_STATES_TAB = os.getenv("GSHEET_STATES_TAB") or "Лист1"

# Менеджеры (имя → telegram_id/max_id)
GSHEET_MANAGERS_ID = os.getenv("GSHEET_MANAGERS_ID") or "REPLACE_ME_MANAGERS_SHEET_ID"
GSHEET_MANAGERS_TAB = os.getenv("GSHEET_MANAGERS_TAB") or "Лист1"

# Клиенты ИНН (база клиентов)
GSHEET_CLIENTS_ID = os.getenv("GSHEET_CLIENTS_ID") or "REPLACE_ME_CLIENTS_SHEET_ID"
GSHEET_CLIENTS_TAB = os.getenv("GSHEET_CLIENTS_TAB") or "Лист1"

# Телефоны (user_id → номер)
GSHEET_PHONES_ID = os.getenv("GSHEET_PHONES_ID") or "REPLACE_ME_PHONES_SHEET_ID"
GSHEET_PHONES_TAB = os.getenv("GSHEET_PHONES_TAB") or "Лист1"

# Логи чат-бота
GSHEET_LOGS_ID = os.getenv("GSHEET_LOGS_ID") or "REPLACE_ME_LOGS_SHEET_ID"
GSHEET_LOGS_TAB = os.getenv("GSHEET_LOGS_TAB") or "Лист1"

# Карта сообщений (manager_message_id ↔ client)
GSHEET_MSGMAP_ID = os.getenv("GSHEET_MSGMAP_ID") or "REPLACE_ME_MSGMAP_SHEET_ID"
GSHEET_MSGMAP_TAB = os.getenv("GSHEET_MSGMAP_TAB") or "Лист1"

# ── Получатели (MAX user_id) ─────────────────────────────────────
# Замени на реальные MAX user_id
KLO_USER_ID = int(os.getenv("KLO_USER_ID") or "0")               # КЛО основной
KLO_USER_ID_ROTATION = int(os.getenv("KLO_USER_ID_ROTATION") or "0")  # КЛО ротация
ACCOUNTANT_USER_ID = int(os.getenv("ACCOUNTANT_USER_ID") or "0")  # Бухгалтер 1
ACCOUNTANT2_USER_ID = int(os.getenv("ACCOUNTANT2_USER_ID") or "0")  # Бухгалтер 2
SALES_USER_ID = int(os.getenv("SALES_USER_ID") or "0")            # Продажник
GENERAL_CHAT_ID = int(os.getenv("GENERAL_CHAT_ID") or "0")        # Общий чат (если менеджер не найден)
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID") or "0")            # Администратор

# ── OpenRouter AI ─────────────────────────────────────────────────
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-001")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

# ── Флаги ─────────────────────────────────────────────────────────
_use_cart = os.getenv("USE_CART_SHEETS", "1")
USE_CART_SHEETS = _use_cart == "1"

MAX_UPDATE_TYPES = os.getenv("MAX_UPDATE_TYPES") or "message_created,message_callback,message_command"

# Памятка ЛК: файл с диска, по умолчанию всегда `<корень репозитория>/assets/lk_memo.pdf`
# (не зависит от MAX_BASE_DIR). В .env не задавайте ссылку http(s) — такие значения игнорируются.
_APP_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_APP_DIR)
LK_MEMO_PDF_DEFAULT = os.path.normpath(os.path.join(_REPO_ROOT, "assets", "lk_memo.pdf"))
_lk_env = (os.getenv("LK_MEMO_PDF_PATH") or "").strip()
if _lk_env and not _lk_env.lower().startswith(("http://", "https://", "ftp://")):
    LK_MEMO_PDF_PATH = os.path.normpath(
        _lk_env if os.path.isabs(_lk_env) else os.path.join(_REPO_ROOT, _lk_env)
    )
else:
    LK_MEMO_PDF_PATH = LK_MEMO_PDF_DEFAULT

# ── Специальные дни ротации КЛО (МСК даты в формате MM-DD) ───────
# Заполни реальными датами из n8n
KLO_SPECIAL_DAYS = os.getenv("KLO_SPECIAL_DAYS", "").split(",") if os.getenv("KLO_SPECIAL_DAYS") else []

# ── Выходные: дежурный сотрудник и праздники ──────────────────────
# ID дежурного, которому в выходной уходят КЛО-запросы (создать заказ РФ,
# вопросы по заказу, платная упаковка). Остальные запросы получают автоответ.
WEEKEND_DUTY_USER_ID_DEFAULT = 29038920  # запасной КЛО (выходные/праздники)
WEEKEND_DUTY_USER_ID = int(os.getenv("WEEKEND_DUTY_USER_ID") or str(WEEKEND_DUTY_USER_ID_DEFAULT))

# Праздники в формате YYYY-MM-DD через запятую. В эти даты бот ведёт себя
# как в выходной (Сб/Вс). Пример: "2026-01-01,2026-01-02,2026-05-09"
_holidays_raw = (os.getenv("WEEKEND_HOLIDAYS") or "").strip()
WEEKEND_HOLIDAYS = (
    [d.strip() for d in _holidays_raw.split(",") if d.strip()]
    if _holidays_raw else []
)
