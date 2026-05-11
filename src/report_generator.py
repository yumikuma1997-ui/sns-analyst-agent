from __future__ import annotations

from pathlib import Path
from typing import Any

from confidence import confidence_description
from utils import DATA_INSUFFICIENT, format_bool, format_number, format_percent, safe_join


def write_markdown_report(analysis: dict[str, Any], output_path: str | Path) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(generate_markdown_report(analysis), encoding="utf-8")


def generate_markdown_report(analysis: dict[str, Any]) -> str:
    lines: list[str] = ["# TikTokアカウント分析レポート", ""]
    _executive_summary(lines, analysis)
    _section_0(lines, analysis)
    _section_1(lines, analysis)
    _section_2(lines, analysis)
    _section_3(lines, analysis)
    _section_4(lines, analysis)
    _section_5(lines, analysis)
    _section_6(lines, analysis)
    _section_7(lines, analysis)
    _section_8(lines, analysis)
    _section_9(lines, analysis)
    _section_10(lines, analysis)
    _section_11(lines, analysis)
    _section_12(lines, analysis)
    _section_13(lines, analysis)
    _section_14(lines, analysis)
    _section_15(lines, analysis)
    _section_16(lines, analysis)
    _section_17(lines, analysis)
    _section_18(lines, analysis)
    return "\n".join(lines).rstrip() + "\n"


def _executive_summary(lines: list[str], analysis: dict[str, Any]) -> None:
    summary = analysis["executive_summary"]
    scope = analysis["data_scope"]
    lines.extend(
        [
            "## Executive Summary",
            f"- APIで言える事実: {summary['api_fact']}",
            f"- API集計信頼度: {scope['api_aggregation_confidence']}（{confidence_description(scope['api_aggregation_confidence'])}）",
            f"- 戦略提案信頼度: {scope['strategy_recommendation_confidence']}（{confidence_description(scope['strategy_recommendation_confidence'])}）",
            f"- 最大の不足: {summary['biggest_gap']}",
            f"- 次のアクション: {summary['next_action']}",
            "",
        ]
    )


def _section_0(lines: list[str], analysis: dict[str, Any]) -> None:
    scope = analysis["data_scope"]
    lines.extend(
        [
            "## 0. データ取得・分析範囲",
            f"- 使用データ一覧: API投稿 {scope['api_post_count']}本 / 手入力インサイト {scope['manual_insight_count']}件 / クリエイティブメモ {scope['creative_note_count']}件 / トレンド調査 {scope['trend_research_count']}件 / 競合・参考投稿 {scope['competitor_post_count']}件",
            f"- API取得データ: {safe_join(scope['api_fields'])}",
            "- 手入力インサイト: manual_insights.csv の保存数、完視聴率、平均視聴時間、流入元など",
            "- 手入力クリエイティブメモ: creative_notes.csv の冒頭3秒、動画構成、CTA、PR有無など",
            "- トレンド調査データ: trend_research.csv に手動調査したCreative Center / Google Trends等の結果のみ",
            "- 競合・参考アカウントデータ: competitor_posts.csv。取り入れるのはテーマではなく型のみです。",
            f"- 今回取れていない指標: {safe_join(scope['not_available_via_basic_api'])}",
            "- APIでは通常取れないため手入力が必要な指標: 保存率、プロフィール遷移率、フォロー転換率、完視聴率、平均視聴維持率、流入元、冒頭3秒、動画構成、CTA",
            f"- API集計信頼度: {scope['api_aggregation_confidence']}",
            f"- 戦略提案信頼度: {scope['strategy_recommendation_confidence']}",
            "",
        ]
    )


