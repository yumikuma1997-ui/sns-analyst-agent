from __future__ import annotations

import csv
import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
USER_INFO_URL = "https://open.tiktokapis.com/v2/user/info/"
VIDEO_LIST_URL = "https://open.tiktokapis.com/v2/video/list/"

DEFAULT_SCOPES = ["user.info.basic", "video.list"]
DEFAULT_USER_FIELDS = [
    "open_id",
    "union_id",
    "avatar_url",
    "display_name",
    "bio_description",
    "profile_deep_link",
    "username",
    "follower_count",
    "following_count",
    "likes_count",
    "video_count",
]
DEFAULT_VIDEO_FIELDS = [
    "id",
    "title",
    "video_description",
    "create_time",
    "duration",
    "cover_image_url",
    "share_url",
    "embed_link",
    "like_count",
    "comment_count",
    "share_count",
    "view_count",
]
NORMALIZED_VIDEO_FIELDS = [
    "video_id",
    "create_time",
    "date",
    "day_of_week",
    "time",
    "title",
    "url",
    "genre",
    "sound",
    "hashtags",
    "hook",
    "duration_sec",
    "structure",
    "has_cta",
    "views",
    "likes",
    "comments",
    "saves",
    "shares",
    "profile_visits",
    "follow_gains",
    "completion_rate",
    "avg_watch_time_sec",
    "impressions",
    "traffic_sources",
    "notes",
    "cover_image_url",
    "embed_link",
    "video_description",
]


@dataclass
class OAuthConfig:
    client_key: str
    redirect_uri: str
    scopes: list[str]
    state: str | None = None
    code_challenge: str | None = None
    code_challenge_method: str = "S256"


def build_authorization_url(config: OAuthConfig) -> str:
    params = {
        "client_key": config.client_key,
        "scope": ",".join(config.scopes),
        "response_type": "code",
        "redirect_uri": config.redirect_uri,
    }
    if config.state:
        params["state"] = config.state
    if config.code_challenge:
        params["code_challenge"] = config.code_challenge
        params["code_challenge_method"] = config.code_challenge_method
    return f"{AUTH_URL}?{urllib.parse.urlencode(params)}"


def load_token_file(path: str | Path) -> dict[str, Any]:
    token_path = Path(path)
    if not token_path.exists():
        raise FileNotFoundError(f"Token file not found: {token_path}")
    return json.loads(token_path.read_text(encoding="utf-8"))


def save_token_file(path: str | Path, token_data: dict[str, Any]) -> None:
    token_path = Path(path)
    token_path.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(token_data)
    payload["saved_at"] = datetime.now(timezone.utc).isoformat()
    token_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def exchange_code_for_token(
    client_key: str,
    client_secret: str,
    code: str,
    redirect_uri: str,
    code_verifier: str | None = None,
) -> dict[str, Any]:
    payload = {
        "client_key": client_key,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
    }
    if code_verifier:
        payload["code_verifier"] = code_verifier
    return _post_form(TOKEN_URL, payload)


