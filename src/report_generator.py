from __future__ import annotations

from pathlib import Path
from typing import Any

from models import PostMetric
from utils import DATA_INSUFFICIENT, format_bool, format_number, format_percent, safe_join


def generate_markdown_report(analysis: dict[str, Any]) -> str:
    account = analysis["account"]
    summary = analysis["summary"]
    performance = analysis["performance"]
    habits = analysis["habits"]
    trend_analysis = analysis["trend_analysis"]
    competitor_analysis = analysis["competitor_analysis"]
    strategy = analysis["strategy"]

    lines: list[str] = []
    lines.append("# TikTokアカウント分析レポート")
    lines.append("")
    lines.extend(_section_conclusion(strategy))
    lines.extend(_section_account(account, strategy, habits))
    lines.extend(_section_summary(summary))
    lines.extend(_section_top_posts(performance))
    lines.extend(_section_weak_posts(performance))
    lines.extend(_section_habits(habits))
    lines.extend(_section_trends(trend_analysis))
    lines.extend(_section_competitors(competitor_analysis))
    lines.extend(_section_profile(strategy, account))
    lines.extend(_section_video_ideas(analysis["video_ideas"]))
    lines.extend(_section_operation_plan(analysis["operation_plan"]))
    lines.extend(_section_kpi_design(analysis["kpi_design"]))
    lines.extend(_section_hypotheses(analysis["hypotheses"]))
    lines.extend(_section_backlog(analysis["backlog"]))
    lines.extend(_section_llm_analysis(analysis.get("llm_analysis")))
    return "\n".join(lines).rstrip() + "\n"


def write_markdown_report(analysis: dict[str, Any], output_path: str | Path) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(generate_markdown_report(analysis), encoding="utf-8")


def _section_conclusion(strategy: dict[str, Any]) -> list[str]:
    return [
        "## 1. 結論",
        f"- 現在のアカウントの状態: {strategy['current_state']}",
        f"- 最大の課題: {strategy['biggest_issue']}",
        f"- 最優先で改善すべきこと: {strategy['first_priority']}",
        f"- 今後30日間の方針: {strategy['thirty_day_policy']}",
        "",
    ]


def _section_account(account: dict[str, Any], strategy: dict[str, Any], habits: dict[str, Any]) -> list[str]:
    return [
        "## 2. アカウント概要",
        f"- ジャンル: {account['genre']}",
        f"- 想定ターゲット: {account['target_audience']}",
        f"- 現在の運用状況: 投稿頻度 {format_frequency(habits['weekly_frequency'])}、投稿可能頻度 {account['postable_frequency']}",
        f"- 目標: 現在 {format_number(account['current_followers'])} フォロワー / 目標 {format_number(account['target_followers'])} フォロワー",
        f"- 投稿頻度: {format_frequency(habits['weekly_frequency'])}",
        f"- 現在の強み: {safe_join(strategy['strengths'])}",
        f"- 現在の弱み: {safe_join(strategy['weaknesses'])}",
        f"- 顔出し: {format_bool(account['face_reveal'])} / 声出し: {format_bool(account['voice_available'])}",
        f"- 避けたい表現: {account['avoid_expressions']}",
        "",
    ]


def _section_summary(summary: dict[str, Any]) -> list[str]:
    return [
        "## 3. 投稿実績サマリー",
        f"- 投稿本数: {summary['post_count']}",
        f"- データ評価: {summary['data_sufficiency']}",
        f"- 平均再生数: {format_number(summary['average_views'])}",
        f"- 中央値再生数: {format_number(summary['median_views'])}",
        f"- 最大再生数: {format_number(summary['max_views'])}",
        f"- 欠損データ: {summary['data_quality_note']}",
        f"- 平均いいね率: {format_percent(summary['average_like_rate'])}",
        f"- 平均コメント率: {format_percent(summary['average_comment_rate'])}",
        f"- 平均保存率: {format_percent(summary['average_save_rate'])}",
        f"- 平均シェア率: {format_percent(summary['average_share_rate'])}",
        f"- 平均フォロー転換率: {format_percent(summary['average_follow_conversion_rate'])}",
        f"- 完視聴率の傾向: 平均 {format_percent(summary['average_completion_rate'])}",
        "",
    ]