def _section_1(lines: list[str], analysis: dict[str, Any]) -> None:
    summary = analysis["summaries"]["all"]
    scope = analysis["data_scope"]
    missing = [row["metric"] for row in analysis["missing_data"] if row["status"] == "未入力"]
    lines.extend(
        [
            "## 1. 結論",
            f"- 現在のアカウント状態: API上は{format_number(summary['post_count'])}本を分析対象にできます。中央値再生数は{format_number(summary['median_views'])}です。",
            "- 今回の分析で確実に言えること: 再生数、いいね率、コメント率、シェア率、投稿頻度、投稿間隔、動画尺分類はAPI取得データで確認できます。",
            f"- データ不足でまだ言えないこと: {safe_join(missing[:10])}",
            "- 最優先で改善すべきこと: 高再生・美容本流・PR候補の投稿から順にmanual_insightsとcreative_notesを入力してください。",
            "- 次の10投稿で検証すべきこと: 買う前チェック、正直レビュー、比較、使い切り、対象者分岐を分けて検証してください。",
            f"- 今後30日間の方針: API集計は{scope['api_aggregation_confidence']}、戦略提案は{scope['strategy_recommendation_confidence']}として扱い、平均値だけでなく中央値・直近値・バズ除外値を見ます。",
            "",
        ]
    )


def _section_2(lines: list[str], analysis: dict[str, Any]) -> None:
    account = analysis["account"]
    habits = analysis["habits"]
    current_frequency = habits["frequencies"]["全期間"]["weekly_frequency"]
    lines.extend(
        [
            "## 2. アカウント概要",
            f"- ジャンル: {account['genre']}",
            f"- 想定ターゲット: {account['target_audience']}",
            f"- 現在のフォロワー数: {format_number(account['current_followers'])}",
            f"- 目標フォロワー数: {format_number(account['target_followers'])}",
            f"- 投稿可能頻度: {account['postable_frequency']}",
            f"- 現在の投稿頻度: {_format_frequency(current_frequency)}",
            f"- 顔出し可否: {format_bool(account['face_reveal'])}",
            f"- 声出し可否: {format_bool(account['voice_available'])}",
            f"- 避けたい表現: {account['avoid_expressions']}",
            "",
        ]
    )


def _section_3(lines: list[str], analysis: dict[str, Any]) -> None:
    summary = analysis["summaries"]["all"]
    lines.extend(
        [
            "## 3. API取得指標サマリー",
            _confidence_line(summary),
            f"- 投稿本数: {format_number(summary['post_count'])}",
            f"- 平均再生数: {format_number(summary['average_views'])}",
            f"- 中央値再生数: {format_number(summary['median_views'])}",
            f"- 最大再生数: {format_number(summary['max_views'])}",
            f"- 最小再生数: {format_number(summary['min_views'])}",
            f"- 上位10%除外平均: {format_number(summary['top_10_excluded_average'])}",
            f"- 直近10投稿中央値: {format_number(summary['recent_10_median'])}",
            f"- 直近30日投稿数: {format_number(summary['recent_30_count'])}",
            f"- 直近30日中央値: {format_number(summary['recent_30_median'])}",
            f"- 平均いいね率: {format_percent(summary['average_like_rate'])}",
            f"- 平均コメント率: {format_percent(summary['average_comment_rate'])}",
            f"- 平均シェア率: {format_percent(summary['average_share_rate'])}",
            f"- 投稿曜日: {_format_pairs(summary['day_counts'])}",
            f"- 投稿時間帯: {_format_pairs(summary['time_buckets'])}",
            f"- 動画尺分類: {_format_pairs(summary['duration_buckets'])}",
            "",
        ]
    )


def _section_4(lines: list[str], analysis: dict[str, Any]) -> None:
    lines.extend(["## 4. 手入力が必要な不足指標", "| 指標 | 状態 | 不足理由 | 入力先 | 分析できるようになること |", "|---|---|---|---|---|"])
    for row in analysis["missing_data"]:
        lines.append(f"| {row['metric']} | {row['status']} | {row['reason']} | {row['input']} | {row['benefit']} |")
    lines.extend(["", "### 次に入力すべきデータ", "優先入力対象の投稿10本です。まずこの順でmanual_insightsとcreative_notesを埋めると、戦略提案信頼度を上げやすくなります。", "| video_id | タイトル | 投稿日 | 再生数 | カテゴリ | PR判定 | 不足 | 理由 |", "|---|---|---|---:|---|---|---|---|"])
    for row in analysis["priority_input_targets"]:
        lines.append(
            f"| {row['video_id']} | {_escape(row['title'])} | {row['posted_at']} | {format_number(row['view_count'])} | {row['category']} | {row['pr_status']} | {safe_join(row['missing'])} | {row['reason']} |"
        )
    if not analysis["priority_input_targets"]:
        lines.append("| データ不足 | 追加入力対象を判定できません |  |  |  |  |  |  |")
    lines.extend(
        [
            "",
            f"- creative_notes の最小入力項目: {safe_join(analysis['creative_minimum_fields'])}",
            f"- manual_insights の最小入力項目: {safe_join(analysis['manual_insight_minimum_fields'])}",
            "",
        ]
    )


