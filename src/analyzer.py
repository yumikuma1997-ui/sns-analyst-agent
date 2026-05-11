from __future__ import annotations

from collections import Counter
from dataclasses import asdict
from typing import Any

from metrics import calculate_all_post_metrics, summarize_posts
from models import AccountProfile, Post, PostMetric
from utils import (
    DATA_INSUFFICIENT,
    duration_bucket,
    format_number,
    mean,
    parse_date,
    safe_join,
    time_bucket,
    top_items,
    top_terms,
)


def analyze(
    account: AccountProfile,
    posts: list[Post],
    trends: list[dict[str, Any]],
    competitors: list[dict[str, Any]],
    competitor_posts: list[Post] | None = None,
) -> dict[str, Any]:
    competitor_posts = competitor_posts or []
    metrics = calculate_all_post_metrics(posts)
    summary = summarize_posts(metrics)
    ranked = _rank_posts(metrics)
    habits = _analyze_habits(posts)
    performance = _analyze_performance(metrics, ranked["top"], ranked["weak"])
    trend_analysis = _analyze_trends(posts, trends)
    competitor_post_analysis = _analyze_reference_posts(posts, competitor_posts)
    competitor_analysis = _analyze_competitors(competitors, competitor_post_analysis)
    strategy = _build_strategy(account, summary, performance, habits, trend_analysis)

    return {
        "account": asdict(account),
        "posts": posts,
        "metrics": metrics,
        "summary": summary,
        "ranked": ranked,
        "performance": performance,
        "habits": habits,
        "trend_analysis": trend_analysis,
        "competitor_analysis": competitor_analysis,
        "competitor_post_analysis": competitor_post_analysis,
        "strategy": strategy,
        "video_ideas": _generate_video_ideas(account, performance, trend_analysis, competitors),
        "operation_plan": _generate_operation_plan(account, performance, trend_analysis),
        "kpi_design": _generate_kpi_design(summary),
        "hypotheses": _generate_hypotheses(performance, habits, trend_analysis),
        "backlog": _generate_backlog(),
    }


def _rank_posts(metrics: list[PostMetric]) -> dict[str, list[PostMetric]]:
    valid = [metric for metric in metrics if metric.post.views is not None]
    ordered = sorted(valid, key=lambda item: item.post.views or 0, reverse=True)
    if not ordered:
        return {"top": [], "weak": []}
    size = max(1, min(3, round(len(ordered) * 0.25)))
    return {"top": ordered[:size], "weak": list(reversed(ordered[-size:]))}


def _analyze_performance(
    metrics: list[PostMetric],
    top_metrics: list[PostMetric],
    weak_metrics: list[PostMetric],
) -> dict[str, Any]:
    top_posts = [metric.post for metric in top_metrics]
    weak_posts = [metric.post for metric in weak_metrics]
    best_by = {
        "views": _best_metric(metrics, lambda metric: metric.post.views),
        "like_rate": _best_metric(metrics, lambda metric: metric.like_rate),
        "comment_rate": _best_metric(metrics, lambda metric: metric.comment_rate),
        "save_rate": _best_metric(metrics, lambda metric: metric.save_rate),
        "share_rate": _best_metric(metrics, lambda metric: metric.share_rate),
        "follow_conversion_rate": _best_metric(metrics, lambda metric: metric.follow_conversion_rate),
        "completion_rate": _best_metric(metrics, lambda metric: metric.post.completion_rate),
        "avg_retention_rate": _best_metric(metrics, lambda metric: metric.avg_retention_rate),
    }

    return {
        "best_by": best_by,
        "top_common": _common_traits(top_posts),
        "weak_common": _common_traits(weak_posts),
        "top_evidence": _evidence_lines(top_metrics),
        "weak_evidence": _evidence_lines(weak_metrics),
        "quantitative_notes": _quantitative_notes(metrics, top_metrics, weak_metrics),
        "qualitative_notes": _qualitative_notes(top_posts, weak_posts),
    }


def _best_metric(metrics: list[PostMetric], getter) -> PostMetric | None:
    candidates = [(getter(metric), metric) for metric in metrics if getter(metric) is not None]
    if not candidates:
        return None
    return max(candidates, key=lambda item: item[0])[1]


