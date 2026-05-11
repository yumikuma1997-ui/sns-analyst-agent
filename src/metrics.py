from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Any

from models import ApiPost, Post, PostMetric
from utils import mean, median


def safe_divide(numerator: int | float | None, denominator: int | float | None) -> float | None:
    if numerator is None or denominator is None:
        return None
    if denominator == 0:
        return None
    return float(numerator) / float(denominator)


def trimmed_mean_excluding_top_percent(values: list[int | float | None], top_percent: float = 10) -> float | None:
    cleaned = sorted(float(value) for value in values if value is not None)
    if not cleaned:
        return None
    remove_count = math.floor(len(cleaned) * top_percent / 100)
    if remove_count <= 0:
        return mean(cleaned)
    trimmed = cleaned[: max(1, len(cleaned) - remove_count)]
    return mean(trimmed)


def calculate_api_metrics(post: ApiPost) -> dict[str, float | int | None]:
    return {
        "view_count": post.view_count,
        "like_count": post.like_count,
        "comment_count": post.comment_count,
        "share_count": post.share_count,
        "like_rate": safe_divide(post.like_count, post.view_count),
        "comment_rate": safe_divide(post.comment_count, post.view_count),
        "share_rate": safe_divide(post.share_count, post.view_count),
    }


def summarize_api_posts(rows: list[dict[str, Any]], now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    views = [row.get("view_count") for row in rows]
    dated = [row for row in rows if row.get("posted_dt") is not None]
    recent10 = sorted(dated, key=lambda row: row["posted_dt"], reverse=True)[:10]
    recent30 = [row for row in dated if row["posted_dt"] >= now - timedelta(days=30)]
    sorted_dates = sorted(row["posted_dt"] for row in dated)
    gaps = [(sorted_dates[index] - sorted_dates[index - 1]).days for index in range(1, len(sorted_dates))]
    return {
        "post_count": len(rows),
        "average_views": mean(views),
        "median_views": median(views),
        "max_views": max((value for value in views if value is not None), default=None),
        "min_views": min((value for value in views if value is not None), default=None),
        "top_10_excluded_average": trimmed_mean_excluding_top_percent(views, 10),
        "recent_10_median": median(row.get("view_count") for row in recent10),
        "recent_30_count": len(recent30),
        "recent_30_median": median(row.get("view_count") for row in recent30),
        "average_like_rate": mean(row.get("like_rate") for row in rows),
        "average_comment_rate": mean(row.get("comment_rate") for row in rows),
        "average_share_rate": mean(row.get("share_rate") for row in rows),
        "average_post_interval_days": mean(gaps),
        "max_post_interval_days": max(gaps, default=None),
    }


def calculate_post_metrics(post: Post) -> PostMetric:
    return PostMetric(
        post=post,
        like_rate=safe_divide(post.likes, post.views),
        comment_rate=safe_divide(post.comments, post.views),
        save_rate=safe_divide(post.saves, post.views),
        share_rate=safe_divide(post.shares, post.views),
        follow_conversion_rate=safe_divide(post.follow_gains, post.views),
        profile_visit_rate=safe_divide(post.profile_visits, post.views),
        avg_retention_rate=safe_divide(post.avg_watch_time_sec, post.duration_sec),
    )


def calculate_all_post_metrics(posts: list[Post]) -> list[PostMetric]:
    return [calculate_post_metrics(post) for post in posts]


def summarize_posts(metrics: list[PostMetric]) -> dict[str, float | int | None | str]:
    posts = [metric.post for metric in metrics]
    views = [post.views for post in posts]
    posts_with_missing_views = sum(1 for post in posts if post.views is None)
    posts_with_missing_rate_inputs = sum(
        1
        for post in posts
        if post.views in (None, 0)
        or post.likes is None
        or post.comments is None
        or post.saves is None
        or post.shares is None
        or post.follow_gains is None
    )
    return {
        "post_count": len(posts),
        "average_views": mean(views),
        "median_views": median(views),
        "max_views": max((view for view in views if view is not None), default=None),
        "average_like_rate": mean(metric.like_rate for metric in metrics),
        "average_comment_rate": mean(metric.comment_rate for metric in metrics),
        "average_save_rate": mean(metric.save_rate for metric in metrics),
        "average_share_rate": mean(metric.share_rate for metric in metrics),
        "average_follow_conversion_rate": mean(metric.follow_conversion_rate for metric in metrics),
        "average_profile_visit_rate": mean(metric.profile_visit_rate for metric in metrics),
        "average_completion_rate": mean(post.completion_rate for post in posts),
        "average_retention_rate": mean(metric.avg_retention_rate for metric in metrics),
        "data_sufficiency": _data_sufficiency(len(posts)),
        "posts_with_missing_views": posts_with_missing_views,
        "posts_with_missing_rate_inputs": posts_with_missing_rate_inputs,
        "data_quality_note": _data_quality_note(posts_with_missing_views, posts_with_missing_rate_inputs),
    }


def _data_sufficiency(post_count: int) -> str:
    if post_count == 0:
        return "投稿データがないためデータ不足"
    if post_count < 10:
        return "投稿数が少ないため暫定仮説"
    return "分析可能。ただし継続検証が必要"


def _data_quality_note(posts_with_missing_views: int, posts_with_missing_rate_inputs: int) -> str:
    if posts_with_missing_views == 0 and posts_with_missing_rate_inputs == 0:
        return "主要KPIの入力は揃っています。"
    return (
        f"データ不足: 再生数未入力 {posts_with_missing_views}件、"
        f"率計算に必要な入力不足 {posts_with_missing_rate_inputs}件があります。"
    )
