from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from models import (
    AccountProfile,
    ApiPost,
    CompetitorPost,
    CreativeNote,
    ManualInsight,
    TrendResearch,
    manual_insight_from_dict,
)
from utils import extract_hashtags, parse_bool, parse_datetime, parse_float, parse_int, split_tags


def load_account_profile(path: str | Path) -> AccountProfile:
    data = _load_json(path)
    return AccountProfile.from_dict(data if isinstance(data, dict) else {})


def load_api_posts(path: str | Path | None) -> list[ApiPost]:
    return [_api_post_from_row(row) for row in _load_records(path, keys=("api_posts", "posts", "videos"))]


def load_manual_insights(path: str | Path | None) -> list[ManualInsight]:
    return [manual_insight_from_dict(row) for row in _load_records(path, keys=("manual_insights", "insights"))]


def load_creative_notes(path: str | Path | None) -> list[CreativeNote]:
    return [_creative_note_from_row(row) for row in _load_records(path, keys=("creative_notes", "notes"))]


def load_trend_research(path: str | Path | None) -> list[TrendResearch]:
    return [_trend_from_row(row) for row in _load_records(path, keys=("trend_research", "trends"))]


def load_competitor_posts(path: str | Path | None) -> list[CompetitorPost]:
    return [_competitor_post_from_row(row) for row in _load_records(path, keys=("competitor_posts", "posts"))]


def load_posts_csv(path: str | Path) -> list[ApiPost]:
    return load_api_posts(path)


def load_reference_posts_csv(path: str | Path | None) -> list[CompetitorPost]:
    return load_competitor_posts(path)


def load_trends(path: str | Path) -> list[TrendResearch]:
    return load_trend_research(path)


def load_competitors(path: str | Path | None) -> list[dict[str, Any]]:
    return _load_records(path, keys=("competitors",))


def _load_records(path: str | Path | None, keys: tuple[str, ...]) -> list[dict[str, Any]]:
    if not path:
        return []
    data_path = Path(path)
    if not data_path.exists():
        return []
    if data_path.suffix.lower() == ".csv":
        with data_path.open("r", encoding="utf-8-sig", newline="") as file:
            return [dict(row) for row in csv.DictReader(file)]
    data = _load_json(data_path)
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in keys:
            value = data.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        if any(key in data for key in ("video_id", "id", "title")):
            return [data]
    return []


def _load_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as file:
        return json.load(file)