def _common_traits(posts: list[Post]) -> dict[str, Any]:
    return {
        "genres": top_terms(post.genre for post in posts),
        "sounds": top_terms(post.sound for post in posts),
        "hashtags": top_terms(tag for post in posts for tag in post.hashtags),
        "duration_buckets": top_terms(duration_bucket(post.duration_sec) for post in posts),
        "time_buckets": top_terms(time_bucket(post.time) for post in posts),
        "cta_ratio": mean(1 if post.has_cta else 0 for post in posts if post.has_cta is not None),
        "hooks": [post.hook for post in posts if post.hook][:5],
        "structures": [post.structure for post in posts if post.structure][:5],
        "titles": [post.title for post in posts if post.title][:5],
        "notes": [post.notes for post in posts if post.notes][:5],
    }


def _evidence_lines(metrics: list[PostMetric]) -> list[str]:
    lines = []
    for metric in metrics:
        post = metric.post
        views = post.views if post.views is not None else DATA_INSUFFICIENT
        lines.append(f"{post.title}: 再生数 {views}、ジャンル {post.genre or DATA_INSUFFICIENT}、冒頭「{post.hook or DATA_INSUFFICIENT}」")
    return lines


def _quantitative_notes(
    metrics: list[PostMetric],
    top_metrics: list[PostMetric],
    weak_metrics: list[PostMetric],
) -> list[str]:
    notes = []
    if not metrics:
        return ["投稿データがないため、数値分析はデータ不足です。"]
    if len(metrics) < 10:
        notes.append("投稿数が10本未満の場合、傾向は暫定仮説として扱う必要があります。")
    top_views = mean(metric.post.views for metric in top_metrics)
    weak_views = mean(metric.post.views for metric in weak_metrics)
    if top_views is not None and weak_views is not None and weak_views > 0:
        notes.append(f"上位投稿の平均再生数は下位投稿の約{top_views / weak_views:.1f}倍です。")
    save_rate = mean(metric.save_rate for metric in top_metrics)
    weak_save_rate = mean(metric.save_rate for metric in weak_metrics)
    if save_rate is not None and weak_save_rate is not None:
        if save_rate > weak_save_rate:
            notes.append("伸びた投稿は保存率も高く、実用性や後で見返す理由が再生拡大に寄与した可能性があります。")
        else:
            notes.append("再生数上位と保存率上位が一致していないため、話題性と保存価値を分けて検証してください。")
    return notes or ["率計算に必要な再生数または反応数が不足しています。"]


def _qualitative_notes(top_posts: list[Post], weak_posts: list[Post]) -> list[str]:
    notes = []
    if any("NG" in post.structure or "NG" in post.title for post in top_posts):
        notes.append("伸びた投稿にはNG提示や損失回避の構成が含まれており、冒頭で見る理由を作れている可能性があります。")
    if any(post.has_cta for post in top_posts):
        notes.append("上位投稿はCTAや保存促しが入りやすく、視聴後の行動を設計できている可能性があります。")
    if any(not post.has_cta for post in weak_posts if post.has_cta is not None):
        notes.append("伸びなかった投稿にはCTAなしのものがあり、保存・コメント・フォローへの導線が弱い可能性があります。")
    if any("Vlog" in post.title or "ルーティン" in post.genre for post in weak_posts):
        notes.append("Vlogやルーティン寄りの投稿は、誰のどんな悩みを解決するかが曖昧になると伸びにくい可能性があります。")
    return notes or ["定性情報が不足しているため、冒頭、構成、CTA、投稿メモを追加すると改善仮説を作りやすくなります。"]


