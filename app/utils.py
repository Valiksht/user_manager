from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.config import settings

default_timezone = ZoneInfo(settings.DEFAULT_TIMEZONE)


def normalize_datetime(
        value: datetime,
        time_zone: ZoneInfo = default_timezone,
) -> datetime:
    """
    Функция нормализации формата даты и времени.
    """
    if value.utcoffset() is None:
        value = value.replace(tzinfo=time_zone)
    return value.astimezone(timezone.utc)