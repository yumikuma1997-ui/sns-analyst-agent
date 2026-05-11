from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


DATA_INSUFFICIENT = "データ不足"


def parse_int(value: Any) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    text = text.replace(",", "").replace("回", "").replace("件", "").replace("人", "")
    try:
        return int(float(text))
    except ValueError:
        return None


def parse_float(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    text = text.replace(",", "").replace("秒", "").replace("s", "")
    if ":" in text:
        parts = text.split(":")
        try:
            if len(parts) == 2:
                return int(parts[0]) * 60 + float(parts[1])
            if len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        except ValueError:
            return None
    try:
        return float(text)
    except ValueError:
        return None


def parse_rate(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    is_percent = "%" in text
    text = text.replace("%", "").replace(",", "")
    try:
        number = float(text)
    except ValueError:
        return None
    if is_percent or number > 1:
        return number / 100
    return number


def parse_bool(value: Any) -> bool | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    if not text:
        return None
    if text in {"true", "yes", "y", "1", "あり", "有", "可", "ok", "縺ゅｊ", "譛・", "蜿ｯ"}:
        return True
    if text in {"false", "no", "n", "0", "なし", "無", "不可", "ng", "縺ｪ縺・", "辟｡", "荳榊庄"}:
        return False
    return None


def split_tags(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).replace("、", " ").replace("縲・", " ").replace(",", " ").replace("\n", " ")
    return [part.strip() for part in text.split() if part.strip()]


def extract_hashtags(text: str) -> list[str]:
    tags = []
    for part in str(text or "").replace("\n", " ").split():
        if part.startswith("#") and len(part) > 1:
            tags.append(part.strip(".,;:!?)）】」』、。"))
    return tags


def ensure_parent_dir(path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def format_number(value: int | float | None) -> str:
    if value is None:
        return DATA_INSUFFICIENT
    if isinstance(value, float) and not value.is_integer():
        return f"{value:,.1f}"
    return f"{int(value):,}"


def format_percent(value: float | None) -> str:
    if value is None:
        return DATA_INSUFFICIENT
    return f"{value * 100:.2f}%"


def format_bool(value: bool | None) -> str:
    if value is None:
        return DATA_INSUFFICIENT
    return "可" if value else "不可"


def mean(values: Iterable[float | int | None]) -> float | None:
    cleaned = [float(value) for value in values if value is not None]
    if not cleaned:
        return None
    return sum(cleaned) / len(cleaned)


def median(values: Iterable[float | int | None]) -> float | None:
    cleaned = sorted(float(value) for value in values if value is not None)
    if not cleaned:
        return None
    midpoint = len(cleaned) // 2
    if len(cleaned) % 2:
        return cleaned[midpoint]
    return (cleaned[midpoint - 1] + cleaned[midpoint]) / 2


def top_terms(values: Iterable[str], limit: int = 5) -> list[tuple[str, int]]:
    cleaned = [value.strip() for value in values if value and value.strip()]
    return Counter(cleaned).most_common(limit)


def safe_join(items: Iterable[str], fallback: str = DATA_INSUFFICIENT) -> str:
    cleaned = [item for item in items if item]
    if not cleaned:
        return fallback
    return "、".join(cleaned)


def parse_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    if not text:
        return None
    if text.isdigit():
        try:
            return datetime.fromtimestamp(int(text), tz=timezone.utc)
        except (ValueError, OSError):
            return None
    for fmt in (
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%Y/%m/%d %H:%M",
        "%Y/%m/%d",
        "%Y.%m.%d",
    ):
        try:
            parsed = datetime.strptime(text, fmt)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed
        except ValueError:
            continue
    return None


def parse_date(value: str) -> datetime | None:
    parsed = parse_datetime(value)
    if parsed is None:
        return None
    return parsed.replace(hour=0, minute=0, second=0, microsecond=0)


def time_bucket(value: str | None) -> str:
    if not value:
        return DATA_INSUFFICIENT
    hour_text = str(value).split(":")[0].strip()
    try:
        hour = int(hour_text)
    except ValueError:
        return DATA_INSUFFICIENT
    if 5 <= hour < 11:
        return "朝"
    if 11 <= hour < 17:
        return "昼"
    if 17 <= hour < 22:
        return "夜"
    return "深夜"


def duration_bucket(seconds: float | None) -> str:
    if seconds is None:
        return DATA_INSUFFICIENT
    if seconds < 15:
        return "15秒未満"
    if seconds < 30:
        return "15-29秒"
    if seconds < 45:
        return "30-44秒"
    if seconds < 60:
        return "45-59秒"
    return "60秒以上"