def _analyze_habits(posts: list[Post]) -> dict[str, Any]:
    dates = [parse_date(post.date) for post in posts]
    valid_dates = sorted(date for date in dates if date is not None)
    span_days = None
    weekly_frequency = None
    max_gap_days = None
    if valid_dates:
        span_days = max(1, (valid_dates[-1] - valid_dates[0]).days + 1)
        weekly_frequency = len(valid_dates) / span_days * 7
        gaps = [(valid_dates[index] - valid_dates[index - 1]).days for index in range(1, len(valid_dates))]
        max_gap_days = max(gaps, default=0)
    genres = Counter(post.genre for post in posts if post.genre)
    day_counts = Counter(post.day_of_week for post in posts if post.day_of_week)
    time_counts = Counter(time_bucket(post.time) for post in posts if post.time)
    cta_ratio = mean(1 if post.has_cta else 0 for post in posts if post.has_cta is not None)
    notes = []
    if weekly_frequency is None:
        notes.append("投稿日が不足しているため、投稿頻度はデータ不足です。")
    elif weekly_frequency < 3:
        notes.append("週3本未満のペースです。次の30日間は検証回数を増やすため、週3-5本を目安にしてください。")
    else:
        notes.append(f"投稿頻度は週約{weekly_frequency:.1f}本です。検証に必要な最低限の試行回数は確保できています。")
    if max_gap_days is not None and max_gap_days >= 5:
        notes.append(f"最大投稿間隔が{max_gap_days}日あります。継続性の検証では投稿間隔を詰める余地があります。")
    if genres and genres.most_common(1)[0][1] / len(posts) > 0.55:
        notes.append(f"投稿ジャンルは「{genres.most_common(1)[0][0]}」に偏っています。勝ち筋なら強化しつつ、隣接テーマも検証してください。")
    if cta_ratio is not None and cta_ratio < 0.7:
        notes.append("CTAありの投稿比率が低めです。保存・コメント・フォローのどれを狙う投稿かを明確にしてください。")
    return {
        "span_days": span_days,
        "weekly_frequency": weekly_frequency,
        "max_gap_days": max_gap_days,
        "genre_counts": genres.most_common(),
        "day_counts": day_counts.most_common(),
        "time_counts": time_counts.most_common(),
        "cta_ratio": cta_ratio,
        "notes": notes,
    }


def _analyze_trends(posts: list[Post], trends: list[dict[str, Any]]) -> dict[str, Any]:
    post_sounds = {post.sound for post in posts if post.sound}
    post_genres = {post.genre for post in posts if post.genre}
    used_trends = []
    easy_to_apply = []
    avoid_or_adapt = []
    for trend in trends:
        trend_sounds = set(_list_value(trend.get("trending_sounds")))
        trend_genres = set(_list_value(trend.get("genres")))
        matched_sounds = sorted(post_sounds & trend_sounds)
        matched_genres = sorted(post_genres & trend_genres)
        item = {
            "name": trend.get("name", DATA_INSUFFICIENT),
            "matched_sounds": matched_sounds,
            "matched_genres": matched_genres,
            "applicable_points": trend.get("applicable_points", DATA_INSUFFICIENT),
            "growth_hypothesis": trend.get("growth_hypothesis", DATA_INSUFFICIENT),
            "opening_hooks": _list_value(trend.get("opening_hooks")),
            "video_structures": _list_value(trend.get("video_structures")),
            "editing_tempo": trend.get("editing_tempo", DATA_INSUFFICIENT),
        }
        if matched_sounds or matched_genres:
            used_trends.append(item)
            easy_to_apply.append(item)
        else:
            avoid_or_adapt.append(item)
    notes = []
    if not trends:
        notes.append("trends.json が空のため、現在トレンドとの比較はデータ不足です。")
    elif easy_to_apply:
        notes.append("既存投稿ジャンルと重なるトレンドがあります。完全に別ジャンルへ寄せるより、既存の勝ち筋に構成だけ取り入れる方が検証しやすいです。")
    if avoid_or_adapt:
        notes.append("ジャンルや音源が一致しないトレンドは、無理に寄せるとアカウントの一貫性が弱まる可能性があります。構成や冒頭だけ抽出して使ってください。")
    return {
        "used_trends": used_trends,
        "easy_to_apply": easy_to_apply,
        "avoid_or_adapt": avoid_or_adapt,
        "notes": notes,
    }


