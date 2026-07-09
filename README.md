# AIC API Field Audit — Rembrandt van Rijn

Scripts and findings from auditing the Art Institute of Chicago API
(`api.artic.edu`) for null/missing fields, to decide how the overview and
detail screens should handle missing data.

## Scripts

- **`overview_fields_validators.py`** — walks all pages of `/artworks/search` for an
  artist and checks each result for null/empty `title`, `image_id`, or
  `date_display` (the fields the overview grid needs).
- **`check_detail_fields.py`** — fetches the full `/artworks/{id}` record for
  every work by an artist and checks `title`, `artist_display`,
  `date_display`, `medium_display`, `dimensions`, `place_of_origin`,
  `credit_line`, `image_id`, and `short_description`/`description` (the
  fields the detail screen needs).
- **`print_sample_description.py`** — scans an artist's works and prints the
  first one that actually has a `short_description` or `description`, to see
  what the field looks like in practice.

Run with: `python <script>.py "Artist Name"`

## Results — Rembrandt van Rijn (247 artworks)

### Overview fields (title, image_id, date_display)

245 / 247 clean. Two exceptions:

| id | issue |
|---|---|
| 49156 | `date_display` is null (title, image_id present) |
| 49212 | `image_id` is null (title, date_display present) |

**Conclusion:** overview data is reliable. Just guard for these two edge
cases — a fallback label (e.g. "Date unknown") when `date_display` is
missing, and skip/placeholder the cell when `image_id` is missing.

### Detail fields

`artist_display`, `date_display`, `medium_display`, `dimensions`,
`place_of_origin`, `credit_line`, and `image_id` are reliably present
(same two exceptions as above, no new issues).

`short_description` / `description` are missing on **218 / 247 (88%)** of
artworks. This isn't a data quality bug — it reflects how the museum
curates the collection: descriptive text is only written for a small
subset of "highlighted" works (`is_boosted: true`), not for the bulk of
the collection (most prints/studies never get editorial text).

**Conclusion:** treat `short_description`/`description` as optional,
enhancement-only content on the detail screen:
- Prefer `short_description`, fall back to `description` if the former is
  absent.
- If neither field is present, omit the section entirely rather than
  showing an empty box or a "no description" placeholder.
- Build the detail layout around the fields that are consistently
  present (artist, date, medium, dimensions, place of origin, credit
  line); treat the description as a bonus paragraph, not the anchor of
  the screen.

## Caveat

Results are specific to Rembrandt van Rijn. Field completeness likely
varies by artist/collection — worth spot-checking with
`check_detail_fields.py --max 30` before assuming the same ratios hold
for whichever artist ships in the final app.
