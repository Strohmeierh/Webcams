#!/usr/bin/env python3
"""
Fetch LSZK weather data from the public WeatherLink embed endpoints and write:
  - data/lszk_latest.json    (single pretty-printed snapshot, overwritten)
  - data/lszk_history.jsonl  (one compact JSON per line, appended)

The embed endpoints (used by weatherlink.com's /embeddablePage widget) do not
require API-Key / Secret — just the device URL-token from the embed URL.

Required environment variables:
    WEATHERLINK_DEVICE_TOKEN   e.g. 411b7945460c42848a14d053bb7c03c0

Optional:
    WEATHERLINK_OUT_DIR        default: "data"

Note: these endpoints are *internal* to weatherlink.com (not part of the
documented v2 API). They are stable enough for hobby logging but could change
without notice.
"""
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://www.weatherlink.com/embeddablePage"
TOKEN = os.environ.get("WEATHERLINK_DEVICE_TOKEN")
OUT_DIR = Path(os.environ.get("WEATHERLINK_OUT_DIR", "data"))

if not TOKEN:
    sys.exit("ERROR: Set WEATHERLINK_DEVICE_TOKEN (from the embed URL).")


def get_json(url: str) -> dict:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "lszk-weather-logger/1.0 (+github-actions)",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code} for {url}: {e.read().decode(errors='replace')}")


current = get_json(f"{BASE}/getData/{TOKEN}")
summary = get_json(f"{BASE}/summaryData/{TOKEN}")

last_received_ms = current.get("lastReceived")
last_received_iso = (
    datetime.fromtimestamp(last_received_ms / 1000, tz=timezone.utc).isoformat()
    if isinstance(last_received_ms, (int, float))
    else None
)

record = {
    "fetched_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    "station_last_received_utc": last_received_iso,
    "device_token": TOKEN,
    "current": current,
    "summary": summary,
}

OUT_DIR.mkdir(parents=True, exist_ok=True)
(OUT_DIR / "lszk_latest.json").write_text(
    json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8"
)
with (OUT_DIR / "lszk_history.jsonl").open("a", encoding="utf-8") as f:
    f.write(json.dumps(record, separators=(",", ":"), ensure_ascii=False) + "\n")

temp = current.get("temperature")
wind = current.get("wind")
gust = current.get("gust")
print(
    f"OK — LSZK @ {last_received_iso}: T={temp}°C, wind={wind} gust={gust} "
    f"(station last update)"
)
