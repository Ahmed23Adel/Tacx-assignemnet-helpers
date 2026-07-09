"""
Finds and prints ONE artwork by a given artist that actually has a
short_description or description, so you can see what the field looks
like in practice. Stops as soon as it finds one (no need to fetch every
artwork).

Usage:
    python print_sample_description.py "Rembrandt van Rijn"
"""

import argparse
import sys
from urllib.parse import urlencode

import requests

SEARCH_URL = "https://api.artic.edu/api/v1/artworks/search"
DETAIL_URL = "https://api.artic.edu/api/v1/artworks/{id}"

HEADERS = {"AIC-User-Agent": "TacxAssignmentSampleDesc/1.0 (contact: example@example.com)"}


def is_missing(value) -> bool:
    return value is None or (isinstance(value, str) and value.strip() == "")


def iter_artist_ids(session: requests.Session, artist: str, page_limit: int = 100):
    """Yield artwork ids for the artist, page by page, without collecting them all upfront."""
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

        for row in data["data"]:
            yield row["id"]

        total_pages = data["pagination"]["total_pages"]
        if page >= total_pages:
            break
        page += 1


def fetch_detail(session: requests.Session, artwork_id: int) -> dict:
    url = DETAIL_URL.format(id=artwork_id)
    resp = session.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json()["data"]


def find_sample(artist: str):
    session = requests.Session()
    checked = 0

    for artwork_id in iter_artist_ids(session, artist):
        checked += 1
        detail = fetch_detail(session, artwork_id)

        if not is_missing(detail.get("short_description")) or not is_missing(detail.get("description")):
            print(f"Found sample after checking {checked} artwork(s).\n")
            print(f"id: {detail.get('id')}")
            print(f"title: {detail.get('title')}")
            print(f"artist_display: {detail.get('artist_display')}")
            print(f"date_display: {detail.get('date_display')}")
            print(f"\nshort_description:\n{detail.get('short_description')}")
            print(f"\ndescription:\n{detail.get('description')}")
            return detail

        if checked % 20 == 0:
            print(f"  checked {checked} artworks, no description yet...")

    print(f"Checked all {checked} artworks — none had a short_description or description.")
    return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artist", help='Artist name, e.g. "Rembrandt van Rijn"')
    args = parser.parse_args()

    result = find_sample(args.artist)
    sys.exit(0 if result else 1)