from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from utils import parse_bool, parse_float, parse_int, parse_rate


@dataclass
class AccountProfile:
    account_name: str = "データ不足"
    genre: str = "データ不足"
    target_audience: str = "データ不足"
    operation_goal: str = "データ不足"
    current_followers: int | None = None
    target_followers: int | None = None
    target_state: str = "データ不足"
    postable_frequency: str = "データ不足"
    face_reveal: bool | None = None
    voice_available: bool | None = None
    shooting_environment: str = "データ不足"
    available_assets: str = "データ不足"
    avoid_expressions: str = "データ不足"
    reference_accounts: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AccountProfile":
        return cls(
            account_name=str(data.get("account_name") or data.get("アカウント名") or "データ不足"),
            genre=str(data.get("genre") or data.get("ジャンル") or "データ不足"),
            target_audience=str(data.get("target_audience") or data.get("想定ターゲット") or "データ不足"),
            operation_goal=str(data.get("operation_goal") or data.get("運用目的") or "データ不足"),
            current_followers=parse_int(data.get("current_followers") or data.get("現在のフォロワー数")),
            target_followers=parse_int(data.get("target_followers") or data.get("目標フォロワー数")),
            target_state=str(data.get("target_state") or data.get("目標とする状態") or "データ不足"),
            postable_frequency=str(data.get("postable_frequency") or data.get("投稿可能頻度") or "データ不足"),
            face_reveal=parse_bool(data.get("face_reveal", data.get("顔出し可否"))),
            voice_available=parse_bool(data.get("voice_available", data.get("声出し可否"))),
            shooting_environment=str(data.get("shooting_environment") or data.get("撮影可能な環境") or "データ不足"),
            available_assets=str(data.get("available_assets") or data.get("使える素材") or "データ不足"),
            avoid_expressions=str(data.get("avoid_expressions") or data.get("避けたい表現") or "データ不足"),
            reference_accounts=_string_list(data.get("reference_accounts") or data.get("参考にしたいアカウント")),
        )


@dataclass
class ApiPost:
    video_id: str = ""
    create_time: str = ""
    posted_at: str = ""
    share_url: str = ""
    title: str = ""
    video_description: str = ""
    duration: float | None = None
    view_count: int | None = None
    like_count: int | None = None
    comment_count: int | None = None
    share_count: int | None = None
    cover_image_url: str = ""
    embed_link: str = ""
    hashtags: list[str] = field(default_factory=list)
    music_id: str = ""
    source: str = "api"


@dataclass
class ManualInsight:
    video_id: str = ""
    saves: int | None = None
    profile_views: int | None = None
    follows_from_video: int | None = None
    average_watch_time: float | None = None
    completion_rate: float | None = None
    traffic_source_for_you: float | None = None
    traffic_source_profile: float | None = None
    traffic_source_following: float | None = None
    traffic_source_search: float | None = None
    audience_gender: str = ""
    audience_age_range: str = ""
    audience_region: str = ""
    measured_after_hours: float | None = None
    insight_note: str = ""


@dataclass
class CreativeNote:
    video_id: str = ""
    account_strategy_category: str = ""
    content_category: str = ""
    is_beauty_core: bool | None = None
    is_pr: bool | None = None
    product_brand: str = ""
    product_name: str = ""
    product_type: str = ""
    hook_text: str = ""
    hook_type: str = ""
    first_3sec_summary: str = ""
    video_structure: str = ""
    cta_type: str = ""
    cta_text: str = ""
    face_visible: bool | None = None
    voiceover: bool | None = None
    text_density: str = ""
    cut_count: int | None = None
    before_after: bool | None = None
    review_type: str = ""
    target_viewer: str = ""
    viewer_pain: str = ""
    save_reason: str = ""
    comment_prompt: str = ""
    creator_note: str = ""


@dataclass
class TrendResearch:
    trend_date: str = ""
    source: str = ""
    region: str = ""
    industry: str = ""
    trend_type: str = ""
    trend_name: str = ""
    example_url: str = ""
    observed_hook: str = ""
    observed_structure: str = ""
    observed_cta: str = ""
    observed_duration: str = ""
    observed_text_style: str = ""
    applicability_to_account: str = ""
    should_use: bool | None = None
    reason: str = ""
    adaptation_idea: str = ""


@dataclass
class CompetitorPost:
    competitor_account: str = ""
    account_url: str = ""
    post_url: str = ""
    content_category: str = ""
    view_count: int | None = None
    like_count: int | None = None
    comment_count: int | None = None
    share_count: int | None = None
    duration: float | None = None
    hook_text: str = ""
    hook_type: str = ""
    video_structure: str = ""
    cta_type: str = ""
    text_density: str = ""
    observed_strength: str = ""
    should_adapt: bool | None = None
    adaptation_target: str = ""
    notes: str = ""


@dataclass
class Post:
    date: str = ""
    day_of_week: str = ""
    time: str = ""
    title: str = "無題"
    url: str = ""
    genre: str = ""
    sound: str = ""
    hashtags: list[str] = field(default_factory=list)
    hook: str = ""
    duration_sec: float | None = None
    structure: str = ""
    has_cta: bool | None = None
    views: int | None = None
    likes: int | None = None
    comments: int | None = None
    saves: int | None = None
    shares: int | None = None
    profile_visits: int | None = None
    follow_gains: int | None = None
    completion_rate: float | None = None
    avg_watch_time_sec: float | None = None
    impressions: int | None = None
    traffic_sources: str = ""
    notes: str = ""


@dataclass
class ReferencePost(Post):
    account_name: str = "データ不足"
    account_url: str = ""
    account_role: str = "competitor"


@dataclass
class PostMetric:
    post: Post
    like_rate: float | None
    comment_rate: float | None
    save_rate: float | None
    share_rate: float | None
    follow_conversion_rate: float | None
    profile_visit_rate: float | None
    avg_retention_rate: float | None


def _string_list(value: Any) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [part.strip() for part in str(value).replace("、", ",").split(",") if part.strip()]


def manual_insight_from_dict(data: dict[str, Any]) -> ManualInsight:
    return ManualInsight(
        video_id=str(data.get("video_id") or data.get("id") or ""),
        saves=parse_int(data.get("saves")),
        profile_views=parse_int(data.get("profile_views")),
        follows_from_video=parse_int(data.get("follows_from_video")),
        average_watch_time=parse_float(data.get("average_watch_time")),
        completion_rate=parse_rate(data.get("completion_rate")),
        traffic_source_for_you=parse_rate(data.get("traffic_source_for_you")),
        traffic_source_profile=parse_rate(data.get("traffic_source_profile")),
        traffic_source_following=parse_rate(data.get("traffic_source_following")),
        traffic_source_search=parse_rate(data.get("traffic_source_search")),
        audience_gender=str(data.get("audience_gender") or ""),
        audience_age_range=str(data.get("audience_age_range") or ""),
        audience_region=str(data.get("audience_region") or ""),
        measured_after_hours=parse_float(data.get("measured_after_hours")),
        insight_note=str(data.get("insight_note") or ""),
    )
