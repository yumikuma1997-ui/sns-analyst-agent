from __future__ import annotations

from collections import Counter
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from typing import Any

from classifiers import (
    classify_duration_bucket,
    classify_post_time_bucket,
    classify_strategy_category_detail,
    detect_outlier_viral_posts,
    detect_pr_status,
    hashtag_groups,
)
from confidence import calculate_api_aggregation_confidence, calculate_confidence_level, calculate_strategy_confidence
from metrics import calculate_api_metrics, safe_divide, summarize_api_posts
from models import AccountProfile, ApiPost, CompetitorPost, CreativeNote, ManualInsight, TrendResearch
from utils import DATA_INSUFFICIENT, format_number, parse_datetime


PR_STATUSES = {"明示PR", "PR疑い"}
NON_PR_STATUS = "非PR"

MANUAL_REQUIRED_METRICS = [
    ("保存数", "manual_insights.csv", "保存される理由がある投稿の型を比較できる"),
    ("保存率", "manual_insights.csv", "保存価値の強いテーマ・構成を検証できる"),
    ("プロフィールアクセス数", "manual_insights.csv", "動画からプロフィールへの導線を評価できる"),
    ("投稿単位のフォロー増加数", "manual_insights.csv", "フォローに繋がる投稿特徴を見られる"),
    ("フォロー転換率", "manual_insights.csv", "再生からフォローへの効率を比較できる"),
    ("完視聴率", "manual_insights.csv", "尺・構成ごとの離脱を検証できる"),
    ("平均視聴時間", "manual_insights.csv", "冒頭と構成の引き留め力を見られる"),
    ("視聴維持率", "manual_insights.csv", "動画尺に対する視聴深度を比較できる"),
    ("流入元", "manual_insights.csv", "おすすめ・検索・プロフィールなど流入別成果を見られる"),
    ("視聴者属性", "manual_insights.csv", "想定ターゲットとの一致を確認できる"),
    ("冒頭3秒", "creative_notes.csv", "フック構造と成果の関係を検証できる"),
    ("動画構成", "creative_notes.csv", "伸びた構成・弱い構成を比較できる"),
    ("CTA", "creative_notes.csv", "コメント・保存・フォロー誘導の効果を検証できる"),
    ("顔出し有無", "creative_notes.csv", "顔出しと反応の関係を見られる"),
    ("声出し有無", "creative_notes.csv", "声出しと視聴維持の関係を見られる"),
    ("PR有無", "creative_notes.csv", "PR/非PRを正確に分けて比較できる"),
]

CREATIVE_MINIMUM_FIELDS = [
    "video_id",
    "account_strategy_category",
    "content_category",
    "is_pr",
    "hook_text",
    "hook_type",
    "first_3sec_summary",
    "video_structure",
    "cta_type",
    "text_density",
    "save_reason",
    "comment_prompt",
]

MANUAL_INSIGHT_MINIMUM_FIELDS = [
    "video_id",
    "saves",
    "profile_views",
    "follows_from_video",
    "average_watch_time",
    "completion_rate",
    "traffic_source_for_you",
    "traffic_source_search",
    "measured_after_hours",
]


