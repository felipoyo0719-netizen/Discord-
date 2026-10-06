import unittest
from unittest.mock import patch
from pathlib import Path
import tempfile
import notify

TEST_DATA = {
    "Escalation": [
        {"week": "2026-10-05", "missions": ["Tombs", "Bank HQ"],
         "target_loot_by_day": [
            {"day": "2026-10-05", "target_loot": ["mask", "lmg"],
             "prototype_gear_cache": "chest", "prototype_weapon_cache": "smg"},
            {"day": "2026-10-06", "target_loot": ["rifle", "ar"],
             "prototype_gear_cache": "holster", "prototype_weapon_cache": "lmg"}
         ]}
    ]
}

class TestNotifier(unittest.TestCase):
    def test_picks_latest_not_future(self):
        snap = notify.latest_snapshot(TEST_DATA, "2026-10-05")
        self.assertEqual(snap["day"], "2026-10-05")
        self.assertEqual(snap["missions"], [["Tombs", "mask"], ["Bank HQ", "lmg"]])

    def test_today(self):
        self.assertEqual(notify.latest_snapshot(TEST_DATA, "2026-10-06")["missions"][0][1], "rifle")

    def test_bad_data_errors(self):
        with self.assertRaises(ValueError):
            notify.latest_snapshot({"Escalation": []}, "2026-10-06")

    def test_first_posts_and_same_data_does_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(notify, "STATE_PATH", Path(tmp) / "state/last_snapshot.json"), \
                 patch.object(notify, "fetch_json", return_value=TEST_DATA), \
                 patch.object(notify, "send_discord") as send, \
                 patch.dict("os.environ", {"DISCORD_WEBHOOK_URL": "https://discord.com/api/webhooks/123/test"}):
                self.assertTrue(notify.run())
                self.assertFalse(notify.run())
                self.assertEqual(send.call_count, 1)

    def test_no_state_update_after_failed_send(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "state/last_snapshot.json"
            with patch.object(notify, "STATE_PATH", state), \
                 patch.object(notify, "fetch_json", return_value=TEST_DATA), \
                 patch.object(notify, "send_discord", side_effect=RuntimeError("network failure")), \
                 patch.dict("os.environ", {"DISCORD_WEBHOOK_URL": "https://discord.com/api/webhooks/123/test"}):
                with self.assertRaises(RuntimeError):
                    notify.run()
                self.assertFalse(state.exists())

if __name__ == '__main__':
    unittest.main()
