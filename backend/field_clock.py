"""Calendar dates for BioGuard's Malaysia pilot, independent of the server timezone."""
from datetime import datetime, timedelta, timezone
MALAYSIA=timezone(timedelta(hours=8))
def field_today(at=None):
    return (at or datetime.now(timezone.utc)).astimezone(MALAYSIA).date()
