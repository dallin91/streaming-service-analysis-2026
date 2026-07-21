"""
pull_watchmode_data.py

Pulls a snapshot of popular titles for a set of streaming services from the
Watchmode API and writes them to a single combined CSV for downstream
SQL/Tableau analysis.

Usage:
    1. Get a free API key: https://api.watchmode.com/requestApiKey
    2. Set it as an environment variable:  export WATCHMODE_API_KEY="your_key_here"
    3. Run:  python pull_watchmode_data.py
"""

import os
import time
import csv
import requests
from dotenv import load_dotenv
load_dotenv()

API_KEY = os.environ.get("WATCHMODE_API_KEY")
BASE_URL = "https://api.watchmode.com/v1/list-titles/"
OUTPUT_FILE = "data/streaming_titles_raw.csv"

# Map each service to its Watchmode source_id.
# Confirm/update these against the current /v1/sources/ endpoint before running --
# Watchmode's source IDs can change, so don't trust this list blindly.
SERVICES = {
    "Netflix": 203,
    "Hulu": 157,
    "Disney+": 372,
    "Max": 387,
    "Amazon Prime Video": 26,
    "Apple TV+": 371,
    "Peacock": 388,
    "Paramount+": 444,
}

TITLES_PER_SERVICE = 250  # cap per service to stay well within the free quota
PAGE_SIZE = 250           # Watchmode's max page size

FIELDS = ["id", "title", "type", "year", "genre_names", "user_rating", "critic_score", "imdb_id", "tmdb_id", "us_rating"]


def fetch_titles_for_service(source_id: int, limit: int) -> list[dict]:
    """Fetch up to `limit` popular titles for a given source_id."""
    titles = []
    page = 1

    while len(titles) < limit:
        params = {
            "apiKey": API_KEY,
            "source_ids": source_id,
            "region": "US",
            "sort_by": "popularity_desc",
            "limit": min(PAGE_SIZE, limit - len(titles)),
            "page": page,
        }
        response = requests.get(BASE_URL, params=params, timeout=30)

        if response.status_code != 200:
            print(f"  Request failed (status {response.status_code}): {response.text[:200]}")
            break

        payload = response.json()
        page_titles = payload.get("titles", [])

        if not page_titles:
            break  # no more results

        titles.extend(page_titles)
        page += 1
        time.sleep(0.5)  # be polite to the API

    return titles[:limit]


def main():
    if not API_KEY:
        raise SystemExit("Set the WATCHMODE_API_KEY environment variable before running this script.")

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    rows = []

    for service_name, source_id in SERVICES.items():
        print(f"Fetching titles for {service_name}...")
        titles = fetch_titles_for_service(source_id, TITLES_PER_SERVICE)
        print(f"  Retrieved {len(titles)} titles.")

        for t in titles:
            row = {field: t.get(field) for field in FIELDS}
            row["service"] = service_name
            rows.append(row)

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["service"] + FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nDone. Wrote {len(rows)} rows to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()