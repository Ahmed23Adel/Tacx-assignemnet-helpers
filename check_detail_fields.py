"""
For every artwork by a given artist, fetches the FULL record from
GET /artworks/{id} (e.g. https://api.artic.edu/api/v1/artworks/129884)
and checks that all fields needed for the detail screen are present:

    title, artist_display, date_display, medium_display, dimensions,
    place_of_origin, credit_line, image_id (used to build the large IIIF
    image), and at least one of short_description / description.

Step 1 collects every artwork id for the artist via /artworks/search
(paginated). Step 2 fetches each artwork's full detail individually and
checks it. Prints an overall True/False and lists exactly which ids are
missing which field(s).

Usage:
    python check_detail_fields.py "Rembrandt van Rijn"
    python check_detail_fields.py "Utagawa Toyoharu" --max 20 --delay 0.3
"""

import argparse
import sys
import time
from urllib.parse import urlencode

import requests

SEARCH_URL = "https://api.artic.edu/api/v1/artworks/search"
DETAIL_URL = "https://api.artic.edu/api/v1/artworks/{id}"

HEADERS = {"AIC-User-Agent": "TacxAssignmentDetailCheck/1.0 (contact: example@example.com)"}

# Fields required to render the detail screen (excluding the description group,
# which is handled separately since either short_description or description works).
REQUIRED_FIELDS = [
    "title",
    "artist_display",
    "date_display",
    "medium_display",
    "dimensions",
    "place_of_origin",
    "credit_line",
    "image_id",
]

DESCRIPTION_FIELDS = ["short_description", "description"]


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


def check_artist(artist: str, max_artworks: int = None, delay: float = 0.2):
    session = requests.Session()

    print(f'Collecting artwork ids for artist: "{artist}"\n')
    ids = collect_artist_ids(session, artist)

    if max_artworks:
        ids = ids[:max_artworks]

    print(f"\nFetching full detail for {len(ids)} artwork(s)...\n")

    problem_rows = []
    total_checked = 0

    for i, artwork_id in enumerate(ids, start=1):
        detail = fetch_detail(session, artwork_id)
        total_checked += 1

        missing = [f for f in REQUIRED_FIELDS if is_missing(detail.get(f))]

        # Description: only a problem if BOTH short_description and description are missing.
        if all(is_missing(detail.get(f)) for f in DESCRIPTION_FIELDS):
            missing.append("short_description/description")

        if missing:
            problem_rows.append(
                {
                    "id": artwork_id,
                    "title": detail.get("title"),
                    "missing_fields": missing,
                }
            )

        if i % 10 == 0 or i == len(ids):
            print(f"  checked {i}/{len(ids)}")

        time.sleep(delay)  # be polite to the API

    all_clean = len(problem_rows) == 0

    print(f"\nTotal artworks checked: {total_checked}")
    print(f"All rows have every required detail field: {all_clean}\n")

    if not all_clean:
        print(f"Rows with missing fields ({len(problem_rows)}):")
        for r in problem_rows:
            print(f"  id={r['id']:<8} title={r['title']!r:<60} missing={r['missing_fields']}")

    return all_clean, problem_rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artist", help='Artist name, e.g. "Rembrandt van Rijn"')
    parser.add_argument(
        "--max", type=int, default=None, help="Only check the first N artworks (useful for large artists)"
    )
    parser.add_argument("--delay", type=float, default=0.2, help="Delay between detail requests, in seconds")
    args = parser.parse_args()

    ok, _ = check_artist(args.artist, max_artworks=args.max, delay=args.delay)
    sys.exit(0 if ok else 1)