def analyze(
    account: AccountProfile,
    api_posts: list[ApiPost],
    manual_insights: list[ManualInsight] | None = None,
    creative_notes: list[CreativeNote] | None = None,
    trend_research: list[TrendResearch] | None = None,
    competitor_posts: list[CompetitorPost] | None = None,
) -> dict[str, Any]:
    manual_insights = manual_insights or []
    creative_notes = creative_notes or []
    trend_research = trend_research or []
    competitor_posts = competitor_posts or []

    manual_by_id = {item.video_id: item for item in manual_insights if item.video_id}
    creative_by_id = {item.video_id: item for item in creative_notes if item.video_id}
    rows = [_build_row(post, manual_by_id.get(post.video_id), creative_by_id.get(post.video_id)) for post in api_posts]

    overall_summary = _scope_summary(rows)
    viral_posts = detect_outlier_viral_posts(rows, overall_summary["median_views"])
    viral_ids = {row["video_id"] for row in viral_posts}
    buzz_excluded = _scope_summary([row for row in rows if row["video_id"] not in viral_ids])
    creative_coverage = _coverage(len(rows), len([row for row in rows if row.get("creative")]))
    manual_coverage = _coverage(len(rows), len([row for row in rows if row.get("manual")]))
    has_view_metrics = any(row.get("view_count") is not None for row in rows)
    api_confidence = calculate_api_aggregation_confidence(len(rows), has_view_metrics)
    strategy_confidence = calculate_strategy_confidence(
        post_count=len(rows),
        manual_count=len(manual_insights),
        creative_count=len(creative_notes),
        trend_count=len(trend_research),
        competitor_count=len(competitor_posts),
        creative_coverage=creative_coverage,
    )
    priority_targets = _priority_input_targets(rows, viral_ids)

    analysis = {
        "account": asdict(account),
        "data_scope": {
            "api_post_count": len(api_posts),
            "manual_insight_count": len(manual_insights),
            "creative_note_count": len(creative_notes),
            "trend_research_count": len(trend_research),
            "competitor_post_count": len(competitor_posts),
            "api_fields": [
                "id",
                "create_time",
                "share_url",
                "video_description",
                "title",
                "duration",
                "like_count",
                "comment_count",
                "share_count",
                "view_count",
                "cover_image_url",
                "embed_link",
            ],
            "not_available_via_basic_api": [item[0] for item in MANUAL_REQUIRED_METRICS],
            "api_aggregation_confidence": api_confidence,
            "strategy_recommendation_confidence": strategy_confidence,
            "creative_coverage": creative_coverage,
            "manual_coverage": manual_coverage,
        },
        "rows": rows,
        "summaries": {
            "all": overall_summary,
            "beauty_core": _scope_summary([row for row in rows if row["strategy_category"] == "beauty_core"]),
            "beauty_with_adjacent": _scope_summary(
                [row for row in rows if row["strategy_category"] in {"beauty_core", "beauty_adjacent"}]
            ),
            "pr": _scope_summary([row for row in rows if row["pr_status"] in PR_STATUSES]),
            "non_pr": _scope_summary([row for row in rows if row["pr_status"] == NON_PR_STATUS]),
            "unrelated": _scope_summary([row for row in rows if row["strategy_category"] in {"lifestyle", "personal", "unrelated"}]),
            "buzz_excluded": buzz_excluded,
        },
        "missing_data": _missing_data_table(manual_insights, creative_notes, rows),
        "viral": _analyze_viral(rows, viral_posts),
        "beauty_analysis": _analyze_beauty(rows),
        "pr_analysis": _analyze_pr(rows, viral_ids),
        "habits": _analyze_habits(rows),
        "hashtags": _analyze_hashtags(rows, overall_summary["median_views"]),
        "creative_analysis": _analyze_creative(rows, creative_by_id),
        "trend_analysis": _analyze_trends(trend_research),
        "competitor_analysis": _analyze_competitors(competitor_posts),
        "priority_input_targets": priority_targets,
        "creative_minimum_fields": CREATIVE_MINIMUM_FIELDS,
        "manual_insight_minimum_fields": MANUAL_INSIGHT_MINIMUM_FIELDS,
        "video_ideas": _generate_video_ideas(rows, trend_research, competitor_posts),
        "operation_plan": _generate_operation_plan(),
        "kpi_design": _generate_kpi_design(),
        "hypotheses": _generate_hypotheses(),
        "backlog": _generate_backlog(),
    }
    analysis["executive_summary"] = _generate_executive_summary(analysis)
    return analysis


def _build_row(post: ApiPost, manual: ManualInsight | None, creative: CreativeNote | None) -> dict[str, Any]:
    metrics = calculate_api_metrics(post)
    posted_dt = parse_datetime(post.posted_at or post.create_time)
    strategy = classify_strategy_category_detail(post, creative)
    pr_status = detect_pr_status(post, creative)
    return {
        "video_id": post.video_id,
        "posted_at": post.posted_at,
        "posted_dt": posted_dt,
        "day_of_week": posted_dt.strftime("%a") if posted_dt else DATA_INSUFFICIENT,
        "time_bucket": classify_post_time_bucket(post.posted_at),
        "title": post.title,
        "video_description": post.video_description,
        "share_url": post.share_url,
        "duration": post.duration,
        "duration_bucket": classify_duration_bucket(post.duration),
        "view_count": metrics["view_count"],
        "like_count": metrics["like_count"],
        "comment_count": metrics["comment_count"],
        "share_count": metrics["share_count"],
        "like_rate": metrics["like_rate"],
        "comment_rate": metrics["comment_rate"],
        "share_rate": metrics["share_rate"],
        "hashtags": post.hashtags,
        "cover_image_url": post.cover_image_url,
        "embed_link": post.embed_link,
        "source": post.source,
        "manual": manual,
        "creative": creative,
        "strategy_category": strategy["category"],
        "strategy_category_source": strategy["source"],
        "strategy_category_reasons": strategy["reasons"],
        "beauty_core_confidence": strategy["confidence"],
        "pr_status": pr_status,
        "save_rate": safe_divide(manual.saves, post.view_count) if manual else None,
        "profile_visit_rate": safe_divide(manual.profile_views, post.view_count) if manual else None,
        "follow_conversion_rate": safe_divide(manual.follows_from_video, post.view_count) if manual else None,
        "avg_retention_rate": safe_divide(manual.average_watch_time, post.duration) if manual else None,
        "completion_rate": manual.completion_rate if manual else None,
        "hook_text": creative.hook_text if creative else "",
        "hook_type": creative.hook_type if creative else "",
        "video_structure": creative.video_structure if creative else "",
        "cta_type": creative.cta_type if creative else "",
        "text_density": creative.text_density if creative else "",
        "content_category": creative.content_category if creative else "",
    }


