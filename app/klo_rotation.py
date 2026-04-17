"""Логика ротации КЛО по специальным дням и выходным."""

from datetime import datetime, timezone, timedelta

from app import settings

MSK = timezone(timedelta(hours=3))


def is_special_day() -> bool:
    """Проверяет, является ли сегодня (по МСК) специальным днём ротации."""
    today = datetime.now(MSK).strftime("%m-%d")
    return today in settings.KLO_SPECIAL_DAYS


def is_weekend() -> bool:
    """Возвращает True в Сб/Вс (по МСК) или в даты из WEEKEND_HOLIDAYS."""
    now = datetime.now(MSK)
    if now.weekday() >= 5:  # 5=Сб, 6=Вс
        return True
    return now.strftime("%Y-%m-%d") in settings.WEEKEND_HOLIDAYS


def get_klo_user_id() -> int:
    """Возвращает user_id КЛО с учётом выходных и ротации."""
    if is_weekend() and settings.WEEKEND_DUTY_USER_ID:
        return settings.WEEKEND_DUTY_USER_ID
    if is_special_day() and settings.KLO_USER_ID_ROTATION:
        return settings.KLO_USER_ID_ROTATION
    return settings.KLO_USER_ID