def _section_5(lines: list[str], analysis: dict[str, Any]) -> None:
    viral = analysis["viral"]
    buzz_excluded = analysis["summaries"]["buzz_excluded"]
    lines.extend(
        [
            "## 5. 外れ値・バズ投稿の扱い",
            f"- 信頼度: {viral['confidence']}",
            "- バズ投稿候補:",
        ]
    )
    lines.extend(_post_lines(viral["viral_posts"], include_reason=True) or ["  - データ不足"])
    lines.extend(
        [
            f"- バズ投稿を除いた実態値: 中央値 {format_number(buzz_excluded['median_views'])} / 上位10%除外平均 {format_number(buzz_excluded['top_10_excluded_average'])}",
            "- 美容アカウントとして再現可能なバズ:",
        ]
    )
    lines.extend(_post_lines(viral["reproducible"]) or ["  - 現時点では判定不可。同じ型の再現投稿が2本以上必要です。"])
    lines.append("- 再現可能性未判定の勝ち筋候補:")
    lines.extend(_post_lines(viral["unjudged_winning_candidates"]) or ["  - 該当なし"])
    lines.append("- 再現可能性が低いバズ:")
    lines.extend(_post_lines(viral["low_reproducibility"]) or ["  - 該当なし"])
    lines.append("- 今後の分析から分離すべき投稿: 非美容カテゴリ、creative_notes未入力の外れ値、単発で再現性が確認できない投稿")
    lines.append("")


def _section_6(lines: list[str], analysis: dict[str, Any]) -> None:
    beauty = analysis["beauty_analysis"]
    summary = beauty["core_summary"]
    lines.extend(
        [
            "## 6. 美容・コスメ本流投稿の分析",
            f"- 信頼度: {beauty['confidence']}（{confidence_description(beauty['confidence'])}）",
            f"- beauty_core 投稿数: {format_number(beauty['core_count'])}",
            f"- 中央値再生数: {format_number(summary['median_views'])}",
            "- 上位投稿:",
        ]
    )
    lines.extend(_post_lines(beauty["top_core"]) or ["  - データ不足"])
    lines.append("- 下位投稿:")
    lines.extend(_post_lines(beauty["weak_core"]) or ["  - データ不足"])
    lines.append("- beauty_core 判定の根拠:")
    for row in beauty["category_evidence"][:10]:
        lines.append(
            f"  - {row['video_id']} / {row['category']} / confidence {row['confidence']} / source {row['source']} / 根拠: {safe_join(row['reasons'])}"
        )
    lines.append("- 再現可能性未判定の勝ち筋候補:")
    lines.extend(_post_lines(beauty["winning_candidates_unjudged"]) or ["  - データ不足"])
    lines.extend([f"- データ不足点: {beauty['missing']}", ""])