def _analyze_competitors(
    competitors: list[dict[str, Any]],
    competitor_post_analysis: dict[str, Any] | None = None,
) -> dict[str, Any]:
    takeaways = []
    avoid_points = []
    for competitor in competitors:
        name = competitor.get("account_name", DATA_INSUFFICIENT)
        takeaways.append(
            {
                "account_name": name,
                "url": competitor.get("url", ""),
                "posting_frequency": competitor.get("posting_frequency", DATA_INSUFFICIENT),
                "winning_video_features": competitor.get("winning_video_features", DATA_INSUFFICIENT),
                "opening_hooks": _list_value(competitor.get("opening_hooks")),
                "video_structure": competitor.get("video_structure", DATA_INSUFFICIENT),
                "applicable_points": competitor.get("applicable_points", DATA_INSUFFICIENT),
            }
        )
        avoid = competitor.get("avoid_points")
        if avoid:
            avoid_points.append(f"{name}: {avoid}")
    return {
        "takeaways": takeaways,
        "avoid_points": avoid_points or ["参考アカウントの避けるべき点が未入力です。次回から記録してください。"],
        "post_comparison": competitor_post_analysis or {},
    }


def _analyze_reference_posts(self_posts: list[Post], reference_posts: list[Post]) -> dict[str, Any]:
    if not reference_posts:
        return {
            "has_data": False,
            "summary": "参考アカウント投稿CSVが未入力のため、投稿単位の比較はデータ不足です。",
            "accounts": [],
            "top_reference_posts": [],
            "adopt_points": ["参考アカウントの投稿単位データを入力すると、取り入れるべき構成・冒頭・CTAを比較できます。"],
            "avoid_points": ["数値だけで模倣対象を決めず、自アカウントのジャンル・ターゲットと合うものだけ検証してください。"],
            "differentiation_points": ["自アカウントの投稿実績を基準に、参考アカウントの強い型を部分的に取り入れてください。"],
        }

    reference_metrics = calculate_all_post_metrics(reference_posts)
    ranked_reference = sorted(
        [metric for metric in reference_metrics if metric.post.views is not None],
        key=lambda metric: metric.post.views or 0,
        reverse=True,
    )
    top_reference_metrics = ranked_reference[:5]
    top_reference_posts = [metric.post for metric in top_reference_metrics]
    self_top_posts = [metric.post for metric in _rank_posts(calculate_all_post_metrics(self_posts))["top"]]
    reference_traits = _common_traits(top_reference_posts)
    self_traits = _common_traits(self_top_posts)
    account_summaries = _reference_account_summaries(reference_posts)
    adopt_points = _reference_adopt_points(reference_traits, self_traits, top_reference_posts)
    avoid_points = _reference_avoid_points(reference_traits, self_traits)
    differentiation_points = _reference_differentiation_points(reference_traits, self_traits)

    return {
        "has_data": True,
        "summary": f"参考アカウント投稿 {len(reference_posts)}本を読み込み、上位{len(top_reference_posts)}本を比較しました。",
        "accounts": account_summaries,
        "top_reference_posts": _reference_evidence_lines(top_reference_metrics),
        "reference_traits": reference_traits,
        "self_traits": self_traits,
        "adopt_points": adopt_points,
        "avoid_points": avoid_points,
        "differentiation_points": differentiation_points,
    }


def _reference_account_summaries(reference_posts: list[Post]) -> list[dict[str, Any]]:
    grouped: dict[str, list[Post]] = {}
    for post in reference_posts:
        grouped.setdefault(getattr(post, "account_name", DATA_INSUFFICIENT), []).append(post)

    summaries = []
    for account_name, posts in sorted(grouped.items()):
        views = [post.views for post in posts]
        genres = top_terms(post.genre for post in posts)
        hooks = [post.hook for post in posts if post.hook][:3]
        summaries.append(
            {
                "account_name": account_name,
                "post_count": len(posts),
                "average_views": mean(views),
                "top_genres": genres,
                "hooks": hooks,
            }
        )
    return summaries


