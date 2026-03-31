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


def _find_idx(header: list, names: list[str]) -> int | None:
    names_l = [n.lower() for n in names]
    for i, h in enumerate(header):
        h_str = str(h).strip().lower()
        if not h_str:
            continue
        for n in names_l:
            if n in h_str:
                return i
    return None


def find_client_by_inn(inn: str) -> dict | None:
    """Ищет клиента по ИНН в таблице клиентов."""
    sheet = _get_clients_sheet()
    values = sheet.get_all_values()
    if not values:
        return None

    header = values[0]

    i_name = _find_idx(header, ["наименование", "название"])
    i_inn = _find_idx(header, ["инн"])
    i_contract = _find_idx(header, ["номер договора", "номер договор", "договор"])
    i_status = _find_idx(header, ["статус договора", "статус"])
    i_manager = _find_idx(header, ["менеджер продаж", "менеджер"])

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

    i_name = _find_idx(header, ["наименование", "название"])
    i_inn = _find_idx(header, ["инн"])
    i_contract = _find_idx(header, ["номер договора", "номер договор", "договор"])
    i_status = _find_idx(header, ["статус договора", "статус"])
    i_manager = _find_idx(header, ["менеджер продаж", "менеджер"])

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

    i_name = _find_idx(header, ["manager_name", "менеджер"])
    i_id = _find_idx(header, ["telegram_id", "max id", "id max", "id макс", "max_id", "макс"])

    name_lower = manager_name.strip().lower()
    for row in values[1:]:
        row_name = row[i_name] if i_name is not None and len(row) > i_name else ""
        if row_name.strip().lower() == name_lower:
            raw = row[i_id] if i_id is not None and len(row) > i_id else ""
            try:
                return int(float(raw)) if str(raw).strip() else None
            except Exception:
                return None
    return None


def update_manager_id(manager_name: str, new_id: str):
    """Обновляет ID менеджера в таблице managers."""
    sheet = _get_managers_sheet()
    values = sheet.get_all_values()
    if not values:
        return

    header = values[0]
    i_name = _find_idx(header, ["manager_name", "менеджер"])
    i_id = _find_idx(header, ["telegram_id", "max id", "id max", "id макс", "max_id", "макс"])
    if i_name is None or i_id is None:
        return

    for idx, row in enumerate(values[1:], start=2):
        row_name = row[i_name] if len(row) > i_name else ""
        if row_name.strip().lower() == manager_name.strip().lower():
            sheet.update_cell(idx, i_id + 1, str(new_id))
            return


def update_manager_for_clients(old_name: str, new_name: str) -> int:
    """Массово меняет менеджера у клиентов (по имени), возвращает кол-во обновлений."""
    sheet = _get_clients_sheet()
    values = sheet.get_all_values()
    if not values:
        return 0

    header = values[0]
    i_manager = _find_idx(header, ["менеджер продаж", "менеджер"])
    if i_manager is None:
        return 0

    updated = 0
    for idx, row in enumerate(values[1:], start=2):
        row_manager = row[i_manager] if len(row) > i_manager else ""
        if row_manager.strip().lower() == old_name.strip().lower():
            sheet.update_cell(idx, i_manager + 1, new_name)
            updated += 1
    return updated