import unittest

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from classifiers import detect_pr_status, hashtag_groups
from models import ApiPost


class ClassifierTest(unittest.TestCase):
    def test_detect_pr_status(self):
        post = ApiPost(title="正直レビュー", video_description="#PR 提供商品", hashtags=["#PR"])
        self.assertEqual(detect_pr_status(post), "明示PR")

    def test_hashtag_groups_do_not_treat_single_or_generic_as_promising(self):
        rows = [
            {"hashtags": ["#おすすめ", "#リップ"], "view_count": 100},
            {"hashtags": ["#リップ"], "view_count": 200},
            {"hashtags": ["#単発"], "view_count": 300},
        ]
        groups = hashtag_groups(rows, 150)
        self.assertEqual(groups["generic"][0]["tag"], "#おすすめ")
        self.assertEqual(groups["single"][0]["tag"], "#単発")
        self.assertEqual(groups["test_candidates"][0]["tag"], "#リップ")


if __name__ == "__main__":
    unittest.main()