def _section_top_posts(performance: dict[str, Any]) -> list[str]:
    traits = performance["top_common"]
    lines = [
        "## 4. 伸びた投稿の共通点",
        f"- テーマ: {_format_terms(traits['genres'])}",
        f"- 冒頭フック: {safe_join(traits['hooks'])}",
        f"- 動画尺: {_format_terms(traits['duration_buckets'])}",
        f"- 構成: {safe_join(traits['structures'])}",
        f"- 音源: {_format_terms(traits['sounds'])}",
        f"- ハッシュタグ: {_format_terms(traits['hashtags'])}",
        "- コメント欄の反応: コメント数や投稿メモから見ると、悩みが明確な投稿ほど反応が出ている可能性があります。",
        "- 伸びた理由の仮説:",
    ]
    lines.extend([f"  - {note}" for note in performance["quantitative_notes"]])
    lines.extend([f"  - {note}" for note in performance["qualitative_notes"]])
    lines.append("- 根拠となる投稿:")
    lines.extend([f"  - {line}" for line in performance["top_evidence"]] or ["  - データ不足"])
    lines.append("")
    return lines


def _section_weak_posts(performance: dict[str, Any]) -> list[str]:
    traits = performance["weak_common"]
    return [
        "## 5. 伸びなかった投稿の共通点",
        f"- テーマ: {_format_terms(traits['genres'])}",
        f"- 冒頭の弱さ: {safe_join(traits['hooks'])}",
        "- ターゲットの曖昧さ: 投稿タイトルやメモに誰向けかが出ていない投稿は、見る理由が弱くなる可能性があります。",
        f"- 動画尺: {_format_terms(traits['duration_buckets'])}",
        f"- 構成: {safe_join(traits['structures'])}",
        f"- 投稿タイミング: {_format_terms(traits['time_buckets'])}",
        f"- 改善仮説: {safe_join(performance['qualitative_notes'])}",
        f"- 根拠となる投稿: {safe_join(performance['weak_evidence'])}",
        "",
    ]


def _section_habits(habits: dict[str, Any]) -> list[str]:
    return [
        "## 6. 投稿習慣の改善点",
        f"- 投稿頻度: {format_frequency(habits['weekly_frequency'])}",
        f"- 投稿曜日: {_format_terms(habits['day_counts'])}",
        f"- 投稿時間: {_format_terms(habits['time_counts'])}",
        f"- テーマの偏り: {_format_terms(habits['genre_counts'])}",
        "- 検証不足: 投稿数が少ない場合や同じ型の再検証が少ない場合は、断定せず暫定仮説として扱ってください。",
        f"- 次に変えるべき運用ルール: {safe_join(habits['notes'])}",
        "",
    ]


def _section_trends(trend_analysis: dict[str, Any]) -> list[str]:
    lines = [
        "## 7. トレンド分析",
        "- 現在のTikTokで目立つトレンド:",
    ]
    if trend_analysis["used_trends"]:
        for trend in trend_analysis["used_trends"]:
            lines.append(f"  - {trend['name']}: {trend['growth_hypothesis']}")
    else:
        lines.append("  - データ不足")
    lines.append("- 自分のアカウントに取り入れやすいトレンド:")
    if trend_analysis["easy_to_apply"]:
        for trend in trend_analysis["easy_to_apply"]:
            lines.append(f"  - {trend['name']}: {trend['applicable_points']}")
    else:
        lines.append("  - データ不足")
    lines.append("- 取り入れない方がよいトレンド:")
    if trend_analysis["avoid_or_adapt"]:
        for trend in trend_analysis["avoid_or_adapt"]:
            lines.append(f"  - {trend['name']}: 音源やジャンルが一致しないため、構成だけ応用する方が安全です。")
    else:
        lines.append("  - 現時点では手動入力された全トレンドが既存ジャンルと一定程度重なっています。")
    lines.append(f"- 具体的な応用案: {safe_join(trend_analysis['notes'])}")
    lines.append("")
    return lines


