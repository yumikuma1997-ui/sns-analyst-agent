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


def _section_0(lines: list[str], analysis: dict[str, Any]) -> None:
    scope = analysis["data_scope"]
    input_files = analysis.get("input_files", {})
    competitor_note = ""
    if "sample" in str(input_files.get("competitor_posts", "")):
        competitor_note = "（現在はサンプルファイルのため、実アカウント判断には使いすぎないでください）"
    lines.extend(
        [
            "## 0. データ取得・分析範囲",
            f"- 使用データ一覧: API投稿 {scope['api_post_count']}本 / 手入力インサイト {scope['manual_insight_count']}件 / クリエイティブメモ {scope['creative_note_count']}件 / トレンド調査 {scope['trend_research_count']}件 / 参考投稿 {scope['competitor_post_count']}件",
            f"- API取得データ: {safe_join(scope['api_fields'])}",
            "- 手入力インサイト: manual_insights.csv に保存数、完視聴率、平均視聴時間、流入元などを転記",
            "- 手入力クリエイティブメモ: creative_notes.csv に冒頭3秒、構成、CTA、PR有無などを記録",
            "- トレンド調査データ: trend_research.csv。Creative CenterやGoogle Trendsの手動調査結果のみ使用",
            f"- 競合・参考アカウントデータ: competitor_posts.csv。型だけを参考にし、テーマや台本はコピーしない{competitor_note}",
            f"- 今回取れていない指標: {safe_join(scope['not_available_via_basic_api'])}",
            "- APIでは通常取れないため手入力が必要な指標: 保存数、保存率、プロフィールアクセス数、フォロー転換率、完視聴率、平均視聴時間、流入元、視聴者属性、冒頭3秒、動画構成、CTA、PR有無",
            f"- レポート全体の信頼度: {scope['overall_confidence']}（{confidence_description(scope['overall_confidence'])}）",
            "",
        ]
    )


def _section_1(lines: list[str], analysis: dict[str, Any]) -> None:
    summary = analysis["summaries"]["all"]
    missing = [row["metric"] for row in analysis["missing_data"] if row["status"] == "未入力"]
    partial = [row["metric"] for row in analysis["missing_data"] if row["status"] in {"一部入力あり", "自動推定のみ"}]
    not_yet_clear = missing[:8] or partial[:8]
    lines.extend(
        [
            "## 1. 結論",
            f"- 現在のアカウント状態: API上は{format_number(summary['post_count'])}本の投稿を分析対象にできます。中央値再生数は{format_number(summary['median_views'])}です。",
            "- 今回の分析で確実に言えること: 再生数、いいね率、コメント率、シェア率、投稿頻度、投稿間隔、動画尺は公式API取得データだけで確認できます。",
            f"- データ不足でまだ言えないこと: {safe_join(not_yet_clear)}。これらはAPIでは通常取れない、または全投稿で入力が揃っていないため、手入力後に判断してください。",
            "- 最優先で改善すべきこと: 次の10投稿では、美容・コスメ本流の投稿だけを対象に、冒頭3秒、動画構成、CTA、PR有無をcreative_notes.csvへ記録してください。",
            "- 次の10投稿で検証すべきこと: 買う前チェック、正直レビュー、比較、使い切りレビューを美容領域に限定して検証してください。",
            "- 今後30日間の方針: 平均値ではなく中央値、直近10投稿中央値、外れ値除外値を見ながら、PR/非PRと美容本流/非美容を分けて評価します。",
            "",
        ]
    )