def refresh_access_token(client_key: str, client_secret: str, refresh_token: str) -> dict[str, Any]:
    return _post_form(
        TOKEN_URL,
        {
            "client_key": client_key,
            "client_secret": client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
    )


def fetch_user_info(access_token: str, fields: list[str] | None = None) -> dict[str, Any]:
    query = urllib.parse.urlencode({"fields": ",".join(fields or DEFAULT_USER_FIELDS)})
    return _request_json(
        f"{USER_INFO_URL}?{query}",
        method="GET",
        headers={"Authorization": f"Bearer {access_token}"},
    )


def fetch_video_list(
    access_token: str,
    fields: list[str] | None = None,
    max_count: int = 20,
    max_pages: int | None = None,
    cursor: int | None = None,
) -> dict[str, Any]:
    requested_fields = fields or DEFAULT_VIDEO_FIELDS
    pages = []
    videos = []
    page_count = 0
    next_cursor = cursor
    has_more = True

    while has_more:
        if max_pages is not None and page_count >= max_pages:
            break
        body: dict[str, Any] = {"max_count": max(1, min(max_count, 20))}
        if next_cursor is not None:
            body["cursor"] = next_cursor
        query = urllib.parse.urlencode({"fields": ",".join(requested_fields)})
        response = _request_json(
            f"{VIDEO_LIST_URL}?{query}",
            method="POST",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            body=json.dumps(body).encode("utf-8"),
        )
        pages.append(response)
        data = response.get("data", {})
        page_videos = data.get("videos", [])
        if isinstance(page_videos, list):
            videos.extend(page_videos)
        has_more = bool(data.get("has_more"))
        next_cursor = data.get("cursor")
        page_count += 1

    return {
        "source": "tiktok_display_api_video_list",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "fields": requested_fields,
        "pages": pages,
        "videos": videos,
    }


def write_json(path: str | Path, data: dict[str, Any]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def normalize_video_list_raw(raw_data: dict[str, Any]) -> list[dict[str, Any]]:
    videos = _extract_videos(raw_data)
    return [_normalize_video(video) for video in videos]


def write_normalized_videos_csv(path: str | Path, rows: list[dict[str, Any]]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=NORMALIZED_VIDEO_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def normalize_video_list_file(input_path: str | Path, output_path: str | Path) -> list[dict[str, Any]]:
    raw_data = json.loads(Path(input_path).read_text(encoding="utf-8"))
    rows = normalize_video_list_raw(raw_data)
    write_normalized_videos_csv(output_path, rows)
    return rows


def parse_fields(value: str | None, default: list[str]) -> list[str]:
    if not value:
        return default
    return [field.strip() for field in value.split(",") if field.strip()]


def _extract_videos(raw_data: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(raw_data.get("videos"), list):
        return raw_data["videos"]
    data = raw_data.get("data", {})
    if isinstance(data, dict) and isinstance(data.get("videos"), list):
        return data["videos"]
    videos = []
    for page in raw_data.get("pages", []):
        page_data = page.get("data", {}) if isinstance(page, dict) else {}
        page_videos = page_data.get("videos", [])
        if isinstance(page_videos, list):
            videos.extend(page_videos)
    return videos


def _normalize_video(video: dict[str, Any]) -> dict[str, Any]:
    created_at = _datetime_from_unix_seconds(video.get("create_time"))
    description = str(video.get("video_description") or "")
    title = str(video.get("title") or description[:80] or "無題")
    return {
        "video_id": video.get("id", ""),
        "create_time": video.get("create_time", ""),
        "date": created_at.strftime("%Y-%m-%d") if created_at else "",
        "day_of_week": created_at.strftime("%a") if created_at else "",
        "time": created_at.strftime("%H:%M") if created_at else "",
        "title": title,
        "url": video.get("share_url", ""),
        "genre": "",
        "sound": "",
        "hashtags": " ".join(_extract_hashtags(description)),
        "hook": "",
        "duration_sec": video.get("duration", ""),
        "structure": "",
        "has_cta": "",
        "views": video.get("view_count", ""),
        "likes": video.get("like_count", ""),
        "comments": video.get("comment_count", ""),
        "saves": "",
        "shares": video.get("share_count", ""),
        "profile_visits": "",
        "follow_gains": "",
        "completion_rate": "",
        "avg_watch_time_sec": "",
        "impressions": "",
        "traffic_sources": "",
        "notes": "TikTok公式Display API取得。Studio系詳細指標は手動補完。",
        "cover_image_url": video.get("cover_image_url", ""),
        "embed_link": video.get("embed_link", ""),
        "video_description": description,
    }


def _extract_hashtags(text: str) -> list[str]:
    tags = []
    for part in text.replace("\n", " ").split():
        if part.startswith("#") and len(part) > 1:
            tags.append(part.strip(".,;:!?)）]】"))
    return tags


def _datetime_from_unix_seconds(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


def _post_form(url: str, payload: dict[str, str]) -> dict[str, Any]:
    return _request_json(
        url,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded", "Cache-Control": "no-cache"},
        body=urllib.parse.urlencode(payload).encode("utf-8"),
    )


def _request_json(
    url: str,
    method: str,
    headers: dict[str, str],
    body: bytes | None = None,
) -> dict[str, Any]:
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            response_body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        if exc.code == 429:
            raise RuntimeError(f"TikTok API rate limit exceeded: {error_body[:500]}") from exc
        raise RuntimeError(f"TikTok API HTTP {exc.code}: {error_body[:500]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"TikTok API request failed: {exc}") from exc
    return json.loads(response_body)