def _reference_adopt_points(
    reference_traits: dict[str, Any],
    self_traits: dict[str, Any],
    top_reference_posts: list[Post],
) -> list[str]:
    points = []
    reference_genres = [item for item, _ in reference_traits["genres"]]
    self_genres = {item for item, _ in self_traits["genres"]}
    genre_gaps = [genre for genre in reference_genres if genre not in self_genres]
    if genre_gaps:
        points.append(f"参考上位投稿で強い「{safe_join(genre_gaps[:3])}」は、自アカウントの勝ち筋と隣接する場合だけ検証候補にしてください。")
    if reference_traits["hooks"]:
        points.append(f"冒頭は「{reference_traits['hooks'][0]}」のように、悩み・損失・変化を1文で出す型を取り入れる余地があります。")
    if reference_traits["structures"]:
        points.append(f"構成は「{reference_traits['structures'][0]}」をそのままコピーせず、自分の素材で再現できる手順に分解してください。")
    if any(post.has_cta for post in top_reference_posts):
        points.append("参考上位投稿にはCTAが含まれるため、保存促し・質問誘導・フォロー理由を投稿目的ごとに使い分けてください。")
    return points or ["投稿単位の差分が小さいため、まずは冒頭3秒とCTAだけを参考にしてください。"]


def _reference_avoid_points(reference_traits: dict[str, Any], self_traits: dict[str, Any]) -> list[str]:
    points = [
        "参考投稿の構成やテロップを丸写しせず、悩みの切り口・構成順・CTAだけを抽出してください。",
        "自アカウントのターゲットから外れるジャンルは、再生数が高くても優先度を下げてください。",
    ]
    reference_duration = [item for item, _ in reference_traits["duration_buckets"]]
    self_duration = [item for item, _ in self_traits["duration_buckets"]]
    if reference_duration and self_duration and reference_duration[0] != self_duration[0]:
        points.append(f"参考上位投稿の尺は「{reference_duration[0]}」が多い一方、自アカウント上位は「{self_duration[0]}」です。尺は急に寄せず、段階的に検証してください。")
    return points


def _reference_differentiation_points(reference_traits: dict[str, Any], self_traits: dict[str, Any]) -> list[str]:
    reference_hashtags = [item for item, _ in reference_traits["hashtags"]]
    self_hashtags = [item for item, _ in self_traits["hashtags"]]
    points = []
    if self_hashtags:
        points.append(f"自アカウントは「{safe_join(self_hashtags[:3])}」を軸に、参考アカウントより対象者を狭く見せると差別化しやすいです。")
    if reference_hashtags:
        points.append(f"参考側で多い「{safe_join(reference_hashtags[:3])}」は、汎用タグとして使いすぎず投稿内容に合うものだけ採用してください。")
    points.append("差別化は編集装飾より、誰のどの場面の悩みを解決するかを具体化する方が効果検証しやすいです。")
    return points


def _reference_evidence_lines(metrics: list[PostMetric]) -> list[str]:
    lines = []
    for metric in metrics:
        post = metric.post
        account_name = getattr(post, "account_name", DATA_INSUFFICIENT)
        views = post.views if post.views is not None else DATA_INSUFFICIENT
        lines.append(
            f"{account_name} / {post.title}: 再生数 {views}、冒頭「{post.hook or DATA_INSUFFICIENT}」、構成 {post.structure or DATA_INSUFFICIENT}"
        )
    return lines or ["データ不足"]


def _build_strategy(
    account: AccountProfile,
    summary: dict[str, Any],
    performance: dict[str, Any],
    habits: dict[str, Any],
    trend_analysis: dict[str, Any],
) -> dict[str, Any]:
    strongest_genres = [item for item, _ in performance["top_common"]["genres"]]
    weak_genres = [item for item, _ in performance["weak_common"]["genres"]]
    top_issue = "データ不足"
    if summary["post_count"] == 0:
        top_issue = "投稿データがないため、まず10本分の投稿実績を入力すること"
    elif summary["post_count"] < 10:
        top_issue = "投稿数が少なく、勝ち筋判断が暫定であること"
    elif habits["weekly_frequency"] is not None and habits["weekly_frequency"] < 3:
        top_issue = "検証に必要な投稿頻度が不足していること"
    else:
        top_issue = "伸びた投稿の型を次の10投稿で再現検証すること"

    first_priority = "次の10投稿では、伸びたジャンルと冒頭構成を固定し、CTAと保存理由だけを変えて検証してください。"
    if strongest_genres:
        first_priority = f"次の10投稿では「{strongest_genres[0]}」を主軸にし、冒頭3秒・CTA・保存理由を変えて検証してください。"

    return {
        "current_state": f"{account.genre}として運用中。数値は{summary['data_sufficiency']}です。",
        "biggest_issue": top_issue,
        "first_priority": first_priority,
        "positioning": f"{account.target_audience}に向けて、{account.genre}の実用情報を届けるアカウントとして一貫性を高める余地があります。",
        "strengths": _strategy_strengths(performance, trend_analysis),
        "weaknesses": _strategy_weaknesses(performance, habits),
        "grow_categories": strongest_genres or [account.genre],
        "drop_or_reduce_categories": weak_genres[:3] or ["データ不足"],
        "thirty_day_policy": "週3-5本で、勝ち筋ジャンルを増やすより、既存の伸びた型の再現性を検証する30日にしてください。",
    }


