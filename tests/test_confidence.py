import unittest

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from confidence import calculate_confidence_level, calculate_strategy_confidence


class ConfidenceTest(unittest.TestCase):
    def test_confidence_levels(self):
        self.assertEqual(calculate_confidence_level(0), "信頼度D")
        self.assertEqual(calculate_confidence_level(5), "信頼度C")
        self.assertEqual(calculate_confidence_level(12, qualitative_coverage=0.1), "信頼度B")
        self.assertEqual(calculate_confidence_level(30, qualitative_coverage=0.5), "信頼度A")

    def test_strategy_confidence_is_capped_when_supplemental_sources_are_empty(self):
        self.assertEqual(
            calculate_strategy_confidence(
                post_count=40,
                manual_count=0,
                creative_count=20,
                trend_count=5,
                competitor_count=5,
                creative_coverage=0.5,
            ),
            "信頼度C",
        )
        self.assertEqual(
            calculate_strategy_confidence(
                post_count=40,
                manual_count=0,
                creative_count=0,
                trend_count=0,
                competitor_count=0,
                creative_coverage=0.0,
            ),
            "信頼度D",
        )


if __name__ == "__main__":
    unittest.main()