def _section_7(lines: list[str], analysis: dict[str, Any]) -> None:
    pr = analysis["pr_analysis"]
    lines.extend(
        [
            "## 7. PR投稿 / 非PR投稿の比較",
            f"- 信頼度: {pr['confidence']}",
            f"- PR投稿候補の判定: {_format_pairs(pr['status_counts'])}",
            "| 範囲 | 対象投稿数 | PR中央値再生数 | 非PR中央値再生数 | PR平均いいね率 | 非PR平均いいね率 | PR平均コメント率 | 非PR平均コメント率 |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for label, scope in pr["scopes"].items():
        pr_summary = scope["pr_summary"]
        non_pr_summary = scope["non_pr_summary"]
        lines.append(
            f"| {label} | {format_number(scope['post_count'])} | {format_number(pr_summary['median_views'])} | {format_number(non_pr_summary['median_views'])} | {format_percent(pr_summary['average_like_rate'])} | {format_percent(non_pr_summary['average_like_rate'])} | {format_percent(pr_summary['average_comment_rate'])} | {format_percent(non_pr_summary['average_comment_rate'])} |"
        )
    lines.extend(
        [
            "- PR投稿で弱くなりやすい点: 商品訴求だけになると、視聴者の不安解消や保存理由が弱くなる可能性があります。",
            "- PR投稿で改善すべき見せ方: PR表記、良い点、微妙な点、向く人/向かない人を分けて出してください。",
            "- 注意: 薬機法・景表法・PR表記不足に注意してください。法的判断はこのツールの範囲外です。",
            "",
        ]
    )


def _section_8(lines: list[str], analysis: dict[str, Any]) -> None:
    habits = analysis["habits"]
    lines.extend(
        [
            "## 8. 投稿習慣分析",
            f"- 信頼度: {habits['confidence']}",
            "| 期間 | 投稿本数 | 週あたり投稿頻度 |",
            "|---|---:|---:|",
        ]
    )
    for label, value in habits["frequencies"].items():
        lines.append(f"| {label} | {format_number(value['post_count'])} | {_format_frequency(value['weekly_frequency'])} |")
    lines.extend(
        [
            f"- 投稿間隔: 平均 {format_number(habits['average_post_interval_days'])} 日",
            f"- 最大投稿間隔: {format_number(habits['max_post_interval_days'])} 日",
            f"- 投稿曜日: {_format_pairs(habits['day_counts'])}",
            f"- 投稿時間帯: {_format_pairs(habits['time_buckets'])}",
            "- 継続性: 直近30日と直近90日の頻度差を見て、検証サイクルが途切れていないか確認してください。",
            "- 次に変えるべき運用ルール: 次の30日は週3-4本を目安に、同じ検証型を最低2本ずつ出してください。",
            "",
        ]
    )


def _section_9(lines: list[str], analysis: dict[str, Any]) -> None:
    hashtags = analysis["hashtags"]
    groups = hashtags["groups"]
    lines.extend(
        [
            "## 9. ハッシュタグ・キャプション分析",
            f"- 信頼度: {hashtags['confidence']}",
            f"- 出現1回のタグ（単発。戦略判断には使わない）: {_format_tag_items(groups['single'])}",
            f"- 汎用タグ: {_format_tag_items(groups['generic'])}",
            f"- PR開示タグ: {_format_tag_items(groups['pr_disclosure'])}",
            f"- 検証候補タグ（2-3回）: {_format_tag_items(groups['test_candidates'])}",
            f"- 傾向候補タグ（4回以上）: {_format_tag_items(groups['trend_candidates'])}",
            f"- 有望タグ候補: {_format_tag_items(groups['promising_candidates'])}",
            f"- キャプション傾向: {safe_join(hashtags['caption_notes'])}",
            "- 注意点: #PR と #ad は開示目的のタグであり、伸びるタグや勝ち筋として扱いません。",
            "",
        ]
    )


def _section_10(lines: list[str], analysis: dict[str, Any]) -> None:
    creative = analysis["creative_analysis"]
    lines.extend(["## 10. クリエイティブ分析", f"- 信頼度: {creative['confidence']}"])
    if not creative["available"]:
        lines.extend(
            [
                f"- 状態: {creative['message']}",
                f"- 入力すべき項目: {safe_join(creative['required_fields'])}",
                "",
            ]
        )
        return
    lines.extend(
        [
            f"- 冒頭3秒 / hook_type: {_format_pairs(creative['hook_types'])}",
            f"- video_structure: {_format_pairs(creative['structures'])}",
            f"- CTA: {_format_pairs(creative['cta_types'])}",
            f"- テロップ密度: {_format_pairs(creative['text_density'])}",
            "- 伸びた投稿との関係: creative_notesがある投稿だけで暫定比較しています。未入力投稿は判断に含めません。",
            "",
        ]
    )


def _section_11(lines: list[str], analysis: dict[str, Any]) -> None:
    trend = analysis["trend_analysis"]
    lines.extend(["## 11. トレンド分析", f"- 信頼度: {trend['confidence']}"])
    if not trend["available"]:
        lines.extend([f"- 状態: {trend['message']}", f"- 手動調査すべき項目: {safe_join(trend['manual_research_items'])}", ""])
        return
    lines.append("- 取り入れやすいトレンド:")
    for item in trend["usable"]:
        lines.append(f"  - {item.trend_name}: {item.adaptation_idea or item.reason}")
    lines.append("- 取り入れない方がよいトレンド:")
    for item in trend["avoid"]:
        lines.append(f"  - {item.trend_name}: {item.reason}")
    lines.extend(["- 音源方針: trend_researchで美容領域に合うものだけを採用してください。", "- 注意点: トレンドは自動取得せず、手動調査結果のみを使います。", ""])


def _section_12(lines: list[str], analysis: dict[str, Any]) -> None:
    competitors = analysis["competitor_analysis"]
    lines.extend(["## 12. 参考アカウント分析", f"- 信頼度: {competitors['confidence']}"])
    if not competitors["available"]:
        lines.extend([f"- 状態: {competitors['message']}", ""])
        return
    lines.extend(
        [
            f"- 冒頭フック構造: {_format_pairs(competitors['hook_types'])}",
            f"- 動画構成: {_format_pairs(competitors['structures'])}",
            f"- CTAパターン: {_format_pairs(competitors['cta_types'])}",
            f"- 尺: {_format_pairs(competitors['durations'])}",
            "- 自アカウントへの変換案: 参考テーマではなく、損失回避フック・比較構成・保存CTAなどの型だけを美容テーマへ変換してください。",
            f"- コピーしてはいけない点: {competitors['copy_guardrail']}",
            "",
        ]
    )


def _section_13(lines: list[str], analysis: dict[str, Any]) -> None:
    account = analysis["account"]
    lines.extend(
        [
            "## 13. プロフィール・導線改善",
            "- 現在のプロフィール改善点: 誰向けに、何を正直にレビューするアカウントかを1文目で明確にしてください。",
            f"- 誰向けか: {account['target_audience']}",
            "- 何が得られるか: 買う前に失敗しにくくなる比較・正直レビュー・注意点。",
            f"- 投稿頻度: {account['postable_frequency']}を目標に、同じ検証型を複数本出してください。",
            "- 固定投稿: 初見向けに、代表的な正直レビュー、買う前チェック、プロフィール説明の3本を候補にしてください。",
            "- フォローする理由: 新作やPRでも良い点・微妙な点を分けて見られることを明記してください。",
            "- 動画末尾からプロフィールへの導線: “他の比較もプロフィールにまとめています”のように、視聴後の次行動を作ってください。",
            "",
        ]
    )


def _section_14(lines: list[str], analysis: dict[str, Any]) -> None:
    lines.append("## 14. 次に作るべき動画案")
    for idea in analysis["video_ideas"]:
        lines.extend(
            [
                f"### 動画案{idea['number']}",
                f"- タイトル: {idea['title']}",
                f"- 検証型: {idea['validation_type']}",
                f"- 狙い: {idea['goal']}",
                f"- 想定ターゲット: {idea['target']}",
                f"- 冒頭3秒: {idea['hook']}",
                f"- 動画構成: {idea['structure']}",
                f"- 尺: {idea['duration']}",
                f"- 使用できそうな音源または音源方針: {idea['sound']}",
                f"- テロップ案: {idea['caption']}",
                f"- CTA: {idea['cta']}",
                f"- 検証したい仮説: {idea['hypothesis']}",
                f"- 成功判定KPI: {idea['success_kpi']}",
                f"- 季節性: {idea['seasonality']}",
                f"- 信頼度: {idea['confidence']}",
                f"- 注意点: {idea['note']}",
                "- 元にした根拠データ:",
            ]
        )
        if idea["evidence_posts"]:
            for evidence in idea["evidence_posts"]:
                lines.append(
                    f"  - video_id={evidence['video_id']} / title={evidence['title']} / category={evidence['category']} / views={format_number(evidence['view_count'])} / PR={evidence['pr_status']} / posted_at={evidence['posted_at']} / duration={format_number(evidence['duration'])}秒"
                )
        else:
            lines.append("  - データ不足。beauty_coreの上位投稿を入力してください。")
        if idea["trend_evidence"]:
            lines.append(f"  - trend_research: {safe_join(idea['trend_evidence'])}")
        if idea["competitor_pattern_evidence"]:
            lines.append(f"  - competitor pattern: {safe_join(idea['competitor_pattern_evidence'])}")
        lines.append("")


def _section_15(lines: list[str], analysis: dict[str, Any]) -> None:
    lines.append("## 15. 30日間の運用プラン")
    for week in analysis["operation_plan"]:
        lines.extend(
            [
                f"- {week['week']}",
                f"  - 投稿本数: {week['posts']}",
                f"  - 検証テーマ: {week['theme']}",
                f"  - 投稿ジャンル: {week['genres']}",
                f"  - 改善ポイント: {week['improvement']}",
                f"  - 確認するKPI: {week['kpi']}",
                f"  - 必要な手入力データ: {week['manual_data']}",
            ]
        )
    lines.append("")


def _section_16(lines: list[str], analysis: dict[str, Any]) -> None:
    kpi = analysis["kpi_design"]
    lines.extend(
        [
            "## 16. KPI設計",
            f"- APIだけで見られるKPI: {safe_join(kpi['api_only'])}",
            f"- 手入力後に見られるKPI: {safe_join(kpi['manual_required'])}",
            "",
        ]
    )


def _section_17(lines: list[str], analysis: dict[str, Any]) -> None:
    lines.extend(
        [
            "## 17. 仮説検証リスト",
            "| 優先度 | 仮説 | 必要データ | 検証方法 | 必要投稿数 | 成功条件 | 信頼度 | 次のアクション |",
            "|---|---|---|---|---|---|---|---|",
        ]
    )
    for row in analysis["hypotheses"]:
        lines.append(
            f"| {row['priority']} | {row['hypothesis']} | {row['data']} | {row['method']} | {row['posts']} | {row['success']} | {row['confidence']} | {row['action']} |"
        )
    lines.append("")


def _section_18(lines: list[str], analysis: dict[str, Any]) -> None:
    backlog = analysis["backlog"]
    lines.append("## 18. 改善バックログ")
    for title, items in backlog.items():
        lines.append(f"### {title}")
        for item in items:
            lines.append(f"- {item}")
    lines.append("")


def _confidence_line(summary: dict[str, Any]) -> str:
    level = summary.get("confidence", "信頼度D")
    return f"- 信頼度: {level}（{confidence_description(level)}）"


def _format_frequency(value: float | None) -> str:
    if value is None:
        return DATA_INSUFFICIENT
    return f"週{value:.1f}本"


def _format_pairs(items: list[tuple[Any, int]]) -> str:
    if not items:
        return DATA_INSUFFICIENT
    return "、".join(f"{key}:{value}" for key, value in items)


def _format_tag_items(items: list[dict[str, Any]]) -> str:
    if not items:
        return DATA_INSUFFICIENT
    return "、".join(f"{item['tag']}({item['count']}回/中央値超え{item['above_median_count']}回)" for item in items)


def _post_lines(posts: list[dict[str, Any]], include_reason: bool = False) -> list[str]:
    lines = []
    for row in posts:
        reason = ""
        if include_reason and row.get("viral_reasons"):
            reason = f" / 理由: {safe_join(row['viral_reasons'])}"
        lines.append(
            f"  - {row.get('video_id') or 'unknown'} / {row.get('title') or '無題'} / {format_number(row.get('view_count'))}再生 / {row.get('strategy_category')} / PR:{row.get('pr_status')}{reason}"
        )
    return lines


def _escape(value: Any) -> str:
    return str(value or "").replace("|", "\\|")
