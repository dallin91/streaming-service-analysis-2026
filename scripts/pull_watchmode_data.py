"""
pull_watchmode_data.py

Pulls a snapshot of popular titles for a set of streaming services from the
Watchmode API and writes them to a single combined CSV for downstream
SQL/Tableau analysis.

FIX (2026-07-22): The original script only called /v1/list-titles/, which
returns id/title/type/year/imdb_id/tmdb_id but NOT genre_names, user_rating,
critic_score, or us_rating -- those fields only exist on the separate
/v1/title/{id}/details/ endpoint, called once per title. This version adds
that second call and merges the results in.

Cost note: with TITLES_PER_SERVICE=250 across 8 services (up to 2,000 titles,
fewer after de-duping titles that appear on multiple services), this will
use roughly (list-titles calls) + (1 details call per unique title) requests.
On the free Watchmode tier (2,500 requests/month) that's most of a month's
quota in one run -- there's no cheaper way to get these fields for every
title, since Watchmode doesn't expose them in bulk.

The script writes rows to disk incrementally and keeps a checkpoint file, so
if you hit the monthly quota (HTTP 402/429) partway through, you can re-run
it later and it'll pick up where it left off instead of losing progress or
re-spending requests on titles it already has.

Usage:
    1. Get a free API key: https://api.watchmode.com/requestApiKey
    2. Set it as an environment variable:  export WATCHMODE_API_KEY="your_key_here"
    3. Run:  python pull_watchmode_data.py
"""

import os
import time
import csv
import json
import requests
from dotenv import load_dotenv
load_dotenv()

API_KEY = os.environ.get("WATCHMODE_API_KEY")
BASE_URL = "https://api.watchmode.com/v1"
LIST_TITLES_URL = f"{BASE_URL}/list-titles/"
TITLE_DETAILS_URL = f"{BASE_URL}/title/{{title_id}}/details/"

OUTPUT_FILE = "data/raw/streaming_titles_raw.csv"
CHECKPOINT_FILE = "data/raw/.watchmode_details_checkpoint.json"

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
DETAILS_REQUEST_DELAY = 0.4  # be polite to the API / stay under rate limits

LIST_FIELDS = ["id", "title", "type", "year", "imdb_id", "tmdb_id"]
DETAIL_FIELDS = ["genre_names", "user_rating", "critic_score", "us_rating"]
FIELDS = ["id", "title", "type", "year", "genre_names", "user_rating",
          "critic_score", "imdb_id", "tmdb_id", "us_rating"]


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
        response = requests.get(LIST_TITLES_URL, params=params, timeout=30)

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


def load_checkpoint() -> dict:
    """Load previously-fetched title details, keyed by title id (as str)."""
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_checkpoint(details_by_id: dict) -> None:
    os.makedirs(os.path.dirname(CHECKPOINT_FILE), exist_ok=True)
    with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
        json.dump(details_by_id, f)


MAX_RETRIES = 4          # for transient network errors (timeouts, DNS blips, etc.)
RETRY_BACKOFF_BASE = 2.0  # seconds; doubles each retry (2s, 4s, 8s, 16s)


def fetch_title_details(title_id: int) -> dict | str | None:
    """Fetch genre_names, user_rating, critic_score, us_rating for one title.

    Returns:
      - {"data": {...}}                  on success
      - "retry_exhausted"                if the network kept failing after MAX_RETRIES
      - None                             on quota/auth errors (401/402/429) -- caller should stop
    """
    params = {"apiKey": API_KEY}
    url = TITLE_DETAILS_URL.format(title_id=title_id)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(url, params=params, timeout=30)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
            wait = RETRY_BACKOFF_BASE * (2 ** (attempt - 1))
            print(f"  Network error on title {title_id} (attempt {attempt}/{MAX_RETRIES}): "
                  f"{type(exc).__name__}. Retrying in {wait:.0f}s...")
            time.sleep(wait)
            continue

        if response.status_code in (401, 402, 429):
            print(f"  Stopping: got status {response.status_code} on title {title_id} "
                  f"({response.text[:150]}). Likely hit the API quota or rate limit.")
            return None

        if response.status_code != 200:
            print(f"  Details request failed for title {title_id} (status {response.status_code}); skipping.")
            return {"data": {field: None for field in DETAIL_FIELDS}}

        payload = response.json()
        genres = payload.get("genre_names")
        return {
            "data": {
                "genre_names": "|".join(genres) if genres else None,
                "user_rating": payload.get("user_rating"),
                "critic_score": payload.get("critic_score"),
                "us_rating": payload.get("us_rating"),
            },
        }

    # Exhausted retries on network errors -- don't mark this title as done in the
    # checkpoint, so a future run will try it again instead of leaving it blank forever.
    print(f"  Giving up on title {title_id} after {MAX_RETRIES} network retries; will retry on next run.")
    return "retry_exhausted"


def main():
    if not API_KEY:
        raise SystemExit("Set the WATCHMODE_API_KEY environment variable before running this script.")

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    # --- Step 1: list-titles per service (cheap: ~1 request per service) ---
    rows = []
    for service_name, source_id in SERVICES.items():
        print(f"Fetching titles for {service_name}...")
        titles = fetch_titles_for_service(source_id, TITLES_PER_SERVICE)
        print(f"  Retrieved {len(titles)} titles.")

        for t in titles:
            row = {field: t.get(field) for field in LIST_FIELDS}
            row["service"] = service_name
            rows.append(row)

    unique_ids = sorted({row["id"] for row in rows if row.get("id") is not None})
    print(f"\n{len(rows)} service listings covering {len(unique_ids)} unique titles.")

    # --- Step 2: title details per UNIQUE title id (expensive: 1 request each) ---
    details_by_id = load_checkpoint()
    already_have = len(details_by_id)
    if already_have:
        print(f"Resuming from checkpoint: {already_have} titles already have details.")

    stopped_early = False
    try:
        for i, title_id in enumerate(unique_ids, start=1):
            key = str(title_id)
            if key in details_by_id:
                continue

            result = fetch_title_details(title_id)
            if result is None:
                stopped_early = True
                break
            if result == "retry_exhausted":
                continue  # leave it out of the checkpoint; a later run will retry it

            details_by_id[key] = result["data"]

            if i % 25 == 0:
                print(f"  Fetched details for {i}/{len(unique_ids)} unique titles...")
                save_checkpoint(details_by_id)  # periodic save in case of a crash

            time.sleep(DETAILS_REQUEST_DELAY)
    finally:
        # Always persist whatever we've fetched so far, even on Ctrl+C or an
        # unexpected exception -- no run should lose more than one in-flight title.
        save_checkpoint(details_by_id)

    # --- Step 3: merge details into rows and write CSV ---
    for row in rows:
        detail = details_by_id.get(str(row.get("id")), {})
        for field in DETAIL_FIELDS:
            row[field] = detail.get(field)

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["service"] + FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    filled = sum(1 for row in rows if row.get("genre_names"))
    print(f"\nDone. Wrote {len(rows)} rows to {OUTPUT_FILE}")
    print(f"  {filled}/{len(rows)} rows have genre/rating data filled in.")
    if stopped_early:
        print("  NOTE: stopped early due to API quota/rate limit. Re-run this script "
              "later to pick up the remaining titles from the checkpoint -- rows for "
              "titles not yet fetched will have blank genre/rating columns for now.")
    else:
        # All details fetched successfully -- checkpoint no longer needed.
        if os.path.exists(CHECKPOINT_FILE):
            os.remove(CHECKPOINT_FILE)


if __name__ == "__main__":
    main()