def _strategy_strengths(performance: dict[str, Any], trend_analysis: dict[str, Any]) -> list[str]:
    strengths = []
    top_genres = [item for item, _ in performance["top_common"]["genres"]]
    if top_genres:
        strengths.append(f"上位投稿に「{safe_join(top_genres)}」の共通点があります。")
    if trend_analysis["easy_to_apply"]:
        strengths.append("手動入力されたトレンドと既存投稿ジャンルに重なりがあります。")
    return strengths or ["強みを判断するには、投稿実績と投稿メモの追加が必要です。"]


def _strategy_weaknesses(performance: dict[str, Any], habits: dict[str, Any]) -> list[str]:
    weaknesses = []
    weak_genres = [item for item, _ in performance["weak_common"]["genres"]]
    if weak_genres:
        weaknesses.append(f"下位投稿に「{safe_join(weak_genres)}」が含まれています。テーマの見せ方を再設計してください。")
    if habits["cta_ratio"] is not None and habits["cta_ratio"] < 0.7:
        weaknesses.append("投稿ごとの役割とCTAが不足しています。")
    return weaknesses or ["弱みを判断するには、下位投稿のメモと冒頭3秒の入力が必要です。"]


def _generate_video_ideas(
    account: AccountProfile,
    performance: dict[str, Any],
    trend_analysis: dict[str, Any],
    competitors: list[dict[str, Any]],
) -> list[dict[str, str]]:
    main_genre = _first_or_default([item for item, _ in performance["top_common"]["genres"]], account.genre)
    trend_hooks = []
    trend_structures = []
    trend_sounds = []
    for item in trend_analysis["easy_to_apply"] + trend_analysis["used_trends"]:
        trend_hooks.extend(item.get("opening_hooks", []))
        trend_structures.extend(item.get("video_structures", []))
    for trend in trend_analysis["easy_to_apply"]:
        trend_sounds.extend(trend.get("matched_sounds", []))
    competitor_hooks = []
    for competitor in competitors:
        competitor_hooks.extend(_list_value(competitor.get("opening_hooks")))
    hooks = trend_hooks + competitor_hooks + [
        "これやってる人、損してるかも",
        "買う前にまずこれ試して",
        "一人暮らしで失敗しやすいこと",
    ]
    structures = trend_structures + [
        "悩み提示 > 3つの改善策 > 実例 > 保存促し",
        "NG行動 > 理由 > 代替案 > コメント誘導",
        "Before > 手順 > After > フォロー理由",
    ]
    sounds = trend_sounds + ["手動調査した流行音源", "既存上位投稿で使った音源"]
    themes = [
        "買ってよかったではなく買う前に試す収納術",
        "食費を減らす買い物前ルール",
        "洗濯・掃除のNG行動",
        "月末に見直す固定費",
        "玄関・冷蔵庫・デスクのBefore/After",
        "コメントで割れそうな節約判断",
        "保存したくなるチェックリスト",
        "失敗談から入る暮らし改善",
        "3分でできるリセット習慣",
        "初心者がやりがちな片付けミス",
        "フォロワーの悩みに答えるQ&A",
        "過去上位投稿の続編",
    ]
    ideas = []
    for index, theme in enumerate(themes[:12], start=1):
        ideas.append(
            {
                "number": str(index),
                "title": f"{theme}：{main_genre}編",
                "goal": "保存・コメント・フォロー転換のどれが伸びるかを検証する",
                "target": account.target_audience,
                "hook": hooks[(index - 1) % len(hooks)],
                "structure": structures[(index - 1) % len(structures)],
                "duration": "25-40秒",
                "sound": sounds[(index - 1) % len(sounds)],
                "caption": "悩みを1文で示し、各カットは12文字前後の短いテロップにする",
                "cta": "保存して次の買い物前に見返してください / あなたはどっち派？",
                "hypothesis": "冒頭で悩みを具体化し、最後に保存理由を置くと保存率とフォロー転換率が上がる可能性があります。",
                "success_kpi": "再生数中央値超え、保存率平均超え、フォロー転換率平均超え",
            }
        )
    return ideas


