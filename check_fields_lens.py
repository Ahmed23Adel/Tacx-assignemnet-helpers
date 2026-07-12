"""
For every artwork by a given artist, fetches the FULL record from
GET /artworks/{id} and reports string-length statistics (min, max, average)
for the `medium_display` and `date_display` fields.

Step 1 collects every artwork id for the artist via /artworks/search
(paginated). Step 2 fetches each artwork's full detail individually and
measures len(medium_display) and len(date_display). Missing/empty fields
are excluded from the stats but counted separately.

Usage:
    python check_field_lengths.py "Rembrandt van Rijn"
    python check_field_lengths.py "Utagawa Toyoharu" --max 20 --delay 0.3
"""

import argparse
import sys
import time
from urllib.parse import urlencode

import requests

SEARCH_URL = "https://api.artic.edu/api/v1/artworks/search"
DETAIL_URL = "https://api.artic.edu/api/v1/artworks/{id}"

HEADERS = {"AIC-User-Agent": "TacxAssignmentFieldLengthCheck/1.0 (contact: example@example.com)"}

FIELDS_TO_MEASURE = ["medium_display", "date_display"]


def is_missing(value) -> bool:
    """Treat None and empty/whitespace-only strings as missing."""
    return value is None or (isinstance(value, str) and value.strip() == "")


def collect_artist_ids(session: requests.Session, artist: str, page_limit: int = 100) -> list:
    """Walk /artworks/search pages and collect every artwork id for the artist."""
    ids = []
    page = 1
    while True:
        params = {
            "query[match_phrase][artist_title]": artist,
            "fields": "id",
            "limit": page_limit,
            "page": page,
        }
        url = f"{SEARCH_URL}?{urlencode(params)}"
        resp = session.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        ids.extend(row["id"] for row in data["data"])

        total_pages = data["pagination"]["total_pages"]
        print(f"  collected page {page}/{total_pages} of artwork ids ({len(ids)} so far)")

        if page >= total_pages:
            break
        page += 1

    return ids


def fetch_detail(session: requests.Session, artwork_id: int) -> dict:
    url = DETAIL_URL.format(id=artwork_id)
    resp = session.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json()["data"]


def summarize_lengths(records: list) -> dict:
    """records is a list of (artwork_id, value) tuples for a single field."""
    if not records:
        return {"count": 0, "min": None, "max": None, "avg": None, "max_record": None}
    lengths = [len(value) for _, value in records]
    max_record = max(records, key=lambda r: len(r[1]))
    return {
        "count": len(records),
        "min": min(lengths),
        "max": max(lengths),
        "avg": sum(lengths) / len(lengths),
        "max_record": max_record,  # (artwork_id, value)
    }


def check_artist(artist: str, max_artworks: int = None, delay: float = 0.2):
    session = requests.Session()

    print(f'Collecting artwork ids for artist: "{artist}"\n')
    ids = collect_artist_ids(session, artist)

    if max_artworks:
        ids = ids[:max_artworks]

    print(f"\nFetching full detail for {len(ids)} artwork(s)...\n")

    # records[field] -> list of (artwork_id, value) for present, non-empty values
    records = {field: [] for field in FIELDS_TO_MEASURE}
    # missing_ids[field] -> list of artwork ids where the field was missing/empty
    missing_ids = {field: [] for field in FIELDS_TO_MEASURE}

    total_checked = 0

    for i, artwork_id in enumerate(ids, start=1):
        detail = fetch_detail(session, artwork_id)
        total_checked += 1

        for field in FIELDS_TO_MEASURE:
            value = detail.get(field)
            if is_missing(value):
                missing_ids[field].append(artwork_id)
            else:
                records[field].append((artwork_id, value))

        if i % 10 == 0 or i == len(ids):
            print(f"  checked {i}/{len(ids)}")

        time.sleep(delay)  # be polite to the API

    print(f"\nTotal artworks checked: {total_checked}\n")

    summaries = {}
    for field in FIELDS_TO_MEASURE:
        stats = summarize_lengths(records[field])
        summaries[field] = stats

        print(f"--- {field} ---")
        print(f"  present: {stats['count']}/{total_checked}")
        print(f"  missing/empty: {len(missing_ids[field])}/{total_checked}")
        if stats["count"]:
            print(f"  min length: {stats['min']}")
            print(f"  max length: {stats['max']}")
            print(f"  avg length: {stats['avg']:.2f}")
            max_id, max_value = stats["max_record"]
            print(f"  longest value (id={max_id}): {max_value!r}")
        else:
            print("  no values to summarize")
        if missing_ids[field]:
            preview = missing_ids[field][:10]
            suffix = "..." if len(missing_ids[field]) > 10 else ""
            print(f"  missing ids (first 10): {preview}{suffix}")
        print()

    return summaries, missing_ids


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artist", help='Artist name, e.g. "Rembrandt van Rijn"')
    parser.add_argument(
        "--max", type=int, default=None, help="Only check the first N artworks (useful for large artists)"
    )
    parser.add_argument("--delay", type=float, default=0.2, help="Delay between detail requests, in seconds")
    args = parser.parse_args()

    check_artist(args.artist, max_artworks=args.max, delay=args.delay)
    sys.exit(0)