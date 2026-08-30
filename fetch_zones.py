"""
Fetch FortyGuard Heat Intelligence reports for multiple micro-zones.
Run this yourself with your real API key. It will save one PDF per zone
into ./reports/, e.g. reports/downtown_concrete.pdf

Usage:
    python fetch_zones.py
"""

import time
from pathlib import Path
import requests

API_KEY = "d2b929048f21cb8ba4616c9666061c70"  # <-- put your real key here
HEADERS = {"api-key": API_KEY}
BASE_URL = "https://api.fortyguard.com/v1"
TODAY = "2026-08-29"  # update if you run this on a different day

# Pick 3 contrasting Phoenix micro-zones for the "3 blocks away" story.
# lat/long are approximate — swap for exact addresses if you have them.
ZONES = {
    "downtown_concrete": {
        "latitude": 33.4484,
        "longitude": -112.0740,
        "temperature": 112.0,  # current/observed temp for that zone, adjust as needed
    },
    "tree_canopy_suburb": {
        "latitude": 33.4942,
        "longitude": -112.0430,  # Encanto Park area, more tree cover
        "temperature": 104.0,
    },
    "industrial_zone": {
        "latitude": 33.4255,
        "longitude": -112.0104,
        "temperature": 115.0,
    },
}

Path("reports").mkdir(exist_ok=True)


def submit(zone_name, params):
    payload = {
        "latitude": params["latitude"],
        "longitude": params["longitude"],
        "temperature": params["temperature"],
        "date": TODAY,
        "analysis": ["environmental"],
    }
    resp = requests.post(f"{BASE_URL}/heat_intelligence", headers=HEADERS, json=payload)
    resp.raise_for_status()
    data = resp.json()
    print(f"[{zone_name}] submitted -> {data}")
    return data["data"]["activity_id"]


def poll_and_download(zone_name, activity_id):
    status_url = f"{BASE_URL}/status/{activity_id}"
    for _ in range(120):
        r = requests.get(status_url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        data = r.json()["data"]
        status = data.get("status")

        if status == "Completed":
            link = (data.get("result") or {}).get("download_link")
            if not link:
                raise RuntimeError(f"[{zone_name}] completed with no download_link")
            report = requests.get(link, timeout=60)
            report.raise_for_status()
            out_path = Path("reports") / f"{zone_name}.pdf"
            out_path.write_bytes(report.content)
            print(f"[{zone_name}] saved -> {out_path}")
            return

        if status == "Failed":
            raise RuntimeError(f"[{zone_name}] activity failed")

        time.sleep(5)

    raise TimeoutError(f"[{zone_name}] did not complete in time")


if __name__ == "__main__":
    for zone_name, params in ZONES.items():
        activity_id = submit(zone_name, params)
        poll_and_download(zone_name, activity_id)