def _generate_operation_plan(
    account: AccountProfile,
    performance: dict[str, Any],
    trend_analysis: dict[str, Any],
) -> list[dict[str, str]]:
    main_genre = _first_or_default([item for item, _ in performance["top_common"]["genres"]], account.genre)
    trend_name = trend_analysis["easy_to_apply"][0]["name"] if trend_analysis["easy_to_apply"] else "手動入力したトレンド"
    return [
        {
            "week": "Week 1",
            "posts": "3-4本",
            "theme": "現状の勝ち筋確認",
            "genres": main_genre,
            "improvement": "上位投稿と同じジャンルで、冒頭3秒だけを変えた投稿を作る",
            "kpi": "再生数、完視聴率、平均視聴維持率",
        },
        {
            "week": "Week 2",
            "posts": "4-5本",
            "theme": "保存理由の検証",
            "genres": f"{main_genre} + チェックリスト型",
            "improvement": "最後に保存する理由を明示し、保存率を比較する",
            "kpi": "保存率、プロフィール遷移率、フォロー転換率",
        },
        {
            "week": "Week 3",
            "posts": "4-5本",
            "theme": "トレンド構成の取り込み",
            "genres": trend_name,
            "improvement": "流行構成を丸ごと真似ず、自分のジャンルに合う冒頭と編集テンポだけ取り入れる",
            "kpi": "再生数、シェア率、コメント率",
        },
        {
            "week": "Week 4",
            "posts": "4本",
            "theme": "再現性チェック",
            "genres": f"{main_genre}の上位2フォーマット",
            "improvement": "最も良かった2型を再投稿ではなく別テーマで再現する",
            "kpi": "中央値比、保存率、フォロー転換率、プロフィール遷移率",
        },
    ]


def _generate_kpi_design(summary: dict[str, Any]) -> dict[str, list[str]]:
    return {
        "primary": [
            "フォロー転換率: 趣味投稿から成長アカウントへ変える目的に直結するため最重要",
            "保存率: 実用系コンテンツとして価値が伝わっているかを見る",
        ],
        "secondary": [
            "完視聴率: 冒頭と構成の強さを見る",
            "平均視聴維持率: 尺が長すぎないかを見る",
            "コメント率: 共感・反論・質問の余白を見る",
            "プロフィール遷移率: アカウント導線の強さを見る",
        ],
        "per_post": [
            "再生数、いいね率、コメント率、保存率、シェア率、プロフィール遷移率、フォロー転換率、完視聴率",
        ],
        "weekly": [
            "投稿本数、ジャンル別中央値、冒頭フック別の完視聴率、CTA別の保存率",
        ],
        "monthly": [
            "フォロワー増加数、上位投稿の共通点、下位投稿の共通点、伸ばすカテゴリと減らすカテゴリ",
        ],
        "decision_rules": [
            f"再生数は中央値 {format_number(summary.get('median_views'))} を基準にし、中央値超えを一次成功とする",
            "保存率またはフォロー転換率が平均を超えた投稿は、同じ型で最低2本追加検証する",
            "3本続けて中央値を下回るテーマは、冒頭・対象者・保存理由のどれかを変更してから再検証する",
        ],
    }


