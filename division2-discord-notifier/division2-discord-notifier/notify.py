#!/usr/bin/env python3
"""Notify Discord only when The Division 2 Escalation target loot changes."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

DATA_URL = os.getenv(
    "DIVISION2_DATA_URL",
    "https://hi-dep.github.io/division2/data/event/index.json",
)
PAGE_URL = "https://hidep-division2.pages.dev/?lang=ja&view=target_loot"
STATE_PATH = Path("state/last_snapshot.json")
JST = ZoneInfo("Asia/Tokyo")


def fetch_json(url: str) -> dict:
    request = Request(url, headers={"User-Agent": "division2-discord-notifier/1.0", "Cache-Control": "no-cache"})
    with urlopen(request, timeout=25) as response:
        return json.load(response)


def latest_snapshot(data: dict, today: str) -> dict:
    """Select the newest available target loot on or before today's JST date."""
    options = []
    events = data.get("Escalation")
    if not isinstance(events, list):
        raise ValueError("Escalation data missing from the source")

    for week in events:
        if not isinstance(week, dict):
            continue
        missions = week.get("missions")
        daily_rows = week.get("target_loot_by_day")
        if not isinstance(missions, list) or not isinstance(daily_rows, list):
            continue
        for row in daily_rows:
            if not isinstance(row, dict):
                continue
            day = row.get("day")
            loot = row.get("target_loot")
            if not isinstance(day, str) or len(day) != 10 or day > today:
                continue
            if not isinstance(loot, list) or not loot or len(loot) != len(missions):
                continue
            snapshot = {
                "day": day,
                "week": str(week.get("week", "")),
                "missions": [[str(m), str(l)] for m, l in zip(missions, loot)],
                "prototype_gear_cache": str(row.get("prototype_gear_cache", "")),
                "prototype_weapon_cache": str(row.get("prototype_weapon_cache", "")),
            }
            options.append(snapshot)

    if not options:
        raise ValueError("No valid Escalation target loot up to today's JST date")
    return max(options, key=lambda item: item["day"])


def embed_for(snapshot: dict) -> dict:
    mission_lines = [
        f"**{number}. {mission}** → {loot}"
        for number, (mission, loot) in enumerate(snapshot["missions"], start=1)
    ]
    # Discord embed field limit is 1024 characters. Five missions normally fit.
    mission_text = "\n".join(mission_lines)
    if len(mission_text) > 1024:
        raise ValueError("Mission data is too long for Discord embed")

    fields = [{"name": "🎯 エスカレーション目標アイテム", "value": mission_text, "inline": False}]
    caches = []
    if snapshot["prototype_gear_cache"]:
        caches.append(f"装備：{snapshot['prototype_gear_cache']}")
    if snapshot["prototype_weapon_cache"]:
        caches.append(f"武器：{snapshot['prototype_weapon_cache']}")
    if caches:
        fields.append({"name": "📦 プロトタイプキャッシュ", "value": "\n".join(caches)[:1024], "inline": False})

    return {
        "title": f"Division 2｜目標アイテム更新（{snapshot['day']}）",
        "url": PAGE_URL,
        "description": "元データの変更を検出しました。下のリンクから配置を確認できます。",
        "color": 0xFF8C00,
        "fields": fields,
        "footer": {"text": "非公式ファンデータ｜出典：hi-dep"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def send_discord(webhook_url: str, snapshot: dict) -> None:
    payload = {
        "username": "Division 2 目標アイテム通知",
        "avatar_url": "",
        "embeds": [embed_for(snapshot)],
        "allowed_mentions": {"parse": []},
    }
    request = Request(
        webhook_url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "division2-discord-notifier/1.0"},
        method="POST",
    )
    with urlopen(request, timeout=25) as response:
        if response.status not in (200, 204):
            raise RuntimeError(f"Discord returned HTTP {response.status}")


def run() -> bool:
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        raise ValueError("DISCORD_WEBHOOK_URL secret not set")
    if not webhook_url.startswith("https://discord.com/api/webhooks/"):
        raise ValueError("DISCORD_WEBHOOK_URL must be a Discord webhook URL")

    today = datetime.now(JST).date().isoformat()
    snapshot = latest_snapshot(fetch_json(DATA_URL), today)
    old = None
    if STATE_PATH.exists():
        old = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    if old == snapshot:
        print(f"No change: {snapshot['day']} (no Discord post)")
        return False

    send_discord(webhook_url, snapshot)
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(
        json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Posted updated Escalation loot: {snapshot['day']}")
    return True


if __name__ == "__main__":
    try:
        run()
    except (ValueError, HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)
