# Запуск поллинга MAX с Google Sheets (корзина)
$env:GOOGLE_SA_JSON_PATH = "E:\MAX\secrets\google_sa.json"
$env:GSHEET_CART_ID = "1lN1TtjXnpJJhP-SEfETWK-nPumFKoLHNpllLWkuUSkI"
$env:GSHEET_CART_GID = "132342150"
$env:USE_CART_SHEETS = "1"
$env:LOG_TO_STDOUT = "1"
# если нужно, можно явно задать типы апдейтов
$env:MAX_UPDATE_TYPES = "message_created,message_callback,message_command"

python E:\MAX\max_bot_polling.py