def _generate_hypotheses(
    performance: dict[str, Any],
    habits: dict[str, Any],
    trend_analysis: dict[str, Any],
) -> list[dict[str, str]]:
    top_genre = _first_or_default([item for item, _ in performance["top_common"]["genres"]], "上位ジャンル")
    weak_genre = _first_or_default([item for item, _ in performance["weak_common"]["genres"]], "下位ジャンル")
    trend_name = trend_analysis["easy_to_apply"][0]["name"] if trend_analysis["easy_to_apply"] else "手動調査トレンド"
    return [
        {
            "priority": "高",
            "hypothesis": f"{top_genre}は保存する理由が明確なため、再生数と保存率が伸びやすい",
            "method": "同ジャンルで冒頭だけ違う投稿を3本作る",
            "posts_needed": "3本",
            "success": "3本中2本が中央値再生数と平均保存率を超える",
            "next_action": "勝ち型として週2本の定番枠にする",
        },
        {
            "priority": "高",
            "hypothesis": "CTAを明確にすると保存率またはコメント率が上がる",
            "method": "CTAあり/なしではなく、保存促し/質問誘導/フォロー理由の3種類で比較する",
            "posts_needed": "6本",
            "success": "CTA別に最も高いKPIが明確になる",
            "next_action": "投稿目的ごとにCTAテンプレートを固定する",
        },
        {
            "priority": "中",
            "hypothesis": f"{trend_name}の構成だけを取り入れると、既存ジャンルでも完視聴率が上がる",
            "method": "音源を無理に合わせず、冒頭と構成を合わせた投稿を3本作る",
            "posts_needed": "3本",
            "success": "完視聴率または平均視聴維持率が平均を超える",
            "next_action": "効果があった構成をテンプレート化する",
        },
        {
            "priority": "中",
            "hypothesis": f"{weak_genre}は対象者と見る理由を明確化すれば改善できる可能性がある",
            "method": "同テーマを悩み起点の冒頭に変えて2本再検証する",
            "posts_needed": "2本",
            "success": "過去同ジャンルの再生数を超える",
            "next_action": "改善しなければ投稿比率を下げる",
        },
        {
            "priority": "低",
            "hypothesis": "投稿時間帯を夜に寄せると初速が安定する可能性がある",
            "method": "同じ型の投稿を20時台と22時台で比較する",
            "posts_needed": "4本",
            "success": "片方の時間帯で中央値比が明確に高い",
            "next_action": "次月の標準投稿時間にする",
        },
    ]


def _generate_backlog() -> dict[str, list[str]]:
    return {
        "すぐやる": [
            "次の10投稿で検証する主ジャンルを1-2個に絞る",
            "各投稿に保存・コメント・フォローのどれを狙うかを設定する",
            "冒頭3秒、構成、CTA、投稿メモを必ず入力する",
        ],
        "次の10投稿で試す": [
            "NG行動3つ形式",
            "Before/Afterを冒頭に見せる形式",
            "保存用チェックリスト形式",
            "コメントが割れる質問CTA",
        ],
        "30日以内にやる": [
            "プロフィール文を、誰向け・何が得られるか・投稿頻度の3点で書き直す",
            "固定投稿を、アカウントの代表テーマ3本に整理する",
            "週次でKPIを見返す運用メモを作る",
        ],
        "余裕があればやる": [
            "TikTok Creative Centerの手動調査結果の取り込み",
            "Google Trendsとの比較",
            "YouTube Shorts / Instagram Reelsの参考情報取り込み",
            "投稿ネタ管理",
            "投稿カレンダー生成",
            "動画台本生成",
            "冒頭フック生成",
            "サムネイル文言生成",
            "過去レポートとの比較",
            "ダッシュボード化",
            "LLM API連携による定性分析強化",
        ],
        "やらない方がよい": [
            "自動ログイン、自動投稿、自動いいね、自動フォロー、自動コメント",
            "スクレイピングによる無断データ収集",
            "フォロワー購入や再生数水増し",
            "他人のコンテンツの無断転載",
            "根拠のない成功保証やバズ断定",
        ],
    }


def _list_value(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    return [part.strip() for part in str(value).replace("、", ",").split(",") if part.strip()]


def _first_or_default(values: list[str], default: str) -> str:
    return values[0] if values else default
