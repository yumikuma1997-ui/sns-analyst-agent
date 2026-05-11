from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from classifiers import (
    classify_duration_bucket,
    classify_post_time_bucket,
    classify_strategy_category,
    detect_outlier_viral_posts,
    detect_pr_status,
    hashtag_groups,
)
from confidence import calculate_confidence_level, manual_metric_confidence
from metrics import calculate_api_metrics, safe_divide, summarize_api_posts
from models import AccountProfile, ApiPost, CompetitorPost, CreativeNote, ManualInsight, TrendResearch
from utils import DATA_INSUFFICIENT, format_number, format_percent, median, parse_datetime


MANUAL_REQUIRED_METRICS = [
    ("保存数", "manual_insights.csv", "保存率、保存される理由の検証"),
    ("保存率", "manual_insights.csv", "保存価値の強い投稿型の比較"),
    ("プロフィールアクセス数", "manual_insights.csv", "プロフィール導線の評価"),
    ("投稿単位のフォロー増加数", "manual_insights.csv", "フォロー転換に効いた投稿の特定"),
    ("フォロー転換率", "manual_insights.csv", "再生からフォローへの効率比較"),
    ("完視聴率", "manual_insights.csv", "尺と構成の維持率比較"),
    ("平均視聴時間", "manual_insights.csv", "冒頭と構成の離脱検証"),
    ("視聴維持率", "manual_insights.csv", "動画尺に対する視聴の深さ"),
    ("流入元", "manual_insights.csv", "おすすめ、検索、プロフィールなど流入別評価"),
    ("視聴者属性", "manual_insights.csv", "想定ターゲットとの一致確認"),
    ("冒頭3秒", "creative_notes.csv", "フック構造と成果の関係"),
    ("動画構成", "creative_notes.csv", "構成パターンの再現性確認"),
    ("CTA", "creative_notes.csv", "コメント・保存・フォロー誘導の検証"),
    ("顔出し有無", "creative_notes.csv", "顔出しと反応の関係"),
    ("声出し有無", "creative_notes.csv", "声出しと維持率の関係"),
    ("PR有無", "creative_notes.csv", "PR/非PRの正確な比較"),
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
    creative_coverage = _coverage(len(rows), len(creative_by_id))
    manual_coverage = _coverage(len(rows), len(manual_by_id))

    return {
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
            "overall_confidence": calculate_confidence_level(len(rows), True, creative_coverage, manual_coverage),
        },
        "rows": rows,
        "summaries": {
            "all": overall_summary,
            "beauty_core": _scope_summary([row for row in rows if row["strategy_category"] == "beauty_core"]),
            "beauty_with_adjacent": _scope_summary(
                [row for row in rows if row["strategy_category"] in {"beauty_core", "beauty_adjacent"}]
            ),
            "pr": _scope_summary([row for row in rows if row["pr_status"] in {"明示PR", "PR疑い"}]),
            "non_pr": _scope_summary([row for row in rows if row["pr_status"] == "非PR"]),
            "unrelated": _scope_summary([row for row in rows if row["strategy_category"] == "unrelated"]),
            "buzz_excluded": buzz_excluded,
        },
        "missing_data": _missing_data_table(manual_insights, creative_notes, rows),
        "viral": _analyze_viral(rows, viral_posts),
        "beauty_analysis": _analyze_beauty(rows),
        "pr_analysis": _analyze_pr(rows),
        "habits": _analyze_habits(rows),
        "hashtags": _analyze_hashtags(rows, overall_summary["median_views"]),
        "creative_analysis": _analyze_creative(rows, creative_by_id),
        "trend_analysis": _analyze_trends(trend_research),
        "competitor_analysis": _analyze_competitors(competitor_posts),
        "video_ideas": _generate_video_ideas(rows, trend_research, competitor_posts),
        "operation_plan": _generate_operation_plan(),
        "kpi_design": _generate_kpi_design(),
        "hypotheses": _generate_hypotheses(),
        "backlog": _generate_backlog(),
    }