def _section_competitors(competitor_analysis: dict[str, Any]) -> list[str]:
    post_comparison = competitor_analysis.get("post_comparison", {})
    lines = [
        "## 8. 競合・参考アカウント分析",
        "- 参考になるアカウント:",
    ]
    for item in competitor_analysis["takeaways"]:
        lines.append(f"  - {item['account_name']}: {item['winning_video_features']} ({item['url']})")
    if not competitor_analysis["takeaways"]:
        lines.append("  - データ不足")
    lines.append("- 真似すべき構成:")
    lines.extend([f"  - {item['video_structure']}" for item in competitor_analysis["takeaways"]] or ["  - データ不足"])
    lines.append("- 真似すべき冒頭フック:")
    hooks = [hook for item in competitor_analysis["takeaways"] for hook in item["opening_hooks"]]
    lines.append(f"  - {safe_join(hooks)}")
    lines.append("- 真似すべき投稿頻度:")
    lines.extend([f"  - {item['account_name']}: {item['posting_frequency']}" for item in competitor_analysis["takeaways"]] or ["  - データ不足"])
    lines.append(f"- 差別化すべきポイント: {safe_join(competitor_analysis['avoid_points'])}")
    lines.append("- 投稿単位の比較:")
    lines.append(f"  - {post_comparison.get('summary', 'データ不足')}")
    lines.append("- 参考投稿から取り入れるべき点:")
    lines.extend([f"  - {item}" for item in post_comparison.get("adopt_points", ["データ不足"])])
    lines.append("- 取り入れない方がよい点:")
    lines.extend([f"  - {item}" for item in post_comparison.get("avoid_points", ["データ不足"])])
    lines.append("- 自アカウントとして差別化すべき点:")
    lines.extend([f"  - {item}" for item in post_comparison.get("differentiation_points", ["データ不足"])])
    if post_comparison.get("accounts"):
        lines.append("- 参考アカウント別の投稿データ概要:")
        for account in post_comparison["accounts"]:
            lines.append(
                f"  - {account['account_name']}: 投稿{account['post_count']}本、平均再生数 {format_number(account['average_views'])}、主要ジャンル {_format_terms(account['top_genres'])}"
            )
    lines.append("- 根拠となる参考投稿:")
    lines.extend([f"  - {item}" for item in post_comparison.get("top_reference_posts", ["データ不足"])])
    lines.append("")
    return lines


def _section_profile(strategy: dict[str, Any], account: dict[str, Any]) -> list[str]:
    return [
        "## 9. プロフィール・導線改善",
        f"- プロフィール文の改善: 「誰向け」「何が得られるか」「投稿頻度」を1文ずつ入れ、{account['genre']}の実用アカウントだと分かるようにしてください。",
        "- アイコン・名前・固定投稿の改善: 名前にジャンルが伝わる語を入れ、固定投稿は上位ジャンル・自己紹介・保存価値の高い代表投稿に整理してください。",
        f"- フォローする理由の明確化: {strategy['positioning']}",
        "- 動画からプロフィールへの導線: 動画末尾で「同じ悩みの人向けに毎週投稿」と伝え、プロフィール確認の理由を作ってください。",
        "- プロフィールからフォローへの導線: 固定投稿とプロフィール文で、フォロー後に得られる継続価値を明確にしてください。",
        "",
    ]


