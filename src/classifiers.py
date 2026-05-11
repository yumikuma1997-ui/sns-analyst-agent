from __future__ import annotations

import math
from collections import Counter
from typing import Any

from models import ApiPost, CreativeNote
from utils import duration_bucket, parse_datetime, time_bucket


VALID_STRATEGY_CATEGORIES = {
    "beauty_core",
    "beauty_adjacent",
    "lifestyle",
    "personal",
    "unrelated",
}

BEAUTY_KEYWORDS = {
    "コスメ",
    "メイク",
    "リップ",
    "スキンケア",
    "美容",
    "肌",
    "化粧",
    "韓国コスメ",
    "qoo10",
    "メガ割",
    "ティント",
    "クッション",
    "ファンデ",
    "セラム",
    "パック",
    "カラコン",
    "マスカラ",
    "アイシャドウ",
    "ベースメイク",
    "毛穴",
    "敏感肌",
    "pdrn",
    "abib",
    "skin1004",
    "missha",
}

UNRELATED_KEYWORDS = {
    "食費",
    "固定費",
    "掃除",
    "収納",
    "冷蔵庫",
    "玄関",
    "節約",
    "家計",
}

PR_EXPLICIT_TERMS = {"#pr", "#ad", "pr", "ad", "タイアップ"}
PR_SUSPECT_TERMS = {"提供", "広告", "案件", "プロモーション"}
GENERIC_HASHTAGS = {"#おすすめ", "#運営さん大好き", "#fyp", "#foryou", "#viral", "#tiktok"}


def classify_strategy_category(post: ApiPost, creative: CreativeNote | None = None) -> str:
    if creative and creative.account_strategy_category in VALID_STRATEGY_CATEGORIES:
        return creative.account_strategy_category
    text = _post_text(post)
    if any(keyword.lower() in text for keyword in BEAUTY_KEYWORDS):
        return "beauty_core"
    if any(keyword.lower() in text for keyword in UNRELATED_KEYWORDS):
        return "unrelated"
    return "unknown"


def detect_pr_status(post: ApiPost, creative: CreativeNote | None = None) -> str:
    text = _post_text(post)
    if creative and creative.is_pr is False:
        return "非PR"
    if any(term in text for term in PR_EXPLICIT_TERMS):
        return "明示PR"
    if creative and creative.is_pr is True:
        return "PR疑い"
    if any(term.lower() in text for term in PR_SUSPECT_TERMS):
        return "PR疑い"
    if not text:
        return "不明"
    return "非PR"


def classify_duration_bucket(seconds: float | None) -> str:
    return duration_bucket(seconds)


def classify_post_time_bucket(posted_at: str) -> str:
    parsed = parse_datetime(posted_at)
    if parsed is None:
        return "データ不足"
    return time_bucket(f"{parsed.hour:02d}:{parsed.minute:02d}")


def detect_outlier_viral_posts(rows: list[dict[str, Any]], median_views: float | None) -> list[dict[str, Any]]:
    views = sorted((row.get("view_count") or 0 for row in rows), reverse=True)
    if not views:
        return []
    top_count = max(1, math.ceil(len(views) * 0.05))
    top5_threshold = views[top_count - 1]
    viral = []
    for row in rows:
        value = row.get("view_count") or 0
        reasons = []
        if median_views and median_views > 0 and value >= median_views * 20:
            reasons.append("中央値の20倍以上")
        if value >= top5_threshold:
            reasons.append("上位5%")
        if value >= 1_000_000:
            reasons.append("100万再生以上")
        if reasons:
            item = dict(row)
            item["viral_reasons"] = reasons
            viral.append(item)
    return sorted(viral, key=lambda row: row.get("view_count") or 0, reverse=True)


def hashtag_groups(rows: list[dict[str, Any]], median_views: float | None) -> dict[str, list[dict[str, Any]]]:
    counts: Counter[str] = Counter()
    above_median: Counter[str] = Counter()
    for row in rows:
        for tag in row.get("hashtags", []):
            normalized = tag.strip()
            if not normalized:
                continue
            counts[normalized] += 1
            if median_views is not None and (row.get("view_count") or 0) > median_views:
                above_median[normalized] += 1
    grouped = {
        "single": [],
        "test_candidates": [],
        "trend_candidates": [],
        "promising_candidates": [],
        "generic": [],
    }
    for tag, count in counts.most_common():
        item = {"tag": tag, "count": count, "above_median_count": above_median[tag]}
        if tag.lower() in GENERIC_HASHTAGS:
            grouped["generic"].append(item)
        elif count == 1:
            grouped["single"].append(item)
        elif count <= 3:
            grouped["test_candidates"].append(item)
        elif above_median[tag] >= 2:
            grouped["promising_candidates"].append(item)
        else:
            grouped["trend_candidates"].append(item)
    return grouped


def _post_text(post: ApiPost) -> str:
    return f"{post.title} {post.video_description} {' '.join(post.hashtags)}".lower()
