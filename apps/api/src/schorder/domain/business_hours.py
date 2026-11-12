"""营业时间判定。

时区说明：中国不使用夏令时，固定 +08:00 即可，避免依赖 tzdata
（Windows 上的 zoneinfo 默认没有 IANA 数据库）。

跨夜处理：close_time < open_time 表示营业到次日，例如 22:00-02:00。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

CN_TZ = timezone(timedelta(hours=8))


def now_cn() -> datetime:
    return datetime.now(CN_TZ)


def is_open(hours: list[tuple[int, str, str]], now: datetime | None = None) -> bool:
    """hours 是 (weekday, open_time, close_time) 的列表，weekday 1=周一。"""
    current = now or now_cn()
    weekday = current.isoweekday()
    hhmm = current.strftime("%H:%M")

    for day, open_time, close_time in hours:
        if day != weekday:
            continue
        if open_time <= close_time:
            if open_time <= hhmm < close_time:
                return True
        else:  # 跨夜
            if hhmm >= open_time or hhmm < close_time:
                return True
    return False


def next_open_hint(hours: list[tuple[int, str, str]], now: datetime | None = None) -> str | None:
    """未来 7 天内最近的一次开门时间，用于"休息中，XX:XX 开始营业"。"""
    current = now or now_cn()
    weekday = current.isoweekday()
    hhmm = current.strftime("%H:%M")

    for offset in range(8):
        day = (weekday - 1 + offset) % 7 + 1
        candidates = sorted(open_time for d, open_time, _ in hours if d == day)
        if not candidates:
            continue
        if offset == 0:
            for open_time in candidates:
                if open_time > hhmm:
                    return "今天 " + open_time
        else:
            label = "明天" if offset == 1 else f"周{'一二三四五六日'[day - 1]}"
            return f"{label} {candidates[0]}"
    return None
