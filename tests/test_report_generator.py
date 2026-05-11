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
    def _analysis(self):
        return analyze(
            load_account_profile(ROOT / "data" / "account_profile.sample.json"),
            load_api_posts(ROOT / "data" / "api_posts.sample.csv"),
            load_manual_insights(ROOT / "data" / "manual_insights.sample.csv"),
            load_creative_notes(ROOT / "data" / "creative_notes.sample.csv"),
            load_trend_research(ROOT / "data" / "trend_research.sample.csv"),
            load_competitor_posts(ROOT / "data" / "competitor_posts.sample.csv"),
        )

    def test_report_contains_new_required_sections_and_video_ideas(self):
        report = generate_markdown_report(self._analysis())
        self.assertIn("# TikTokアカウント分析レポート", report)
        self.assertIn("## 0. データ取得・分析範囲", report)
        self.assertIn("## 4. 手入力が必要な不足指標", report)
        self.assertIn("## 14. 次に作るべき動画案", report)
        self.assertIn("## 18. 改善バックログ", report)
        self.assertGreaterEqual(report.count("### 動画案"), 10)
        self.assertIn("APIでは通常取れないため", report)
        self.assertIn("信頼度", report)

    def test_report_guardrails_do_not_import_unrelated_themes(self):
        report = generate_markdown_report(self._analysis())
        self.assertNotIn("食費", report)
        self.assertNotIn("固定費", report)
        self.assertNotIn("冷蔵庫", report)
        self.assertIn("そのリップ買う前に見るべき3つのポイント", report)
        self.assertIn("参考アカウントから輸入するのは型だけ", report)


if __name__ == "__main__":
    unittest.main()