def _get(row: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in row and row.get(key) not in (None, ""):
            return row.get(key)
    return None


def _api_post_from_row(row: dict[str, Any]) -> ApiPost:
    create_time = _get(row, "create_time")
    posted_at = _get(row, "posted_at")
    if not posted_at and _get(row, "date"):
        posted_at = f"{_get(row, 'date')} {_get(row, 'time') or '00:00'}"
    if not posted_at and create_time:
        parsed = parse_datetime(create_time)
        posted_at = parsed.isoformat() if parsed else ""
    title = str(_get(row, "title", "動画タイトルまたは概要", "video_title") or "")
    description = str(_get(row, "video_description", "description", "caption") or "")
    hashtags = split_tags(_get(row, "hashtags", "使用したハッシュタグ"))
    if not hashtags:
        hashtags = extract_hashtags(f"{title} {description}")
    return ApiPost(
        video_id=str(_get(row, "video_id", "id") or ""),
        create_time=str(create_time or ""),
        posted_at=str(posted_at or ""),
        share_url=str(_get(row, "share_url", "url", "動画URL") or ""),
        title=title or description[:80] or "無題",
        video_description=description,
        duration=parse_float(_get(row, "duration", "duration_sec", "動画尺")),
        view_count=parse_int(_get(row, "view_count", "views", "再生数")),
        like_count=parse_int(_get(row, "like_count", "likes", "いいね数")),
        comment_count=parse_int(_get(row, "comment_count", "comments", "コメント数")),
        share_count=parse_int(_get(row, "share_count", "shares", "シェア数")),
        cover_image_url=str(_get(row, "cover_image_url") or ""),
        embed_link=str(_get(row, "embed_link") or ""),
        hashtags=hashtags,
        music_id=str(_get(row, "music_id", "sound", "使用した音源") or ""),
        source=str(_get(row, "source") or "api"),
    )


def _creative_note_from_row(row: dict[str, Any]) -> CreativeNote:
    return CreativeNote(
        video_id=str(_get(row, "video_id", "id") or ""),
        account_strategy_category=str(_get(row, "account_strategy_category") or ""),
        content_category=str(_get(row, "content_category") or ""),
        is_beauty_core=parse_bool(_get(row, "is_beauty_core")),
        is_pr=parse_bool(_get(row, "is_pr")),
        product_brand=str(_get(row, "product_brand") or ""),
        product_name=str(_get(row, "product_name") or ""),
        product_type=str(_get(row, "product_type") or ""),
        hook_text=str(_get(row, "hook_text") or ""),
        hook_type=str(_get(row, "hook_type") or ""),
        first_3sec_summary=str(_get(row, "first_3sec_summary") or ""),
        video_structure=str(_get(row, "video_structure") or ""),
        cta_type=str(_get(row, "cta_type") or ""),
        cta_text=str(_get(row, "cta_text") or ""),
        face_visible=parse_bool(_get(row, "face_visible")),
        voiceover=parse_bool(_get(row, "voiceover")),
        text_density=str(_get(row, "text_density") or ""),
        cut_count=parse_int(_get(row, "cut_count")),
        before_after=parse_bool(_get(row, "before_after")),
        review_type=str(_get(row, "review_type") or ""),
        target_viewer=str(_get(row, "target_viewer") or ""),
        viewer_pain=str(_get(row, "viewer_pain") or ""),
        save_reason=str(_get(row, "save_reason") or ""),
        comment_prompt=str(_get(row, "comment_prompt") or ""),
        creator_note=str(_get(row, "creator_note") or ""),
    )


def _trend_from_row(row: dict[str, Any]) -> TrendResearch:
    return TrendResearch(
        trend_date=str(_get(row, "trend_date") or ""),
        source=str(_get(row, "source") or ""),
        region=str(_get(row, "region") or ""),
        industry=str(_get(row, "industry") or ""),
        trend_type=str(_get(row, "trend_type") or ""),
        trend_name=str(_get(row, "trend_name") or ""),
        example_url=str(_get(row, "example_url") or ""),
        observed_hook=str(_get(row, "observed_hook") or ""),
        observed_structure=str(_get(row, "observed_structure") or ""),
        observed_cta=str(_get(row, "observed_cta") or ""),
        observed_duration=str(_get(row, "observed_duration") or ""),
        observed_text_style=str(_get(row, "observed_text_style") or ""),
        applicability_to_account=str(_get(row, "applicability_to_account") or ""),
        should_use=parse_bool(_get(row, "should_use")),
        reason=str(_get(row, "reason") or ""),
        adaptation_idea=str(_get(row, "adaptation_idea") or ""),
    )


def _competitor_post_from_row(row: dict[str, Any]) -> CompetitorPost:
    return CompetitorPost(
        competitor_account=str(_get(row, "competitor_account", "account_name", "reference_account") or ""),
        account_url=str(_get(row, "account_url", "account_profile_url") or ""),
        post_url=str(_get(row, "post_url", "url") or ""),
        content_category=str(_get(row, "content_category", "genre") or ""),
        view_count=parse_int(_get(row, "view_count", "views")),
        like_count=parse_int(_get(row, "like_count", "likes")),
        comment_count=parse_int(_get(row, "comment_count", "comments")),
        share_count=parse_int(_get(row, "share_count", "shares")),
        duration=parse_float(_get(row, "duration", "duration_sec")),
        hook_text=str(_get(row, "hook_text", "hook") or ""),
        hook_type=str(_get(row, "hook_type") or ""),
        video_structure=str(_get(row, "video_structure", "structure") or ""),
        cta_type=str(_get(row, "cta_type") or ""),
        text_density=str(_get(row, "text_density") or ""),
        observed_strength=str(_get(row, "observed_strength", "winning_video_features") or ""),
        should_adapt=parse_bool(_get(row, "should_adapt")),
        adaptation_target=str(_get(row, "adaptation_target") or ""),
        notes=str(_get(row, "notes") or ""),
    )
