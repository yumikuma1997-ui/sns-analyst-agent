import unittest

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from analyzer import analyze
from loaders import (
    load_account_profile,
    load_api_posts,
    load_competitor_posts,
    load_creative_notes,
    load_manual_insights,
    load_trend_research,
)
from report_generator import generate_markdown_report


ROOT = Path(__file__).resolve().parents[1]


class ReportGeneratorTest(unittest.TestCase):
    def _analysis(self, supplemental: bool = True):
        return analyze(
            load_account_profile(ROOT / "data" / "account_profile.sample.json"),
            load_api_posts(ROOT / "data" / "api_posts.sample.csv"),
            load_manual_insights(ROOT / "data" / "manual_insights.sample.csv") if supplemental else [],
            load_creative_notes(ROOT / "data" / "creative_notes.sample.csv") if supplemental else [],
            load_trend_research(ROOT / "data" / "trend_research.sample.csv") if supplemental else [],
            load_competitor_posts(ROOT / "data" / "competitor_posts.sample.csv") if supplemental else [],
        )

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