def _scope_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    summary = summarize_api_posts(rows)
    summary["duration_buckets"] = Counter(row["duration_bucket"] for row in rows).most_common()
    summary["day_counts"] = Counter(row["day_of_week"] for row in rows if row["day_of_week"]).most_common()
    summary["time_buckets"] = Counter(row["time_bucket"] for row in rows if row["time_bucket"]).most_common()
    summary["confidence"] = calculate_confidence_level(
        len(rows),
        has_api_metrics=any(row.get("view_count") is not None for row in rows),
        qualitative_coverage=_coverage(len(rows), sum(1 for row in rows if row.get("creative"))),
        manual_coverage=_coverage(len(rows), sum(1 for row in rows if row.get("manual"))),
    )
    return summary


def _missing_data_table(
    manual_insights: list[ManualInsight],
    creative_notes: list[CreativeNote],
    rows: list[dict[str, Any]],
) -> list[dict[str, str]]:
    values = {
        "保存数": any(item.saves is not None for item in manual_insights),
        "保存率": any(item.saves is not None for item in manual_insights),
        "プロフィールアクセス数": any(item.profile_views is not None for item in manual_insights),
        "投稿単位のフォロー増加数": any(item.follows_from_video is not None for item in manual_insights),
        "フォロー転換率": any(item.follows_from_video is not None for item in manual_insights),
        "完視聴率": any(item.completion_rate is not None for item in manual_insights),
        "平均視聴時間": any(item.average_watch_time is not None for item in manual_insights),
        "視聴維持率": any(item.average_watch_time is not None for item in manual_insights),
        "流入元": any(
            any(
                value is not None
                for value in (
                    item.traffic_source_for_you,
                    item.traffic_source_profile,
                    item.traffic_source_following,
                    item.traffic_source_search,
                )
            )
            for item in manual_insights
        ),
        "視聴者属性": any(item.audience_gender or item.audience_age_range or item.audience_region for item in manual_insights),
        "冒頭3秒": any(item.first_3sec_summary or item.hook_text for item in creative_notes),
        "動画構成": any(item.video_structure for item in creative_notes),
        "CTA": any(item.cta_type or item.cta_text for item in creative_notes),
        "顔出し有無": any(item.face_visible is not None for item in creative_notes),
        "声出し有無": any(item.voiceover is not None for item in creative_notes),
        "PR有無": any(item.is_pr is not None for item in creative_notes),
    }
    table = []
    for metric, input_file, benefit in MANUAL_REQUIRED_METRICS:
        has_value = values.get(metric, False)
        if has_value:
            status = "入力あり"
            reason = "手入力データがあります。ただし入力済み投稿だけを対象にした分析です。"
        elif metric == "PR有無" and rows:
            status = "自動推定のみ"
            reason = "caption内の#PR等で候補判定はできますが、確定にはcreative_notes.csvのis_pr入力が必要です。"
        else:
            status = "未入力"
            reason = "TikTok公式の公開動画APIでは通常取得できないため、手入力が必要です。"
        table.append({"metric": metric, "status": status, "reason": reason, "input": input_file, "benefit": benefit})
    return table


def _analyze_viral(rows: list[dict[str, Any]], viral_posts: list[dict[str, Any]]) -> dict[str, Any]:
    repeat_patterns = Counter(
        (row.get("hook_type"), row.get("video_structure"))
        for row in rows
        if row.get("hook_type") or row.get("video_structure")
    )
    reproducible = []
    unjudged_candidates = []
    low_reproducibility = []
    for row in viral_posts:
        creative_ready = bool(row.get("hook_text") or row.get("video_structure"))
        beauty_related = row["strategy_category"] in {"beauty_core", "beauty_adjacent"}
        pattern_count = repeat_patterns[(row.get("hook_type"), row.get("video_structure"))]
        if beauty_related and creative_ready and pattern_count >= 2:
            reproducible.append(row)
        elif beauty_related:
            unjudged_candidates.append(row)
        else:
            low_reproducibility.append(row)
    return {
        "viral_posts": viral_posts,
        "reproducible": reproducible,
        "unjudged_winning_candidates": unjudged_candidates,
        "low_reproducibility": low_reproducibility,
        "confidence": "信頼度B" if viral_posts else "信頼度D",
    }


