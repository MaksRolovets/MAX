"""Парсинг ИНН и номеров договоров СДЭК из текста пользователя."""

import re


def parse_inn(text: str) -> str | None:
    """Ищет ИНН (10 или 12 цифр) в тексте."""
    m = re.search(r"\b(\d{10}|\d{12})\b", text)
    return m.group(1) if m else None


def parse_contract(text: str) -> str | None:
    """Ищет номер договора СДЭК в тексте.

    Форматы: SZ-LBS2-21, ИМ1231247522, КУ-СЗ-123, ДЛП-123,
    ЛБС-123, НДИМ-123, НДДЛП-123, ИМ-123, и т.д.
    """
    patterns = [
        r"[A-ZА-ЯЁ]{2,5}-[A-ZА-ЯЁ0-9]{2,5}-\d+",   # SZ-LBS2-21
        r"(?:ИМ|КУ|СЗ|ДЛП|ЛБС|НДИМ|НДДЛП|IM|KU|SZ)\d{5,}",  # ИМ1231247522
        r"(?:ИМ|КУ|СЗ|ДЛП|ЛБС|НДИМ|НДДЛП|IM|KU|SZ)-\d+",    # ИМ-123
        r"\d{2}[A-ZА-ЯЁ]{2,4}\d{5,}",                 # 21ИМ12345
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(0)
    return None


def extract_data(text: str) -> dict:
    """Извлекает ИНН и номер договора из текста."""
    return {
        "inn": parse_inn(text),
        "contract": parse_contract(text),
    }