def _build_row(post: ApiPost, manual: ManualInsight | None, creative: CreativeNote | None) -> dict[str, Any]:
    metrics = calculate_api_metrics(post)
    posted_dt = parse_datetime(post.posted_at or post.create_time)
    strategy_category = classify_strategy_category(post, creative)
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
        "strategy_category": strategy_category,
        "strategy_category_source": "manual" if creative and creative.account_strategy_category else "auto_caption",
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
    manual_values = {
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
        has_value = manual_values.get(metric, False)
        if has_value:
            status = "一部入力あり"
            reason = "手入力データがあります。入力がある投稿に限定して分析できます。"
        elif metric == "PR有無" and rows:
            status = "自動推定のみ"
            reason = "caption内の#PR等で候補判定は可能ですが、確定にはcreative_notes.csvへの入力が必要です。"
        else:
            status = "未入力"
            reason = "TikTok公式の公開動画APIでは通常取得できないため、手入力が必要です。"
        table.append(
            {
                "metric": metric,
                "status": status,
                "reason": reason,
                "input": input_file,
                "benefit": benefit,
            }
        )
    return table


def _analyze_viral(rows: list[dict[str, Any]], viral_posts: list[dict[str, Any]]) -> dict[str, Any]:
    repeat_patterns = Counter(
        (row.get("hook_type"), row.get("video_structure"))
        for row in rows
        if row.get("hook_type") or row.get("video_structure")
    )
    reproducible = []
    low_reproducibility = []
    for row in viral_posts:
        creative_ready = bool(row.get("hook_text") or row.get("video_structure"))
        beauty_related = row["strategy_category"] in {"beauty_core", "beauty_adjacent"}
        pattern_count = repeat_patterns[(row.get("hook_type"), row.get("video_structure"))]
        if beauty_related and creative_ready and pattern_count >= 2:
            reproducible.append(row)
        else:
            low_reproducibility.append(row)
    return {
        "viral_posts": viral_posts,
        "reproducible": reproducible,
        "low_reproducibility": low_reproducibility,
        "confidence": "信頼度B" if viral_posts else "信頼度D",
    }


def _analyze_beauty(rows: list[dict[str, Any]]) -> dict[str, Any]:
    core = [row for row in rows if row["strategy_category"] == "beauty_core"]
    adjacent = [row for row in rows if row["strategy_category"] == "beauty_adjacent"]
    unrelated = [row for row in rows if row["strategy_category"] in {"lifestyle", "personal", "unrelated"}]
    ordered_core = sorted(core, key=lambda row: row.get("view_count") or 0, reverse=True)
    return {
        "core_count": len(core),
        "adjacent_count": len(adjacent),
        "unrelated_count": len(unrelated),
        "core_summary": _scope_summary(core),
        "top_core": ordered_core[:5],
        "weak_core": list(reversed(ordered_core[-5:])),
        "missing": "creative_notes.csvが不足すると、冒頭3秒・構成・CTAの共通点は判断できません。",
        "confidence": calculate_confidence_level(len(core), True, _coverage(len(rows), sum(1 for row in core if row.get("creative")))),
    }


def _analyze_pr(rows: list[dict[str, Any]]) -> dict[str, Any]:
    pr = [row for row in rows if row["pr_status"] in {"明示PR", "PR疑い"}]
    non_pr = [row for row in rows if row["pr_status"] == "非PR"]
    return {
        "status_counts": Counter(row["pr_status"] for row in rows).most_common(),
        "pr_summary": _scope_summary(pr),
        "non_pr_summary": _scope_summary(non_pr),
        "confidence": "信頼度B" if pr or non_pr else "信頼度D",
    }


def _analyze_habits(rows: list[dict[str, Any]]) -> dict[str, Any]:
    all_summary = _scope_summary(rows)
    return {
        "weekly_frequency": _weekly_frequency(rows),
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
            "message": "creative_notes.csv が未入力のため、冒頭3秒、構成、CTA、テロップ密度は判断しません。",
            "required_fields": [
                "hook_text",
                "hook_type",
                "first_3sec_summary",
                "video_structure",
                "cta_type",
                "text_density",
                "save_reason",
                "comment_prompt",
            ],
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
            "message": "trend_research.csv が未入力のため、現在トレンドとの適合は判断しません。",
            "manual_research_items": [
                "Creative Centerの美容関連ハッシュタグ",
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
        "copy_guardrail": "参考アカウントから輸入するのは型だけです。テーマ、台本、固有表現、映像構成の丸写しはしません。",
    }


def _generate_video_ideas(
    rows: list[dict[str, Any]],
    trend_research: list[TrendResearch],
    competitor_posts: list[CompetitorPost],
) -> list[dict[str, str]]:
    top_beauty = [
        row
        for row in sorted(rows, key=lambda item: item.get("view_count") or 0, reverse=True)
        if row["strategy_category"] in {"beauty_core", "beauty_adjacent"}
    ][:3]
    evidence = "; ".join(
        f"{row['video_id']}({format_number(row.get('view_count'))}再生)" for row in top_beauty
    ) or "美容本流の手入力メモが不足しているため、暫定案"
    trend_evidence = ", ".join(item.trend_name for item in trend_research if item.should_use is True) or "手動トレンド未入力"
    competitor_evidence = ", ".join(
        item.hook_type or item.video_structure
        for item in competitor_posts
        if item.should_adapt is True and item.adaptation_target in {"hook", "structure", "cta", "text_density"}
    ) or "参考投稿の型メモ未入力"
    templates = [
        ("そのリップ買う前に見るべき3つのポイント", "買う前チェック", "リップ購入で失敗したくない人"),
        ("Qoo10メガ割で失敗しにくい韓国コスメの選び方", "購入候補整理", "韓国コスメを比較検討している人"),
        ("PR商品を正直レビューするときに見るべきポイント", "PRの信頼性改善", "PR投稿でも本音を知りたい人"),
        ("敏感肌向けスキンケア、買う前に確認したい成分", "保存理由の強化", "肌荒れしやすい人"),
        ("秋リップで失敗しやすい色選び3つ", "季節需要の検証", "季節リップを探す人"),
        ("使い切って分かった本音レビュー", "信頼性強化", "購入前に長期使用感を知りたい人"),
        ("バズコスメ、本当に良かったところ・微妙だったところ", "バズ検証", "話題商品を買うか迷う人"),
        ("似合う人と似合わない人が分かれるリップ", "対象者明確化", "自分に合う色を知りたい人"),
        ("初心者がベースメイクでやりがちな失敗", "初心者向け教育", "メイク初心者"),
        ("1週間使って分かったスキンケアの正直感想", "継続使用レビュー", "スキンケア選びで迷う人"),
    ]
    ideas = []
    for index, (title, goal, target) in enumerate(templates, start=1):
        ideas.append(
            {
                "number": str(index),
                "title": title,
                "goal": goal,
                "target": target,
                "hook": f"冒頭で「{title}」を短く提示し、買う前の不安を1つに絞る",
                "structure": "悩み提示 → 比較/確認ポイント3つ → 正直な注意点 → 向いている人/向かない人",
                "duration": "20〜35秒",
                "sound": "美容レビューの説明が聞き取りやすいBGM。流行音源はtrend_research.csvで確認後に採用",
                "caption": "要点を1画面1メッセージで表示。商品名、良い点、注意点を分ける",
                "cta": "保存して買う前に見返してね / あなたはどれが気になる？",
                "hypothesis": "買う前チェック型は保存・コメントにつながる可能性がある。保存率はmanual_insights入力後に検証する",
                "success_kpi": "API: 中央値比、いいね率、コメント率、シェア率。手入力後: 保存率、完視聴率",
                "evidence": f"{evidence} / trend: {trend_evidence} / reference pattern: {competitor_evidence}",
                "confidence": "信頼度C",
                "note": "暫定案。creative_notes と manual_insights の入力後に優先順位を再評価する",
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
            "improvement": "creative_notes.csvに冒頭3秒、構成、CTAを必ず記録",
            "kpi": "中央値比、いいね率、コメント率、シェア率",
            "manual_data": "保存数、完視聴率、平均視聴時間",
        },
        {
            "week": "Week 2",
            "posts": "3〜4本",
            "theme": "正直レビューと比較",
            "genres": "韓国コスメ比較、Qoo10候補、PR商品の見せ方",
            "improvement": "PR/非PRを分けて比較できるようis_prを入力",
            "kpi": "PR/非PR別中央値、コメント率",
            "manual_data": "profile_views、follows_from_video",
        },
        {
            "week": "Week 3",
            "posts": "3〜4本",
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
            "kpi": "直近10投稿中央値、中央値比、投稿間隔",
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
            "success": "中央値比1.5倍以上、保存率が過去中央値以上",
            "confidence": "信頼度C",
            "action": "hook_type=買う前チェックで記録して投稿",
        },
        {
            "priority": "高",
            "hypothesis": "PR投稿は正直な注意点を入れるとコメント率が下がりにくい可能性がある",
            "data": "creative_notesのis_pr、cta_type、manual_insights",
            "method": "PR候補と非PRを分けて中央値とコメント率を比較",
            "posts": "PR 3本 / 非PR 3本",
            "success": "PR投稿のコメント率が非PR中央値の70%以上",
            "confidence": "信頼度C",
            "action": "PR表記と注意点を明示して投稿",
        },
        {
            "priority": "中",
            "hypothesis": "20〜35秒の比較レビューは完視聴率と保存率のバランスが良い可能性がある",
            "data": "API duration、manual_insights completion_rate/saves",
            "method": "尺別中央値、完視聴率、保存率を比較",
            "posts": "各尺3本",
            "success": "20〜35秒が2指標以上で上位",
            "confidence": "信頼度C",
            "action": "尺を固定して比較レビューを投稿",
        },
    ]


def _generate_backlog() -> dict[str, list[str]]:
    return {
        "すぐやる": [
            "data/tiktok_videos.local.csvをapi_postsとして残し、creative_notes.csvを動画ID単位で入力する",
            "保存数、完視聴率、平均視聴時間をmanual_insights.csvへ10本分転記する",
            "PR投稿のis_prとPR表記を確認する",
        ],
        "次の10投稿で試す": [
            "買う前チェック型を3本",
            "正直レビュー型を3本",
            "使い切り/1週間レビュー型を2本",
            "似合う人・似合わない人型を2本",
        ],
        "30日以内にやる": [
            "直近10投稿中央値を追跡",
            "PR/非PR別の中央値比較",
            "美容本流以外の投稿を分析から分離",
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


def _weekly_frequency(rows: list[dict[str, Any]]) -> float | None:
    dates = sorted(row["posted_dt"] for row in rows if row.get("posted_dt") is not None)
    if len(dates) < 2:
        return None
    span_days = max(1, (dates[-1] - dates[0]).days + 1)
    return len(dates) / span_days * 7


def _caption_notes(rows: list[dict[str, Any]]) -> list[str]:
    if not rows:
        return ["投稿がないため判断不可。"]
    pr_count = sum(1 for row in rows if row["pr_status"] in {"明示PR", "PR疑い"})
    return [
        f"PR候補は{pr_count}本。PR表記は自動推定のため、creative_notes.csvで確定してください。",
        "ハッシュタグは出現回数で分類し、1回だけのタグは戦略判断には使いません。",
    ]


def _coverage(total: int, filled: int) -> float:
    if total <= 0:
        return 0.0
    return filled / total
