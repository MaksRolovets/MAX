"""Логика ротации КЛО по специальным дням."""

from datetime import datetime, timezone, timedelta

from app import settings

MSK = timezone(timedelta(hours=3))


def is_special_day() -> bool:
    """Проверяет, является ли сегодня (по МСК) специальным днём ротации."""
    today = datetime.now(MSK).strftime("%m-%d")
    return today in settings.KLO_SPECIAL_DAYS


def get_klo_user_id() -> int:
    """Возвращает user_id КЛО с учётом ротации."""
    if is_special_day() and settings.KLO_USER_ID_ROTATION:
        return settings.KLO_USER_ID_ROTATION
    return settings.KLO_USER_ID
