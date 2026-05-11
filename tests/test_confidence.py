import unittest

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from confidence import calculate_confidence_level


class ConfidenceTest(unittest.TestCase):
    def test_confidence_levels(self):
        self.assertEqual(calculate_confidence_level(0), "信頼度D")
        self.assertEqual(calculate_confidence_level(5), "信頼度C")
        self.assertEqual(calculate_confidence_level(12, qualitative_coverage=0.1), "信頼度B")
        self.assertEqual(calculate_confidence_level(30, qualitative_coverage=0.5), "信頼度A")


if __name__ == "__main__":
    unittest.main()