def _analyze_beauty(rows: list[dict[str, Any]]) -> dict[str, Any]:
    core = [row for row in rows if row["strategy_category"] == "beauty_core"]
    adjacent = [row for row in rows if row["strategy_category"] == "beauty_adjacent"]
    unrelated = [row for row in rows if row["strategy_category"] in {"lifestyle", "personal", "unrelated"}]
    ordered_core = sorted(core, key=lambda row: row.get("view_count") or 0, reverse=True)
    category_evidence = [
        {
            "video_id": row["video_id"],
            "title": row["title"],
            "category": row["strategy_category"],
            "source": row["strategy_category_source"],
            "confidence": row["beauty_core_confidence"],
            "reasons": row["strategy_category_reasons"],
        }
        for row in rows[:20]
    ]
    return {
        "core_count": len(core),
        "adjacent_count": len(adjacent),
        "unrelated_count": len(unrelated),
        "core_summary": _scope_summary(core),
        "top_core": ordered_core[:5],
        "weak_core": list(reversed(ordered_core[-5:])),
        "category_evidence": category_evidence,
        "winning_candidates_unjudged": ordered_core[:5],
        "missing": "creative_notes.csvが不足すると、冒頭3秒・構成・CTAの共通点は判断できません。",
        "confidence": calculate_confidence_level(len(core), True, _coverage(len(core), sum(1 for row in core if row.get("creative")))),
    }


def _analyze_pr(rows: list[dict[str, Any]], viral_ids: set[str]) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    scopes = {
        "全期間": rows,
        "直近30日": [row for row in rows if _is_recent(row, 30, now)],
        "バズ除外": [row for row in rows if row["video_id"] not in viral_ids],
        "beauty_coreのみ": [row for row in rows if row["strategy_category"] == "beauty_core"],
    }
    return {
        "scopes": {label: _pr_scope_summary(scope_rows) for label, scope_rows in scopes.items()},
        "status_counts": Counter(row["pr_status"] for row in rows).most_common(),
        "confidence": "信頼度B" if rows else "信頼度D",
    }


def _pr_scope_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    pr = [row for row in rows if row["pr_status"] in PR_STATUSES]
    non_pr = [row for row in rows if row["pr_status"] == NON_PR_STATUS]
    return {
        "post_count": len(rows),
        "status_counts": Counter(row["pr_status"] for row in rows).most_common(),
        "pr_summary": _scope_summary(pr),
        "non_pr_summary": _scope_summary(non_pr),
    }


def _analyze_habits(rows: list[dict[str, Any]]) -> dict[str, Any]:
    all_summary = _scope_summary(rows)
    return {
        "frequencies": {
            "全期間": _frequency_snapshot(rows),
            "直近30日": _frequency_snapshot(rows, 30),
            "直近90日": _frequency_snapshot(rows, 90),
        },
        "average_post_interval_days": all_summary["average_post_interval_days"],
        "max_post_interval_days": all_summary["max_post_interval_days"],
        "day_counts": all_summary["day_counts"],
        "time_buckets": all_summary["time_buckets"],
        "confidence": all_summary["confidence"],
    }


def _analyze_hashtags(rows: list[dict[str, Any]], median_views: float | None) -> dict[str, Any]:
    groups = hashtag_groups(rows, median_views)
    return {
        "groups": groups,
        "caption_notes": _caption_notes(rows),
        "confidence": "信頼度B" if rows else "信頼度D",
    }


def _analyze_creative(rows: list[dict[str, Any]], creative_by_id: dict[str, CreativeNote]) -> dict[str, Any]:
    if not creative_by_id:
        return {
            "available": False,
            "confidence": "信頼度D",
            "message": "creative_notes.csv が未入力のため、冒頭3秒・構成・CTA・テロップ密度は判断しません。",
            "required_fields": CREATIVE_MINIMUM_FIELDS,
        }
    creative_rows = [row for row in rows if row.get("creative")]
    return {
        "available": True,
        "hook_types": Counter(row["hook_type"] for row in creative_rows if row["hook_type"]).most_common(),
        "structures": Counter(row["video_structure"] for row in creative_rows if row["video_structure"]).most_common(),
        "cta_types": Counter(row["cta_type"] for row in creative_rows if row["cta_type"]).most_common(),
        "text_density": Counter(row["text_density"] for row in creative_rows if row["text_density"]).most_common(),
        "confidence": calculate_confidence_level(len(rows), True, _coverage(len(rows), len(creative_rows))),
    }


