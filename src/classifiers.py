from __future__ import annotations

import math
import re
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
    "美容",
    "コスメ",
    "メイク",
    "リップ",
    "スキンケア",
    "韓国コスメ",
    "qoo10",
    "メガ割",
    "ファンデ",
    "クッション",
    "下地",
    "ベースメイク",
    "セラム",
    "パック",
    "敏感肌",
    "乾燥",
    "毛穴",
    "日焼け止め",
    "アイシャドウ",
    "マスカラ",
    "カラコン",
    "レビュー",
    "比較",
    "繧ｳ繧ｹ繝｡",
    "繝｡繧､繧ｯ",
    "繝ｪ繝・・",
    "繧ｹ繧ｭ繝ｳ繧ｱ繧｢",
    "鄒主ｮｹ",
    "髻灘嵜繧ｳ繧ｹ繝｡",
    "繝｡繧ｬ蜑ｲ",
    "繝吶・繧ｹ繝｡繧､繧ｯ",
    "謨乗─閧・",
}

UNRELATED_KEYWORDS = {
    "食費",
    "固定費",
    "掃除",
    "収納",
    "冷蔵庫",
    "家計",
    "節約",
    "玄関",
    "鬟溯ｲｻ",
    "蝗ｺ螳夊ｲｻ",
    "謗・勁",
    "蜿守ｴ・",
    "蜀ｷ阡ｵ蠎ｫ",
}

PR_DISCLOSURE_HASHTAGS = {"#pr", "#ad", "#sponsored", "#promotion", "#タイアップ", "#提供", "#広告"}
PR_SUSPECT_TERMS = {
    "提供",
    "広告",
    "案件",
    "タイアップ",
    "プロモーション",
    "pr商品",
    "pr投稿",
    "prレビュー",
    "ｐｒ",
    "sponsored",
    "promotion",
    "謠蝉ｾ・",
    "蠎・相",
    "譯井ｻｶ",
}
GENERIC_HASHTAGS = {"#おすすめ", "#運営さん大好き", "#fyp", "#foryou", "#viral", "#tiktok", "#縺翫☆縺吶ａ", "#驕句霧縺輔ｓ螟ｧ螂ｽ縺・"}


def classify_strategy_category(post: ApiPost, creative: CreativeNote | None = None) -> str:
    return classify_strategy_category_detail(post, creative)["category"]


def classify_strategy_category_detail(post: ApiPost, creative: CreativeNote | None = None) -> dict[str, Any]:
    if creative and creative.account_strategy_category in VALID_STRATEGY_CATEGORIES:
        return {
            "category": creative.account_strategy_category,
            "source": "creative_notes.account_strategy_category",
            "reasons": [f"creative_notesで {creative.account_strategy_category} と入力されています"],
            "confidence": "high",
        }
    if creative and creative.is_beauty_core is True:
        return {
            "category": "beauty_core",
            "source": "creative_notes.is_beauty_core",
            "reasons": ["creative_notesで is_beauty_core=true と入力されています"],
            "confidence": "high",
        }
    if creative and creative.is_beauty_core is False:
        category = "unrelated"
        if creative.content_category in {"日常", "ネタ"}:
            category = "personal"
        return {
            "category": category,
            "source": "creative_notes.is_beauty_core",
            "reasons": ["creative_notesで is_beauty_core=false と入力されています"],
            "confidence": "high",
        }

    text = _post_text(post)
    beauty_hits = sorted({keyword for keyword in BEAUTY_KEYWORDS if keyword.lower() in text})
    unrelated_hits = sorted({keyword for keyword in UNRELATED_KEYWORDS if keyword.lower() in text})
    if beauty_hits:
        confidence = "high" if len(beauty_hits) >= 2 else "medium"
        return {
            "category": "beauty_core",
            "source": "caption_keywords",
            "reasons": [f"美容関連キーワード: {', '.join(beauty_hits[:5])}"],
            "confidence": confidence,
        }
    if unrelated_hits:
        return {
            "category": "unrelated",
            "source": "caption_keywords",
            "reasons": [f"非美容キーワード: {', '.join(unrelated_hits[:5])}"],
            "confidence": "medium",
        }
    return {
        "category": "unknown",
        "source": "not_enough_data",
        "reasons": ["caption/titleだけでは美容本流か判断できません。creative_notesの入力が必要です"],
        "confidence": "low",
    }


def detect_pr_status(post: ApiPost, creative: CreativeNote | None = None) -> str:
    text = _post_text(post)
    hashtags = {_normalize_hashtag(tag) for tag in post.hashtags}
    if hashtags & PR_DISCLOSURE_HASHTAGS or re.search(r"(^|\s|#)(pr|ad)(\s|$)", text):
        return "明示PR"
    if creative and creative.is_pr is True:
        return "PR疑い"
    if any(term.lower() in text for term in PR_SUSPECT_TERMS):
        return "PR疑い"
    if creative and creative.is_pr is False:
        return "非PR"
    if not text.strip():
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
    display_names: dict[str, str] = {}
    for row in rows:
        for tag in row.get("hashtags", []):
            normalized = _normalize_hashtag(tag)
            if not normalized:
                continue
            counts[normalized] += 1
            display_names.setdefault(normalized, tag.strip())
            if median_views is not None and (row.get("view_count") or 0) > median_views:
                above_median[normalized] += 1
    grouped = {
        "single": [],
        "test_candidates": [],
        "trend_candidates": [],
        "promising_candidates": [],
        "generic": [],
        "pr_disclosure": [],
    }
    for normalized, count in counts.most_common():
        item = {"tag": display_names[normalized], "count": count, "above_median_count": above_median[normalized]}
        if normalized in PR_DISCLOSURE_HASHTAGS:
            grouped["pr_disclosure"].append(item)
        elif normalized in GENERIC_HASHTAGS:
            grouped["generic"].append(item)
        elif count == 1:
            grouped["single"].append(item)
        elif count <= 3:
            grouped["test_candidates"].append(item)
        elif above_median[normalized] >= 2:
            grouped["promising_candidates"].append(item)
        else:
            grouped["trend_candidates"].append(item)
    return grouped


def _post_text(post: ApiPost) -> str:
    return f"{post.title} {post.video_description} {' '.join(post.hashtags)}".lower()


def _normalize_hashtag(tag: str) -> str:
    text = str(tag or "").strip().replace("＃", "#")
    if text and not text.startswith("#"):
        text = f"#{text}"
    return text.lower()
