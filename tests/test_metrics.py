import unittest

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from metrics import calculate_post_metrics, safe_divide, summarize_posts, trimmed_mean_excluding_top_percent
from models import Post


class MetricsTest(unittest.TestCase):
    def test_safe_divide_handles_zero_and_missing(self):
        self.assertIsNone(safe_divide(10, 0))
        self.assertIsNone(safe_divide(None, 10))
        self.assertEqual(safe_divide(10, 100), 0.1)

    def test_calculate_post_metrics(self):
        post = Post(
            title="test",
            views=1000,
            likes=100,
            comments=20,
            saves=50,
            shares=10,
            profile_visits=25,
            follow_gains=5,
            duration_sec=20,
            avg_watch_time_sec=10,
        )
        metric = calculate_post_metrics(post)
        self.assertEqual(metric.like_rate, 0.1)
        self.assertEqual(metric.comment_rate, 0.02)
        self.assertEqual(metric.save_rate, 0.05)
        self.assertEqual(metric.share_rate, 0.01)
        self.assertEqual(metric.profile_visit_rate, 0.025)
        self.assertEqual(metric.follow_conversion_rate, 0.005)
        self.assertEqual(metric.avg_retention_rate, 0.5)

    def test_summarize_posts_marks_small_data(self):
        metrics = [calculate_post_metrics(Post(views=100, likes=10))]
        summary = summarize_posts(metrics)
        self.assertEqual(summary["post_count"], 1)
        self.assertEqual(summary["average_views"], 100)
        self.assertIn("暫定仮説", summary["data_sufficiency"])

    def test_trimmed_mean_excluding_top_percent(self):
        self.assertEqual(trimmed_mean_excluding_top_percent([100, 110, 120, 10_000], 25), 110)


if __name__ == "__main__":
    unittest.main()