def _analyze_trends(trend_research: list[TrendResearch]) -> dict[str, Any]:
    if not trend_research:
        return {
            "available": False,
            "confidence": "信頼度D",
            "message": "trend_research.csv が未入力のため、現在トレンドとの一致度は判断しません。",
            "manual_research_items": [
                "TikTok Creative Centerの美容関連ハッシュタグ",
                "美容・コスメ領域の流行音源",
                "買う前チェック型の冒頭フック",
                "Qoo10メガ割や季節キーワード",
                "テロップ密度と尺の傾向",
            ],
        }
    usable = [item for item in trend_research if item.should_use is True]
    avoid = [item for item in trend_research if item.should_use is False]
    return {"available": True, "usable": usable, "avoid": avoid, "confidence": "信頼度C"}


def _analyze_competitors(competitor_posts: list[CompetitorPost]) -> dict[str, Any]:
    if not competitor_posts:
        return {
            "available": False,
            "confidence": "信頼度D",
            "message": "competitor_posts.csv が未入力のため、参考アカウント分析は実施しません。",
        }
    allowed_targets = {"hook", "structure", "cta", "text_density", "duration", "comment_prompt", "save_prompt"}
    adaptable = [
        item
        for item in competitor_posts
        if item.should_adapt is True and (item.adaptation_target in allowed_targets or not item.adaptation_target)
    ]
    return {
        "available": True,
        "adaptable": adaptable,
        "hook_types": Counter(item.hook_type for item in adaptable if item.hook_type).most_common(),
        "structures": Counter(item.video_structure for item in adaptable if item.video_structure).most_common(),
        "cta_types": Counter(item.cta_type for item in adaptable if item.cta_type).most_common(),
        "durations": Counter(item.duration for item in adaptable if item.duration is not None).most_common(),
        "confidence": "信頼度C" if adaptable else "信頼度D",
        "copy_guardrail": "参考アカウントから取り入れるのは型だけです。テーマ、台本、固有表現、映像構成の丸写しはしません。",
    }


def _priority_input_targets(rows: list[dict[str, Any]], viral_ids: set[str]) -> list[dict[str, Any]]:
    scored = []
    for row in rows:
        missing = []
        if not row.get("manual"):
            missing.append("manual_insights")
        if not row.get("creative"):
            missing.append("creative_notes")
        if not missing:
            continue
        score = (row.get("view_count") or 0) / 1000
        if row["video_id"] in viral_ids:
            score += 100
        if row["strategy_category"] == "beauty_core":
            score += 30
        if row["pr_status"] in PR_STATUSES:
            score += 15
        if row.get("posted_dt") and _is_recent(row, 30, datetime.now(timezone.utc)):
            score += 10
        scored.append((score, row, missing))
    scored.sort(key=lambda item: item[0], reverse=True)
    targets = []
    for _, row, missing in scored[:10]:
        targets.append(
            {
                "video_id": row["video_id"],
                "title": row["title"],
                "posted_at": row["posted_at"],
                "view_count": row["view_count"],
                "category": row["strategy_category"],
                "pr_status": row["pr_status"],
                "missing": missing,
                "reason": "高再生・美容本流・PR候補・直近投稿のいずれかに該当し、追加入力の分析効果が高いため",
            }
        )
    return targets


