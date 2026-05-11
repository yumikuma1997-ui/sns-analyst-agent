import csv
import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tiktok_api import (
    OAuthConfig,
    build_code_challenge,
    build_authorization_url,
    create_pkce_pair,
    normalize_video_list_raw,
    write_normalized_videos_csv,
)


class TikTokApiTest(unittest.TestCase):
    def test_build_authorization_url(self):
        url = build_authorization_url(
            OAuthConfig(
                client_key="client_key",
                redirect_uri="http://127.0.0.1:8765/callback",
                scopes=["user.info.basic", "video.list"],
                state="state123",
                code_challenge="challenge",
            )
        )
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        self.assertEqual(parsed.scheme, "https")
        self.assertEqual(query["client_key"], ["client_key"])
        self.assertEqual(query["scope"], ["user.info.basic,video.list"])
        self.assertEqual(query["response_type"], ["code"])
        self.assertEqual(query["state"], ["state123"])
        self.assertEqual(query["code_challenge"], ["challenge"])

    def test_pkce_pair(self):
        pkce = create_pkce_pair()
        self.assertGreaterEqual(len(pkce["code_verifier"]), 43)
        self.assertEqual(pkce["code_challenge"], build_code_challenge(pkce["code_verifier"]))
        self.assertEqual(pkce["code_challenge_method"], "S256")

    def test_normalize_video_list_raw(self):
        raw = {
            "source": "tiktok_display_api_video_list",
            "videos": [
                {
                    "id": "123",
                    "title": "Video title",
                    "video_description": "説明 #節約 #一人暮らし",
                    "create_time": 1714521600,
                    "duration": 31,
                    "share_url": "https://www.tiktok.com/@me/video/123",
                    "embed_link": "https://www.tiktok.com/embed/123",
                    "like_count": 100,
                    "comment_count": 5,
                    "share_count": 3,
                    "view_count": 1000,
                }
            ],
        }
        rows = normalize_video_list_raw(raw)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["video_id"], "123")
        self.assertEqual(rows[0]["views"], 1000)
        self.assertEqual(rows[0]["likes"], 100)
        self.assertEqual(rows[0]["comments"], 5)
        self.assertEqual(rows[0]["shares"], 3)
        self.assertIn("#節約", rows[0]["hashtags"])
        self.assertEqual(rows[0]["saves"], "")

    def test_write_normalized_videos_csv(self):
        rows = normalize_video_list_raw(
            {
                "videos": [
                    {
                        "id": "123",
                        "title": "Video title",
                        "video_description": "説明",
                        "create_time": 1714521600,
                        "duration": 31,
                        "view_count": 1000,
                    }
                ]
            }
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "videos.csv"
            write_normalized_videos_csv(output, rows)
            with output.open("r", encoding="utf-8-sig", newline="") as file:
                loaded = list(csv.DictReader(file))
        self.assertEqual(loaded[0]["video_id"], "123")
        self.assertEqual(loaded[0]["views"], "1000")
        self.assertEqual(loaded[0]["avg_watch_time_sec"], "")


if __name__ == "__main__":
    unittest.main()
