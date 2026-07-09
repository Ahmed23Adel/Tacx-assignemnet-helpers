"""
Checks every artwork returned by the Art Institute of Chicago /artworks/search
endpoint for a given artist, looking for null/empty `title`, `image_id`, or
`date_display` fields. Walks all pages using the API's pagination metadata.

Usage:
    python check_null_fields.py "Rembrandt van Rijn"
    python check_null_fields.py "Utagawa Toyoharu" --limit 50
"""

import argparse
import sys
import time
from urllib.parse import urlencode

import requests

BASE_URL = "https://api.artic.edu/api/v1/artworks/search"
FIELDS = "id,title,image_id,date_display,artist_title"

# Fields we require to be non-null / non-empty for the overview screen.
REQUIRED_FIELDS = ["title", "image_id", "date_display"]


def fetch_page(artist: str, page: int, limit: int) -> dict:
    params = {
        "query[match_phrase][artist_title]": artist,
        "fields": FIELDS,
        "limit": limit,
        "page": page,
    }
    url = f"{BASE_URL}?{urlencode(params)}"
    resp = requests.get(
        url,
        headers={"AIC-User-Agent": "TacxAssignmentNullCheck/1.0 (contact: example@example.com)"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def is_missing(value) -> bool:
    """Treat None and empty string as missing."""
    return value is None or (isinstance(value, str) and value.strip() == "")


def check_artist(artist: str, limit: int = 100, delay: float = 0.2):
    print(f'Checking artist: "{artist}"\n')

    page = 1
    total_pages = None
    total_checked = 0
    problem_rows = []

    while True:
        data = fetch_page(artist, page, limit)
        pagination = data["pagination"]
        total_pages = pagination["total_pages"]
        total = pagination["total"]

        for row in data["data"]:
            total_checked += 1
            missing = [f for f in REQUIRED_FIELDS if is_missing(row.get(f))]
            if missing:
                problem_rows.append(
                    {
                        "id": row.get("id"),
                        "title": row.get("title"),
                        "image_id": row.get("image_id"),
                        "date_display": row.get("date_display"),
                        "missing_fields": missing,
                    }
                )

        print(f"  fetched page {page}/{total_pages} ({len(data['data'])} rows)")

        if page >= total_pages:
            break
        page += 1
        time.sleep(delay)  # be polite to the API

    all_clean = len(problem_rows) == 0

    print(f"\nTotal artworks checked: {total_checked} (API reports total={total})")
    print(f"All rows have title, image_id, and date_display: {all_clean}\n")

    if not all_clean:
        print(f"Rows with missing fields ({len(problem_rows)}):")
        for r in problem_rows:
            print(
                f"  id={r['id']:<8} missing={r['missing_fields']!s:<28} "
                f"title={r['title']!r}  image_id={r['image_id']!r}  date_display={r['date_display']!r}"
            )

    return all_clean, problem_rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artist", help='Artist name, e.g. "Rembrandt van Rijn"')
    parser.add_argument("--limit", type=int, default=100, help="Page size (max 100)")
    args = parser.parse_args()

    ok, _ = check_artist(args.artist, limit=args.limit)
    sys.exit(0 if ok else 1)