def _generate_video_ideas(
    rows: list[dict[str, Any]],
    trend_research: list[TrendResearch],
    competitor_posts: list[CompetitorPost],
) -> list[dict[str, Any]]:
    top_beauty = [
        row
        for row in sorted(rows, key=lambda item: item.get("view_count") or 0, reverse=True)
        if row["strategy_category"] in {"beauty_core", "beauty_adjacent"}
    ][:5]
    evidence_rows = top_beauty or sorted(rows, key=lambda item: item.get("view_count") or 0, reverse=True)[:3]
    trend_names = [item.trend_name for item in trend_research if item.should_use is True]
    competitor_patterns = [
        item.hook_type or item.video_structure or item.cta_type
        for item in competitor_posts
        if item.should_adapt is True and item.adaptation_target in {"hook", "structure", "cta", "text_density", "duration"}
    ]
    templates = [
        {
            "title": "そのリップ買う前に見るべき3つのポイント",
            "validation_type": "買う前チェック",
            "goal": "保存される購入前チェック型を検証",
            "target": "リップ購入で色選びや乾燥が不安な人",
            "hook": "そのリップ、買う前にこの3つだけ見てください",
            "structure": "NG例提示 -> チェック3点 -> 向いている人 -> 保存CTA",
            "duration": "20-30秒",
            "hypothesis": "損失回避型フックは保存率を押し上げる可能性がある",
            "seasonality": "季節性なし",
        },
        {
            "title": "Qoo10メガ割で失敗しにくい韓国コスメの選び方",
            "validation_type": "購入イベント",
            "goal": "購買タイミングに合わせた比較型を検証",
            "target": "メガ割で買うものを迷っている人",
            "hook": "メガ割で失敗したくない人は、この順番で見て",
            "structure": "選び方基準 -> 価格以外の確認点 -> 肌質別注意 -> コメント誘導",
            "duration": "30-40秒",
            "hypothesis": "購買イベント文脈はコメント相談を増やす可能性がある",
            "seasonality": "イベント時期依存。現在月にキャンペーンがある場合のみ使用",
        },
        {
            "title": "PR商品を正直レビューするときに見るべきポイント",
            "validation_type": "PR信頼性",
            "goal": "PRでも反応が落ちにくい見せ方を検証",
            "target": "PRレビューの本音度を見極めたい人",
            "hook": "PRだけど、ここは正直に言います",
            "structure": "PR表記 -> 良い点 -> 微妙な点 -> 向く人/向かない人",
            "duration": "25-35秒",
            "hypothesis": "PR表記と注意点の明示はコメント率低下を抑える可能性がある",
            "seasonality": "季節性なし",
        },
        {
            "title": "敏感肌向けスキンケア、買う前に確認したい成分",
            "validation_type": "悩み深掘り",
            "goal": "悩み特化テーマで保存理由を作る",
            "target": "敏感肌で新しいスキンケア選びが不安な人",
            "hook": "敏感肌さん、買う前にここだけ確認して",
            "structure": "悩み共感 -> 成分確認点 -> 避けたい例 -> 保存CTA",
            "duration": "25-40秒",
            "hypothesis": "悩みを明確化した投稿は保存率が高くなる可能性がある",
            "seasonality": "季節性なし",
        },
        {
            "title": "紫外線ケア、日焼け止め以外で見落としがちなポイント",
            "validation_type": "季節ニーズ",
            "goal": "現在月に合う季節テーマを検証",
            "target": "春夏の紫外線対策を始めたい人",
            "hook": "5月からここ見落とすと、夏に後悔しやすいです",
            "structure": "季節課題 -> 見落とし3点 -> 商品選び -> 保存CTA",
            "duration": "20-35秒",
            "hypothesis": "現在月に合う季節課題は視聴開始率を上げる可能性がある",
            "seasonality": _seasonality_for("uv"),
        },
        {
            "title": "使い切って分かった本音レビュー",
            "validation_type": "長期使用レビュー",
            "goal": "信頼感のある実使用レビューを検証",
            "target": "購入前に長期使用感を知りたい人",
            "hook": "使い切ったから、良かった所も微妙な所も言います",
            "structure": "使い切り証拠 -> 良い点 -> 微妙な点 -> リピ有無",
            "duration": "30-45秒",
            "hypothesis": "使い切り証拠はコメントでの相談を増やす可能性がある",
            "seasonality": "季節性なし",
        },
        {
            "title": "バズコスメ、本当に良かったところ・微妙だったところ",
            "validation_type": "バズ検証",
            "goal": "話題性と正直レビューの両立を検証",
            "target": "バズ商品を買うか迷っている人",
            "hook": "バズってるけど、全員におすすめではないです",
            "structure": "話題商品提示 -> 良い点 -> 微妙な点 -> 向く人/向かない人",
            "duration": "25-40秒",
            "hypothesis": "バズ商品の反証型レビューはシェア率が上がる可能性がある",
            "seasonality": "トレンド連動。trend_research入力後に優先度を再判定",
        },
        {
            "title": "似合う人と似合わない人が分かれるリップ",
            "validation_type": "対象者分岐",
            "goal": "フォロー理由になる選び方軸を検証",
            "target": "自分に似合う色を探している人",
            "hook": "このリップ、似合う人と似合わない人が分かれます",
            "structure": "結論 -> 似合う人 -> 似合わない人 -> 代替案",
            "duration": "20-30秒",
            "hypothesis": "対象者を分ける構成は保存とコメント相談を増やす可能性がある",
            "seasonality": "季節性なし",
        },
        {
            "title": "秋リップで失敗しやすい色選び3つ",
            "validation_type": "先取り季節企画",
            "goal": "先取りテーマで検索・保存需要を検証",
            "target": "秋メイクを早めに探し始める人",
            "hook": "秋リップ、早めに選ぶならこの3つ注意",
            "structure": "先取り理由 -> 失敗例3つ -> 選び方 -> 保存CTA",
            "duration": "20-35秒",
            "hypothesis": "先取り季節企画は検索流入の候補になる可能性がある",
            "seasonality": _seasonality_for("autumn_lip"),
        },
        {
            "title": "初心者がベースメイクでやりがちな失敗",
            "validation_type": "初心者教育",
            "goal": "初心者向けでフォロー理由を作る",
            "target": "ベースメイクを安定させたい初心者",
            "hook": "ベースメイクが崩れやすい人、これやってるかも",
            "structure": "失敗例 -> 原因 -> 直し方 -> 次回予告CTA",
            "duration": "25-40秒",
            "hypothesis": "初心者向けの失敗回避型はフォロー導線を作りやすい可能性がある",
            "seasonality": "季節性なし",
        },
    ]
    ideas = []
    for index, template in enumerate(templates, start=1):
        evidence = _evidence_for_idea(evidence_rows[(index - 1) % len(evidence_rows)] if evidence_rows else None)
        ideas.append(
            {
                "number": index,
                **template,
                "sound": "説明が聞き取りやすい低音量BGM。流行音源はtrend_researchで確認後に採用",
                "caption": "冒頭テロップは1画面1メッセージ。比較点・注意点・向く人を短く出す",
                "cta": "保存して買う前に見返してね / どれが気になるかコメントで教えてください",
                "success_kpi": "API: 中央値比、いいね率、コメント率、シェア率。手入力後: 保存率、完視聴率、プロフィール遷移率",
                "evidence_posts": [evidence] if evidence else [],
                "trend_evidence": trend_names[:3],
                "competitor_pattern_evidence": competitor_patterns[:3],
                "confidence": "信頼度C",
                "note": "暫定案。creative_notesとmanual_insights入力後に優先順位を更新してください。",
            }
        )
    return ideas


