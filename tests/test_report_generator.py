import unittest

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from analyzer import analyze
from loaders import load_account_profile, load_competitors, load_posts_csv, load_reference_posts_csv, load_trends
from report_generator import generate_markdown_report


ROOT = Path(__file__).resolve().parents[1]


class ReportGeneratorTest(unittest.TestCase):
    def test_report_contains_required_sections_and_video_ideas(self):
        analysis = analyze(
            load_account_profile(ROOT / "data" / "account_profile.sample.json"),
            load_posts_csv(ROOT / "data" / "posts.sample.csv"),
            load_trends(ROOT / "data" / "trends.sample.json"),
            load_competitors(ROOT / "data" / "competitors.sample.json"),
        )
        report = generate_markdown_report(analysis)
        self.assertIn("# TikTokアカウント分析レポート", report)
        self.assertIn("## 10. 次に作るべき動画案", report)
        self.assertIn("## 11. 30日間の運用プラン", report)
        self.assertIn("## 13. 仮説検証リスト", report)
        self.assertGreaterEqual(report.count("### 動画案"), 10)
        self.assertIn("データ不足", report)

    def test_report_includes_reference_post_comparison(self):
        analysis = analyze(
            load_account_profile(ROOT / "data" / "account_profile.sample.json"),
            load_posts_csv(ROOT / "data" / "posts.sample.csv"),
            load_trends(ROOT / "data" / "trends.sample.json"),
            load_competitors(ROOT / "data" / "competitors.sample.json"),
            load_reference_posts_csv(ROOT / "data" / "competitor_posts.sample.csv"),
        )
        report = generate_markdown_report(analysis)
        self.assertIn("投稿単位の比較", report)
        self.assertIn("参考投稿から取り入れるべき点", report)
        self.assertIn("@setsuyaku_note_c", report)


if __name__ == "__main__":
    unittest.main()
