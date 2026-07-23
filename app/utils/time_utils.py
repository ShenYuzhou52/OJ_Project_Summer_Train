from datetime import datetime, timezone, timedelta

_BEIJING = timezone(timedelta(hours=8))

def now_utc() -> str:
    return datetime.now(_BEIJING).strftime("%Y-%m-%dT%H:%M:%SZ")
