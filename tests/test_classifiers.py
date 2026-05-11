import unittest

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from classifiers import classify_strategy_category_detail, detect_pr_status, hashtag_groups
from models import ApiPost


class ClassifierTest(unittest.TestCase):
    def test_detect_pr_status(self):
        post = ApiPost(title="正直レビュー", video_description="#PR 提供商品", hashtags=["#PR"])
        self.assertEqual(detect_pr_status(post), "明示PR")

    def test_strategy_category_detail_includes_reason_and_confidence(self):
        post = ApiPost(title="リップ比較", video_description="買う前に見るコスメレビュー", hashtags=["#リップ"])
        result = classify_strategy_category_detail(post)
        self.assertEqual(result["category"], "beauty_core")
        self.assertIn(result["confidence"], {"medium", "high"})
        self.assertTrue(result["reasons"])

    def test_hashtag_groups_do_not_treat_single_generic_or_pr_as_promising(self):
        rows = [
            {"hashtags": ["#おすすめ", "#リップ", "#PR"], "view_count": 100},
            {"hashtags": ["#リップ"], "view_count": 200},
            {"hashtags": ["#単発"], "view_count": 300},
        ]
        groups = hashtag_groups(rows, 150)
        self.assertEqual(groups["generic"][0]["tag"], "#おすすめ")
        self.assertEqual(groups["pr_disclosure"][0]["tag"], "#PR")
        self.assertEqual(groups["single"][0]["tag"], "#単発")
        self.assertEqual(groups["test_candidates"][0]["tag"], "#リップ")
        self.assertFalse(groups["promising_candidates"])


if __name__ == "__main__":
    unittest.main()
