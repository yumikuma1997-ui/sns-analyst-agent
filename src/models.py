from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


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
            current_followers=_optional_int(data.get("current_followers") or data.get("現在のフォロワー数")),
            target_followers=_optional_int(data.get("target_followers") or data.get("目標フォロワー数")),
            target_state=str(data.get("target_state") or data.get("目標とする状態") or "データ不足"),
            postable_frequency=str(data.get("postable_frequency") or data.get("投稿可能頻度") or "データ不足"),
            face_reveal=_optional_bool(data.get("face_reveal", data.get("顔出し可否"))),
            voice_available=_optional_bool(data.get("voice_available", data.get("声出し可否"))),
            shooting_environment=str(data.get("shooting_environment") or data.get("撮影可能な環境") or "データ不足"),
            available_assets=str(data.get("available_assets") or data.get("使える素材") or "データ不足"),
            avoid_expressions=str(data.get("avoid_expressions") or data.get("避けたい表現") or "データ不足"),
            reference_accounts=_string_list(data.get("reference_accounts") or data.get("参考にしたいアカウント")),
        )


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


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(str(value).replace(",", "")))
    except ValueError:
        return None


def _optional_bool(value: Any) -> bool | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"true", "yes", "y", "1", "可", "あり", "有", "ok"}:
        return True
    if normalized in {"false", "no", "n", "0", "不可", "なし", "無", "ng"}:
        return False
    return None


def _string_list(value: Any) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [part.strip() for part in str(value).replace("、", ",").split(",") if part.strip()]