def _section_video_ideas(video_ideas: list[dict[str, str]]) -> list[str]:
    lines = ["## 10. 次に作るべき動画案"]
    for idea in video_ideas:
        lines.extend(
            [
                f"### 動画案{idea['number']}",
                f"- タイトル: {idea['title']}",
                f"- 狙い: {idea['goal']}",
                f"- 想定ターゲット: {idea['target']}",
                f"- 冒頭3秒: {idea['hook']}",
                f"- 動画構成: {idea['structure']}",
                f"- 尺: {idea['duration']}",
                f"- 使用できそうな音源: {idea['sound']}",
                f"- テロップ案: {idea['caption']}",
                f"- CTA: {idea['cta']}",
                f"- 検証したい仮説: {idea['hypothesis']}",
                f"- 成功判定KPI: {idea['success_kpi']}",
                "",
            ]
        )
    return lines


def _section_operation_plan(operation_plan: list[dict[str, str]]) -> list[str]:
    lines = ["## 11. 30日間の運用プラン"]
    for week in operation_plan:
        lines.extend(
            [
                f"- {week['week']}:",
                f"  - 投稿本数: {week['posts']}",
                f"  - 検証テーマ: {week['theme']}",
                f"  - 投稿ジャンル: {week['genres']}",
                f"  - 改善ポイント: {week['improvement']}",
                f"  - 確認するKPI: {week['kpi']}",
            ]
        )
    lines.append("")
    return lines


def _section_kpi_design(kpi_design: dict[str, list[str]]) -> list[str]:
    return [
        "## 12. KPI設計",
        f"- 最重要KPI: {safe_join(kpi_design['primary'])}",
        f"- 補助KPI: {safe_join(kpi_design['secondary'])}",
        f"- 投稿ごとに見る指標: {safe_join(kpi_design['per_post'])}",
        f"- 週次で見る指標: {safe_join(kpi_design['weekly'])}",
        f"- 月次で見る指標: {safe_join(kpi_design['monthly'])}",
        f"- 判断基準: {safe_join(kpi_design['decision_rules'])}",
        "",
    ]


def _section_hypotheses(hypotheses: list[dict[str, str]]) -> list[str]:
    lines = [
        "## 13. 仮説検証リスト",
        "| 優先度 | 仮説 | 検証方法 | 必要投稿数 | 成功条件 | 次のアクション |",
        "|---|---|---|---|---|---|",
    ]
    for item in hypotheses:
        lines.append(
            f"| {item['priority']} | {item['hypothesis']} | {item['method']} | {item['posts_needed']} | {item['success']} | {item['next_action']} |"
        )
    lines.append("")
    return lines


def _section_backlog(backlog: dict[str, list[str]]) -> list[str]:
    lines = ["## 14. 改善バックログ"]
    for title, items in backlog.items():
        lines.append(f"### {title}")
        lines.extend([f"- {item}" for item in items])
        lines.append("")
    return lines


def _section_llm_analysis(llm_analysis: dict[str, Any] | None) -> list[str]:
    if not llm_analysis:
        llm_analysis = {
            "status": "未実行",
            "provider": "none",
            "model": None,
            "text": "外部LLM分析は未実行です。CLIから --llm-provider と --llm-model を指定すると追加できます。",
        }
    lines = [
        "## 15. 外部LLM定性分析（任意）",
        f"- 状態: {llm_analysis.get('status', '未実行')}",
        f"- Provider: {llm_analysis.get('provider', 'none')}",
        f"- Model: {llm_analysis.get('model') or '未指定'}",
        "",
        str(llm_analysis.get("text") or "データ不足"),
        "",
    ]
    return lines


def _format_terms(items: list[tuple[str, int]] | list[str]) -> str:
    if not items:
        return DATA_INSUFFICIENT
    formatted = []
    for item in items:
        if isinstance(item, tuple):
            formatted.append(f"{item[0]}({item[1]})")
        else:
            formatted.append(str(item))
    return "、".join(formatted)


def format_frequency(value: float | None) -> str:
    if value is None:
        return DATA_INSUFFICIENT
    return f"週約{value:.1f}本"
