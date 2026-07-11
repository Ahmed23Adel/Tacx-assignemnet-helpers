"""
Scans artwork description / short_description fields from the AIC API and
reports every distinct HTML tag found, with counts and example snippets —
so you know exactly which tags HTMLText.swift needs to handle.

Usage:
    python find_html_tags.py "Rembrandt van Rijn"
    python find_html_tags.py --sample 500          # random-ish sample across all artworks
    python find_html_tags.py "Rembrandt van Rijn" --max 50
"""

import argparse
import re
import sys
import time
from collections import Counter, defaultdict
from urllib.parse import urlencode

import requests

SEARCH_URL = "https://api.artic.edu/api/v1/artworks/search"
LIST_URL = "https://api.artic.edu/api/v1/artworks"
DETAIL_URL = "https://api.artic.edu/api/v1/artworks/{id}"

HEADERS = {"AIC-User-Agent": "TacxAssignmentHTMLScan/1.0 (contact: example@example.com)"}

DESCRIPTION_FIELDS = ["short_description", "description"]

# Matches opening tags, closing tags, and self-closing tags, capturing the tag name.
TAG_RE = re.compile(r"</?([a-zA-Z0-9]+)(\s[^>]*)?/?>")


def collect_artist_ids(session: requests.Session, artist: str, page_limit: int = 100) -> list:
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


def collect_sample_ids(session: requests.Session, sample_size: int, page_limit: int = 100) -> list:
    """Pull ids from across the general artworks listing (no artist filter),
    paging until we have enough. Not a true random sample, but spans many
    artists/eras rather than just one."""
    ids = []
    page = 1
    while len(ids) < sample_size:
        params = {"fields": "id", "limit": page_limit, "page": page}
        url = f"{LIST_URL}?{urlencode(params)}"
        resp = session.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        rows = data["data"]
        if not rows:
            break
        ids.extend(row["id"] for row in rows)
        print(f"  collected page {page} ({len(ids)} ids so far)")
        page += 1
    return ids[:sample_size]


def fetch_detail(session: requests.Session, artwork_id: int) -> dict:
    url = DETAIL_URL.format(id=artwork_id)
    resp = session.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json()["data"]


def scan(ids: list, delay: float):
    session = requests.Session()

    tag_counts = Counter()
    tag_examples = defaultdict(list)  # tag -> list of (artwork_id, snippet)
    fields_with_html = 0
    fields_checked = 0

    for i, artwork_id in enumerate(ids, start=1):
        detail = fetch_detail(session, artwork_id)

        for field_name in DESCRIPTION_FIELDS:
            value = detail.get(field_name)
            if not value or not isinstance(value, str):
                continue
            fields_checked += 1

            tags_found = TAG_RE.findall(value)
            if tags_found:
                fields_with_html += 1

            for tag_name, _attrs in tags_found:
                tag_lower = tag_name.lower()
                tag_counts[tag_lower] += 1
                if len(tag_examples[tag_lower]) < 3:
                    # grab a short snippet around the tag for context
                    match = re.search(re.escape(tag_name), value, re.IGNORECASE)
                    start = max(0, (match.start() if match else 0) - 20)
                    snippet = value[start:start + 80].replace("\n", " ")
                    tag_examples[tag_lower].append((artwork_id, snippet))

        if i % 20 == 0 or i == len(ids):
            print(f"  scanned {i}/{len(ids)}")
        time.sleep(delay)

    return tag_counts, tag_examples, fields_checked, fields_with_html


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artist", nargs="?", default=None, help='Artist name, e.g. "Rembrandt van Rijn"')
    parser.add_argument("--max", type=int, default=None, help="Only check the first N artworks")
    parser.add_argument("--sample", type=int, default=None, help="Instead of one artist, sample N artworks across the whole collection")
    parser.add_argument("--delay", type=float, default=0.15, help="Delay between requests, in seconds")
    args = parser.parse_args()

    if not args.artist and not args.sample:
        parser.error("Provide either an artist name or --sample N")

    session = requests.Session()

    if args.artist:
        print(f'Collecting artwork ids for artist: "{args.artist}"\n')
        ids = collect_artist_ids(session, args.artist)
        if args.max:
            ids = ids[: args.max]
    else:
        print(f"Collecting a sample of {args.sample} artwork ids across the collection\n")
        ids = collect_sample_ids(session, args.sample)

    print(f"\nFetching + scanning detail for {len(ids)} artwork(s)...\n")
    tag_counts, tag_examples, fields_checked, fields_with_html = scan(ids, args.delay)

    print(f"\nDescription fields checked: {fields_checked}")
    print(f"Fields containing at least one HTML tag: {fields_with_html}\n")

    if not tag_counts:
        print("No HTML tags found in any description field.")
        sys.exit(0)

    print(f"Distinct tags found ({len(tag_counts)}):\n")
    for tag, count in tag_counts.most_common():
        print(f"  <{tag}>  — {count} occurrence(s)")
        for artwork_id, snippet in tag_examples[tag]:
            print(f"      id={artwork_id}: ...{snippet}...")
        print()


if __name__ == "__main__":
    main()