def _generate_operation_plan() -> list[dict[str, str]]:
    return [
        {
            "week": "Week 1",
            "posts": "3本",
            "theme": "買う前チェック型を3本",
            "genres": "リップ、スキンケア、ベースメイク",
            "improvement": "creative_notes.csvに冒頭3秒・構成・CTAを必ず記録",
            "kpi": "中央値比、いいね率、コメント率、シェア率",
            "manual_data": "saves、completion_rate、average_watch_time",
        },
        {
            "week": "Week 2",
            "posts": "3-4本",
            "theme": "正直レビューと比較型",
            "genres": "韓国コスメ比較、Qoo10候補、PR商品の見せ方",
            "improvement": "PR/非PRを分けて比較できるようis_prを入力",
            "kpi": "PR/非PR別中央値、コメント率",
            "manual_data": "profile_views、follows_from_video",
        },
        {
            "week": "Week 3",
            "posts": "3-4本",
            "theme": "使い切り・1週間使用レビュー",
            "genres": "スキンケア、リップ、ベースメイク",
            "improvement": "保存理由とコメント誘導を変えて検証",
            "kpi": "保存率、完視聴率、平均視聴維持率",
            "manual_data": "saves、average_watch_time、completion_rate",
        },
        {
            "week": "Week 4",
            "posts": "4本",
            "theme": "反応が良かった型の再投稿検証",
            "genres": "Week1-3の上位カテゴリ",
            "improvement": "同じ型で2本以上の再現性を確認",
            "kpi": "直近30投稿中央値、中央値比、投稿間隔",
            "manual_data": "traffic_source、audience_region",
        },
    ]


def _generate_kpi_design() -> dict[str, list[str]]:
    return {
        "api_only": [
            "再生数",
            "中央値比",
            "いいね率",
            "コメント率",
            "シェア率",
            "投稿頻度",
            "投稿間隔",
            "動画尺別中央値",
        ],
        "manual_required": [
            "保存率",
            "プロフィール遷移率",
            "フォロー転換率",
            "完視聴率",
            "平均視聴維持率",
            "流入元別成果",
        ],
    }


def _generate_hypotheses() -> list[dict[str, str]]:
    return [
        {
            "priority": "高",
            "hypothesis": "買う前チェック型は美容アカウントで保存率を上げる可能性がある",
            "data": "creative_notes、manual_insights",
            "method": "同じ構成で3本投稿し、保存率と完視聴率を比較",
            "posts": "3本",
            "success": "保存率が過去中央値以上、かつAPI中央値比1.2倍以上",
            "confidence": "信頼度C",
            "action": "hook_type=買う前チェックで記録して投稿",
        },
        {
            "priority": "高",
            "hypothesis": "PR投稿は注意点を明示するとコメント率の低下を抑えられる可能性がある",
            "data": "creative_notesのis_pr、cta_type、manual_insights",
            "method": "PR候補と非PRを分けて中央値とコメント率を比較",
            "posts": "PR 3本 / 非PR 3本",
            "success": "PR投稿のコメント率が非PR中央値の70%以上",
            "confidence": "信頼度C",
            "action": "PR表記と注意点を明示して投稿",
        },
        {
            "priority": "中",
            "hypothesis": "対象者を明確に分ける構成はコメント相談を増やす可能性がある",
            "data": "creative_notesのtarget_viewer、comment_prompt",
            "method": "似合う人/似合わない人型を3本投稿し、コメント率を比較",
            "posts": "3本",
            "success": "コメント率が過去中央値以上",
            "confidence": "信頼度C",
            "action": "対象者分岐型の台本で検証",
        },
    ]


