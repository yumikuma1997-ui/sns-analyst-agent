import unittest

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from analyzer import analyze
from models import AccountProfile, ApiPost, CompetitorPost, CreativeNote, ManualInsight, TrendResearch
from report_generator import generate_markdown_report


class ReportGeneratorTest(unittest.TestCase):
    def _analysis(self, supplemental: bool = True):
        posts = [
            ApiPost(
                video_id="v001",
                posted_at="2026-05-08 20:30",
                title="そのリップ買う前に見るべき3つのポイント",
                video_description="リップ比較 #リップ #コスメレビュー",
                duration=27,
                view_count=8200,
                like_count=410,
                comment_count=18,
                share_count=12,
                hashtags=["#リップ", "#コスメレビュー"],
            ),
            ApiPost(
                video_id="v002",
                posted_at="2026-05-06 21:00",
                title="Qoo10メガ割で失敗しにくい韓国コスメの選び方",
                video_description="韓国コスメ比較 #韓国コスメ #Qoo10",
                duration=33,
                view_count=12600,
                like_count=520,
                comment_count=31,
                share_count=26,
                hashtags=["#韓国コスメ", "#Qoo10"],
            ),
            ApiPost(
                video_id="v003",
                posted_at="2026-05-03 19:10",
                title="PRスキンケアを正直レビュー",
                video_description="#PR 提供商品の正直レビュー #スキンケア",
                duration=42,
                view_count=3900,
                like_count=130,
                comment_count=8,
                share_count=5,
                hashtags=["#PR", "#スキンケア"],
            ),
            ApiPost(
                video_id="v004",
                posted_at="2026-04-20 18:30",
                title="バズコスメ本当に良かったところ微妙だったところ",
                video_description="バズコスメ比較 #バズコスメ #コスメレビュー",
                duration=29,
                view_count=45000,
                like_count=1700,
                comment_count=92,
                share_count=75,
                hashtags=["#バズコスメ", "#コスメレビュー"],
            ),
            ApiPost(
                video_id="v005",
                posted_at="2026-03-21 20:00",
                title="冷蔵庫の収納を変えたら楽になった",
                video_description="暮らし #収納",
                duration=18,
                view_count=200000,
                like_count=8500,
                comment_count=120,
                share_count=400,
                hashtags=["#収納", "#暮らし"],
            ),
        ]
        account = AccountProfile(account_name="7makeup7", genre="美容・コスメレビュー", target_audience="美容購入前レビューを探す人")
        manual = [ManualInsight(video_id="v001", saves=96, average_watch_time=18, completion_rate=0.48)] if supplemental else []
        creative = [
            CreativeNote(
                video_id="v001",
                account_strategy_category="beauty_core",
                content_category="リップ比較",
                is_pr=False,
                hook_text="買う前にこの3つ見て",
                hook_type="買う前チェック",
                video_structure="悩み提示 -> 3チェック -> 向く人",
                cta_type="保存促し",
                text_density="中",
            )
        ] if supplemental else []
        trends = [TrendResearch(trend_name="Qoo10メガ割", should_use=True, adaptation_idea="買う前チェックに変換")] if supplemental else []
        competitors = [
            CompetitorPost(
                competitor_account="@beauty_ref",
                hook_type="損失回避",
                video_structure="悩み提示 -> 比較 -> 向く人",
                cta_type="保存促し",
                should_adapt=True,
                adaptation_target="hook",
            )
        ] if supplemental else []
        return analyze(account, posts, manual, creative, trends, competitors)

    def test_report_contains_requested_sections_and_video_ideas(self):
        report = generate_markdown_report(self._analysis())
        self.assertIn("# TikTokアカウント分析レポート", report)
        self.assertIn("## Executive Summary", report)
        self.assertIn("API集計信頼度", report)
        self.assertIn("戦略提案信頼度", report)
        self.assertIn("## 4. 手入力が必要な不足指標", report)
        self.assertIn("### 次に入力すべきデータ", report)
        self.assertIn("## 14. 次に作るべき動画案", report)
        self.assertIn("## 18. 改善バックログ", report)
        self.assertGreaterEqual(report.count("### 動画案"), 10)

    def test_report_guardrails_keep_unrelated_themes_out_of_video_ideas(self):
        report = generate_markdown_report(self._analysis())
        idea_titles = "\n".join(line for line in report.splitlines() if line.startswith("- タイトル:"))
        for banned in ("食費", "固定費", "掃除", "収納", "冷蔵庫", "玄関"):
            self.assertNotIn(banned, idea_titles)
        self.assertIn("そのリップ買う前に見るべき3つのポイント", idea_titles)
        self.assertIn("参考アカウントから取り入れるのは型だけ", report)

    def test_report_classifies_pr_disclosure_tags(self):
        report = generate_markdown_report(self._analysis())
        self.assertIn("PR開示タグ", report)
        promising_line = next(line for line in report.splitlines() if line.startswith("- 有望タグ候補:"))
        self.assertNotIn("#PR", promising_line)
        self.assertNotIn("#ad", promising_line.lower())

    def test_strategy_confidence_drops_without_supplemental_inputs(self):
        analysis = self._analysis(supplemental=False)
        self.assertIn(analysis["data_scope"]["strategy_recommendation_confidence"], {"信頼度C", "信頼度D"})
        report = generate_markdown_report(analysis)
        self.assertIn("戦略提案信頼度", report)
        self.assertIn("creative_notes.csv が未入力", report)


if __name__ == "__main__":
    unittest.main()
