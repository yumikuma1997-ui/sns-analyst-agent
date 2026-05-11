from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from models import AccountProfile, Post, ReferencePost
from utils import parse_bool, parse_float, parse_int, parse_rate, split_tags


POST_ALIASES = {
    "date": ["date", "投稿日"],
    "day_of_week": ["day_of_week", "投稿曜日", "曜日"],
    "time": ["time", "投稿時間", "時間"],
    "title": ["title", "動画タイトルまたは概要", "動画タイトル", "概要"],
    "url": ["url", "動画URL", "URL"],
    "genre": ["genre", "動画ジャンル", "ジャンル"],
    "sound": ["sound", "使用した音源", "音源"],
    "hashtags": ["hashtags", "使用したハッシュタグ", "ハッシュタグ"],
    "hook": ["hook", "冒頭3秒の内容", "冒頭3秒", "フック"],
    "duration_sec": ["duration_sec", "動画尺", "尺"],
    "structure": ["structure", "動画構成", "構成"],
    "has_cta": ["has_cta", "CTAの有無", "CTA"],
    "views": ["views", "再生数"],
    "likes": ["likes", "いいね数", "いいね"],
    "comments": ["comments", "コメント数", "コメント"],
    "saves": ["saves", "保存数", "保存"],
    "shares": ["shares", "シェア数", "シェア"],
    "profile_visits": ["profile_visits", "プロフィールアクセス数", "プロフィールアクセス"],
    "follow_gains": ["follow_gains", "フォロー増加数", "フォロー増加"],
    "completion_rate": ["completion_rate", "完視聴率"],
    "avg_watch_time_sec": ["avg_watch_time_sec", "平均視聴時間"],
    "impressions": ["impressions", "インプレッション"],
    "traffic_sources": ["traffic_sources", "流入元"],
    "notes": ["notes", "投稿メモ", "メモ"],
}

REFERENCE_POST_ALIASES = {
    "account_name": ["account_name", "reference_account", "competitor_account", "アカウント名", "参考アカウント"],
    "account_url": ["account_url", "account_profile_url", "プロフィールURL", "アカウントURL"],
    "account_role": ["account_role", "role", "種別"],
}


def load_account_profile(path: str | Path) -> AccountProfile:
    data = _load_json(path)
    return AccountProfile.from_dict(data)


def load_posts_csv(path: str | Path) -> list[Post]:
    with Path(path).open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
    return [_post_from_row(row) for row in rows]


def load_reference_posts_csv(path: str | Path | None) -> list[ReferencePost]:
    if path is None:
        return []
    csv_path = Path(path)
    if not csv_path.exists():
        return []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
    return [_reference_post_from_row(row) for row in rows]


def load_trends(path: str | Path) -> list[dict[str, Any]]:
    data = _load_json(path)
    if isinstance(data, dict):
        trends = data.get("trends", [])
        return trends if isinstance(trends, list) else []
    return data if isinstance(data, list) else []


def load_competitors(path: str | Path) -> list[dict[str, Any]]:
    data = _load_json(path)
    if isinstance(data, dict):
        competitors = data.get("competitors", [])
        return competitors if isinstance(competitors, list) else []
    return data if isinstance(data, list) else []


def _load_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as file:
        return json.load(file)


def _get(row: dict[str, Any], canonical_key: str) -> Any:
    for key in POST_ALIASES[canonical_key]:
        if key in row:
            return row.get(key)
    return None


def _post_from_row(row: dict[str, Any]) -> Post:
    return Post(
        date=str(_get(row, "date") or "").strip(),
        day_of_week=str(_get(row, "day_of_week") or "").strip(),
        time=str(_get(row, "time") or "").strip(),
        title=str(_get(row, "title") or "無題").strip(),
        url=str(_get(row, "url") or "").strip(),
        genre=str(_get(row, "genre") or "").strip(),
        sound=str(_get(row, "sound") or "").strip(),
        hashtags=split_tags(_get(row, "hashtags")),
        hook=str(_get(row, "hook") or "").strip(),
        duration_sec=parse_float(_get(row, "duration_sec")),
        structure=str(_get(row, "structure") or "").strip(),
        has_cta=parse_bool(_get(row, "has_cta")),
        views=parse_int(_get(row, "views")),
        likes=parse_int(_get(row, "likes")),
        comments=parse_int(_get(row, "comments")),
        saves=parse_int(_get(row, "saves")),
        shares=parse_int(_get(row, "shares")),
        profile_visits=parse_int(_get(row, "profile_visits")),
        follow_gains=parse_int(_get(row, "follow_gains")),
        completion_rate=parse_rate(_get(row, "completion_rate")),
        avg_watch_time_sec=parse_float(_get(row, "avg_watch_time_sec")),
        impressions=parse_int(_get(row, "impressions")),
        traffic_sources=str(_get(row, "traffic_sources") or "").strip(),
        notes=str(_get(row, "notes") or "").strip(),
    )


def _get_reference(row: dict[str, Any], canonical_key: str) -> Any:
    for key in REFERENCE_POST_ALIASES[canonical_key]:
        if key in row:
            return row.get(key)
    return None


def _reference_post_from_row(row: dict[str, Any]) -> ReferencePost:
    post = _post_from_row(row)
    return ReferencePost(
        **post.__dict__,
        account_name=str(_get_reference(row, "account_name") or "データ不足").strip(),
        account_url=str(_get_reference(row, "account_url") or "").strip(),
        account_role=str(_get_reference(row, "account_role") or "competitor").strip(),
    )