def _generate_backlog() -> dict[str, list[str]]:
    return {
        "すぐやる": [
            "API取得CSVをapi_postsとして残し、上位10投稿にcreative_notesを入力する",
            "保存数、完視聴率、平均視聴時間をmanual_insights.csvへ10本分転記する",
            "PR投稿のis_prとPR表記を確認する",
        ],
        "次の10投稿で試す": [
            "買う前チェック型を3本",
            "正直レビュー型を3本",
            "使い切り・1週間レビュー型を2本",
            "似合う人/似合わない人型を2本",
        ],
        "30日以内にやる": [
            "直近30投稿中央値を追跡",
            "PR/非PR別の中央値比較",
            "美容本流以外の投稿を分析対象から分離",
        ],
        "データ入力を増やしてからやる": [
            "保存率を軸にした投稿構成比較",
            "完視聴率を使った尺の最適化",
            "流入元別の改善案",
        ],
        "外部ツール連携候補": [
            "TikTok Creative Centerの手動調査結果CSV",
            "Google Trendsの美容キーワードCSV",
            "過去レポート比較",
        ],
        "やらない方がよい": [
            "スクレイピング",
            "自動ログイン",
            "自動投稿・自動エンゲージメント",
            "非美容テーマを美容アカウントの改善案に混ぜる",
        ],
    }


def _generate_executive_summary(analysis: dict[str, Any]) -> dict[str, Any]:
    summary = analysis["summaries"]["all"]
    strategy_confidence = analysis["data_scope"]["strategy_recommendation_confidence"]
    return {
        "api_fact": f"APIで確認できる投稿は{format_number(summary['post_count'])}本、中央値再生数は{format_number(summary['median_views'])}です。",
        "strategy_note": f"戦略提案信頼度は{strategy_confidence}です。手入力データの不足がある場合、提案は暫定案として扱います。",
        "biggest_gap": "保存率・完視聴率・平均視聴時間・冒頭3秒・動画構成は公式APIだけでは通常取得できないため、手入力が必要です。",
        "next_action": "まず優先入力対象10本にmanual_insightsとcreative_notesを入れ、勝ち筋候補を再判定してください。",
    }


def _frequency_snapshot(rows: list[dict[str, Any]], days: int | None = None) -> dict[str, Any]:
    dated = [row for row in rows if row.get("posted_dt") is not None]
    if days is not None:
        now = datetime.now(timezone.utc)
        dated = [row for row in dated if row["posted_dt"] >= now - timedelta(days=days)]
        return {"post_count": len(dated), "weekly_frequency": len(dated) / days * 7 if days > 0 else None}
    dates = sorted(row["posted_dt"] for row in dated)
    if len(dates) < 2:
        return {"post_count": len(dates), "weekly_frequency": None}
    span_days = max(1, (dates[-1] - dates[0]).days + 1)
    return {"post_count": len(dates), "weekly_frequency": len(dates) / span_days * 7}


def _caption_notes(rows: list[dict[str, Any]]) -> list[str]:
    if not rows:
        return ["投稿がないため判断不可。"]
    pr_count = sum(1 for row in rows if row["pr_status"] in PR_STATUSES)
    return [
        f"PR候補は{pr_count}本。PR判定は自動推定を含むため、creative_notes.csvで確定してください。",
        "ハッシュタグは出現回数で分類し、1回だけのタグは戦略判断に使いません。",
        "#PR と #ad はPR開示タグとして扱い、有望タグ候補から除外します。",
    ]


def _evidence_for_idea(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "video_id": row["video_id"],
        "title": row["title"],
        "category": row["strategy_category"],
        "view_count": row["view_count"],
        "pr_status": row["pr_status"],
        "posted_at": row["posted_at"],
        "duration": row["duration"],
    }


def _seasonality_for(kind: str) -> str:
    month = datetime.now().month
    if kind == "uv":
        if 4 <= month <= 8:
            return f"現在月（{month}月）に合う"
        return "先取り企画（春夏の紫外線需要向け）"
    if kind == "autumn_lip":
        if 8 <= month <= 10:
            return f"現在月（{month}月）に合う"
        return "先取り企画（秋リップ需要向け）"
    return "季節性なし"


def _is_recent(row: dict[str, Any], days: int, now: datetime) -> bool:
    posted_dt = row.get("posted_dt")
    return posted_dt is not None and posted_dt >= now - timedelta(days=days)


def _coverage(total: int, filled: int) -> float:
    if total <= 0:
        return 0.0
    return filled / total
