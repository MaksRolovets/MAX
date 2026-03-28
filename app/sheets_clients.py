"""Поиск клиентов и менеджеров в Google Sheets.

Таблица clients: Наименование контрагента | ИНН контрагента | Номер договора | Статус договора | Менеджер продаж
Таблица managers: manager_name | telegram_id (в MAX — max_user_id)
"""

from app import settings
from app.sheets_base import open_sheet

_clients_sheet = None
_managers_sheet = None


def _get_clients_sheet():
    global _clients_sheet
    if _clients_sheet is None:
        _clients_sheet = open_sheet(settings.GSHEET_CLIENTS_ID, tab=settings.GSHEET_CLIENTS_TAB)
    return _clients_sheet


def _get_managers_sheet():
    global _managers_sheet
    if _managers_sheet is None:
        _managers_sheet = open_sheet(settings.GSHEET_MANAGERS_ID, tab=settings.GSHEET_MANAGERS_TAB)
    return _managers_sheet


def find_client_by_inn(inn: str) -> dict | None:
    """Ищет клиента по ИНН в таблице клиентов."""
    sheet = _get_clients_sheet()
    values = sheet.get_all_values()
    if not values:
        return None

    header = values[0]

    def idx(name: str):
        for i, h in enumerate(header):
            if name.lower() in h.lower():
                return i
        return None

    i_name = idx("Наименование")
    i_inn = idx("ИНН")
    i_contract = idx("Номер договора")
    i_status = idx("Статус")
    i_manager = idx("Менеджер")

    for row in values[1:]:
        row_inn = row[i_inn] if i_inn is not None and len(row) > i_inn else ""
        if row_inn.strip() == inn.strip():
            return {
                "name": row[i_name] if i_name is not None and len(row) > i_name else "",
                "inn": row_inn,
                "contract": row[i_contract] if i_contract is not None and len(row) > i_contract else "",
                "status": row[i_status] if i_status is not None and len(row) > i_status else "",
                "manager_name": row[i_manager] if i_manager is not None and len(row) > i_manager else "",
            }
    return None


def find_client_by_contract(contract: str) -> dict | None:
    """Ищет клиента по номеру договора."""
    sheet = _get_clients_sheet()
    values = sheet.get_all_values()
    if not values:
        return None

    header = values[0]

    def idx(name: str):
        for i, h in enumerate(header):
            if name.lower() in h.lower():
                return i
        return None

    i_name = idx("Наименование")
    i_inn = idx("ИНН")
    i_contract = idx("Номер договора")
    i_status = idx("Статус")
    i_manager = idx("Менеджер")

    contract_lower = contract.strip().lower()
    for row in values[1:]:
        row_contract = row[i_contract] if i_contract is not None and len(row) > i_contract else ""
        if row_contract.strip().lower() == contract_lower:
            return {
                "name": row[i_name] if i_name is not None and len(row) > i_name else "",
                "inn": row[i_inn] if i_inn is not None and len(row) > i_inn else "",
                "contract": row_contract,
                "status": row[i_status] if i_status is not None and len(row) > i_status else "",
                "manager_name": row[i_manager] if i_manager is not None and len(row) > i_manager else "",
            }
    return None


def find_manager_id(manager_name: str) -> int | None:
    """Ищет MAX user_id менеджера по имени."""
    if not manager_name:
        return None
    sheet = _get_managers_sheet()
    values = sheet.get_all_values()
    if not values:
        return None

    header = values[0]

    def idx(name: str):
        for i, h in enumerate(header):
            if name.lower() in h.lower():
                return i
        return None

    i_name = idx("manager_name")
    i_id = idx("telegram_id")  # в MAX это будет max_user_id

    name_lower = manager_name.strip().lower()
    for row in values[1:]:
        row_name = row[i_name] if i_name is not None and len(row) > i_name else ""
        if row_name.strip().lower() == name_lower:
            raw = row[i_id] if i_id is not None and len(row) > i_id else ""
            try:
                return int(float(raw))
            except (ValueError, TypeError):
                return None
    return None


def update_manager_for_clients(old_manager: str, new_manager: str) -> int:
    """Массово обновляет менеджера у всех клиентов. Возвращает кол-во обновлённых."""
    sheet = _get_clients_sheet()
    values = sheet.get_all_values()
    if not values:
        return 0

    header = values[0]

    def idx(name: str):
        for i, h in enumerate(header):
            if name.lower() in h.lower():
                return i
        return None

    i_manager = idx("Менеджер")
    if i_manager is None:
        return 0

    count = 0
    old_lower = old_manager.strip().lower()
    for row_idx, row in enumerate(values[1:], start=2):
        if len(row) > i_manager and row[i_manager].strip().lower() == old_lower:
            sheet.update_cell(row_idx, i_manager + 1, new_manager)
            count += 1
    return count


def update_manager_id(manager_name: str, new_id: str):
    """Обновляет ID менеджера в таблице менеджеров."""
    sheet = _get_managers_sheet()
    values = sheet.get_all_values()
    if not values:
        return

    header = values[0]

    def idx(name: str):
        for i, h in enumerate(header):
            if name.lower() in h.lower():
                return i
        return None

    i_name = idx("manager_name")
    i_id = idx("telegram_id")

    name_lower = manager_name.strip().lower()
    for row_idx, row in enumerate(values[1:], start=2):
        row_name = row[i_name] if i_name is not None and len(row) > i_name else ""
        if row_name.strip().lower() == name_lower:
            if i_id is not None:
                sheet.update_cell(row_idx, i_id + 1, new_id)
            return

    # Менеджер не найден — добавляем
    new_row = [""] * len(header)
    if i_name is not None:
        new_row[i_name] = manager_name
    if i_id is not None:
        new_row[i_id] = new_id
    sheet.append_row(new_row, value_input_option="RAW")