def _section_2(lines: list[str], analysis: dict[str, Any]) -> None:
    account = analysis["account"]
    habits = analysis["habits"]
    lines.extend(
        [
            "## 2. アカウント概要",
            f"- ジャンル: {account['genre']}",
            f"- 想定ターゲット: {account['target_audience']}",
            f"- 現在のフォロワー数: {format_number(account['current_followers'])}",
            f"- 目標フォロワー数: {format_number(account['target_followers'])}",
            f"- 投稿可能頻度: {account['postable_frequency']}",
            f"- 現在の投稿頻度: {_format_frequency(habits['weekly_frequency'])}",
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
    lines.append("")


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
    lines.extend(_post_lines(viral["reproducible"]) or ["  - 現時点では判断不可。beauty_core/beauty_adjacent、creative_notes、同型2本以上が揃っていません。"])
    lines.append("- 再現可能性が低いバズ:")
    lines.extend(_post_lines(viral["low_reproducibility"]) or ["  - データ不足"])
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
    lines.extend(
        [
            "- 共通点: creative_notes.csvが入力されている投稿だけで冒頭・構成・CTAを比較します。未入力の場合は共通点を断定しません。",
            f"- データ不足点: {beauty['missing']}",
            "",
        ]
    )


def _section_7(lines: list[str], analysis: dict[str, Any]) -> None:
    pr = analysis["pr_analysis"]
    lines.extend(
        [
            "## 7. PR投稿 / 非PR投稿の比較",
            f"- 信頼度: {pr['confidence']}",
            f"- PR投稿候補の判定: {_format_pairs(pr['status_counts'])}",
            f"- PR投稿の中央値再生数: {format_number(pr['pr_summary']['median_views'])}",
            f"- 非PR投稿の中央値再生数: {format_number(pr['non_pr_summary']['median_views'])}",
            f"- PR投稿の平均いいね率: {format_percent(pr['pr_summary']['average_like_rate'])}",
            f"- 非PR投稿の平均いいね率: {format_percent(pr['non_pr_summary']['average_like_rate'])}",
            "- PR投稿で弱くなりやすい点: 商品訴求だけになると視聴者の不安解消や保存理由が弱くなる可能性があります。ただしcreative_notes未入力時は断定しません。",
            "- PR投稿で改善すべき見せ方: 良い点だけでなく、向いている人・向かない人、注意点、比較対象を入れてください。",
            "- 注意: 薬機法・景表法・PR表記不足に注意してください。法的判定はこのツールの範囲外です。",
            "",
        ]
    )


def _section_8(lines: list[str], analysis: dict[str, Any]) -> None:
    habits = analysis["habits"]
    lines.extend(
        [
            "## 8. 投稿習慣分析",
            f"- 信頼度: {habits['confidence']}",
            f"- 投稿頻度: {_format_frequency(habits['weekly_frequency'])}",
            f"- 投稿間隔: 平均 {format_number(habits['average_post_interval_days'])} 日",
            f"- 最大投稿間隔: {format_number(habits['max_post_interval_days'])} 日",
            f"- 投稿曜日: {_format_pairs(habits['day_counts'])}",
            f"- 投稿時間帯: {_format_pairs(habits['time_buckets'])}",
            "- 継続性: 投稿間隔が長い場合、直近10投稿中央値の検証速度が落ちます。",
            "- 次に変えるべき運用ルール: 次の30日は週3〜5本を目安に、同じ型を2本以上ずつ検証してください。",
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
            f"- 出現1回のハッシュタグ: {_format_tag_items(groups['single'][:10])}。単発のため戦略判断には使いません。",
            f"- 汎用タグ: {_format_tag_items(groups['generic'])}。戦略軸にはしません。",
            f"- 検証候補タグ: {_format_tag_items(groups['test_candidates'])}",
            f"- 傾向候補タグ: {_format_tag_items(groups['trend_candidates'])}",
            f"- 有望タグ候補: {_format_tag_items(groups['promising_candidates'])}",
            "- 戦略判断に使わないタグ: 出現1回のタグ、汎用タグ、動画内容と関係が薄いタグ",
            f"- キャプション傾向: {safe_join(hashtags['caption_notes'])}",
            "- 注意点: ハッシュタグは補助指標です。1回だけ出たタグを軸や勝ちパターンとして扱いません。",
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
                "- 伸びた投稿との関係: 現時点では判断不可。追加でcreative_notes.csvを入力してください。",
                "",
            ]
        )
        return
    lines.extend(
        [
            f"- 冒頭3秒 / hook_type: {_format_pairs(creative['hook_types'])}",
            f"- video_structure: {_format_pairs(creative['structures'])}",
            f"- CTA: {_format_pairs(creative['cta_types'])}",
            "- 顔出し: creative_notes.csvのface_visible入力後に比較",
            "- 声出し: creative_notes.csvのvoiceover入力後に比較",
            f"- テロップ密度: {_format_pairs(creative['text_density'])}",
            "- Before/After: creative_notes.csvのbefore_after入力後に比較",
            "- 保存理由: save_reason入力後に保存率と比較",
            "- コメント誘導: comment_prompt入力後にコメント率と比較",
            "- 伸びた投稿との関係: API指標とcreative_notesの両方がある投稿に限定して比較します。",
            "",
        ]
    )


def _section_11(lines: list[str], analysis: dict[str, Any]) -> None:
    trend = analysis["trend_analysis"]
    lines.extend(["## 11. トレンド分析", f"- 信頼度: {trend['confidence']}"])
    if not trend["available"]:
        lines.extend(
            [
                f"- 状態: {trend['message']}",
                f"- Creative CenterやGoogle Trendsで手動調査すべき項目: {safe_join(trend['manual_research_items'])}",
                "- 取り入れやすいトレンド: trend_research.csv入力後に判断",
                "- 取り入れない方がよいトレンド: 美容・コスメ領域に変換できないもの",
                "- 美容アカウントへの変換案: 入力後に生成",
                "- 音源方針: 説明が聞き取りやすい音量を優先。流行音源は手動調査結果で確認",
                "- ハッシュタグ方針: 美容カテゴリと投稿内容に一致するものだけ検証",
                "- 注意点: トレンドは自動取得しません。",
                "",
            ]
        )
        return
    lines.append("- 取り入れやすいトレンド:")
    lines.extend([f"  - {item.trend_name}: {item.adaptation_idea}" for item in trend["usable"]] or ["  - データ不足"])
    lines.append("- 取り入れない方がよいトレンド:")
    lines.extend([f"  - {item.trend_name}: {item.reason}" for item in trend["avoid"]] or ["  - データ不足"])
    lines.extend(["- 注意点: トレンドのテーマをそのまま輸入せず、美容の買う前チェック・比較・レビューに変換します。", ""])


def _section_12(lines: list[str], analysis: dict[str, Any]) -> None:
    comp = analysis["competitor_analysis"]
    lines.extend(["## 12. 参考アカウント分析", f"- 信頼度: {comp['confidence']}"])
    if not comp["available"]:
        lines.extend([f"- 状態: {comp['message']}", "- コピーしてはいけない点: テーマ、台本、固有表現、映像構成の丸写し", ""])
        return
    lines.extend(
        [
            "- 参考アカウントから抽出した型:",
            f"  - 冒頭フック構造: {_format_pairs(comp['hook_types'])}",
            f"  - 動画構成: {_format_pairs(comp['structures'])}",
            f"  - CTAパターン: {_format_pairs(comp['cta_types'])}",
            f"  - 尺: {_format_pairs(comp['durations'])}",
            "- テロップ密度: 競合メモのtext_densityだけを参照",
            "- 自アカウントへの変換案: 損失回避型、買う前チェック型、比較型を美容レビューへ変換",
            f"- コピーしてはいけない点: {comp['copy_guardrail']}",
            "",
        ]
    )


def _section_13(lines: list[str], analysis: dict[str, Any]) -> None:
    account = analysis["account"]
    lines.extend(
        [
            "## 13. プロフィール・導線改善",
            f"- 現在のプロフィール改善点: {account['genre']}で誰向けに何を投稿するかを先頭1文で明確にしてください。",
            f"- 誰向けか: {account['target_audience']}",
            "- 何が得られるか: 買う前に比較できる、正直な使用感が分かる、向き不向きが分かる",
            f"- 投稿頻度: {account['postable_frequency']}をプロフィールや固定投稿の期待値と合わせる",
            "- 固定投稿: 買う前チェック、自己紹介、保存価値の高い比較レビューの3本を候補にする",
            "- フォローする理由: 美容・コスメ選びの失敗を減らせることを明確にする",
            "- 動画末尾からプロフィールへの導線: 「他の比較レビューはプロフィールにまとめています」のように自然に誘導",
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
                f"- 元にした根拠データ: {idea['evidence']}",
                f"- 信頼度: {idea['confidence']}",
                f"- 注意点: {idea['note']}",
                "",
            ]
        )


def _section_15(lines: list[str], analysis: dict[str, Any]) -> None:
    lines.append("## 15. 30日間の運用プラン")
    for week in analysis["operation_plan"]:
        lines.extend(
            [
                f"- {week['week']}:",
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
    lines.append("## 18. 改善バックログ")
    for title, items in analysis["backlog"].items():
        lines.append(f"### {title}")
        lines.extend([f"- {item}" for item in items])
    lines.append("")


def _confidence_line(summary: dict[str, Any]) -> str:
    level = summary.get("confidence", "信頼度D")
    return f"- 信頼度: {level}（{confidence_description(level)}）"


def _format_frequency(value: float | None) -> str:
    if value is None:
        return DATA_INSUFFICIENT
    return f"週約{value:.1f}本"


def _format_pairs(items: list[tuple[Any, Any]] | None) -> str:
    if not items:
        return DATA_INSUFFICIENT
    return "、".join(f"{key}({value})" for key, value in items)


def _format_tag_items(items: list[dict[str, Any]] | None) -> str:
    if not items:
        return DATA_INSUFFICIENT
    return "、".join(f"{item['tag']}({item['count']})" for item in items)


def _post_lines(rows: list[dict[str, Any]], include_reason: bool = False) -> list[str]:
    lines = []
    for row in rows[:8]:
        reason = ""
        if include_reason and row.get("viral_reasons"):
            reason = f" / 理由: {safe_join(row['viral_reasons'])}"
        lines.append(
            f"  - {row.get('video_id') or DATA_INSUFFICIENT}: {format_number(row.get('view_count'))}再生 / {row.get('strategy_category') or DATA_INSUFFICIENT} / PR判定 {row.get('pr_status') or DATA_INSUFFICIENT}{reason}"
        )
    return lines
