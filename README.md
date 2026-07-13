# AIC API Field Audit — Rembrandt van Rijn

Scripts and findings from auditing the Art Institute of Chicago API
(`api.artic.edu`) to validate field completeness and determine how the
overview and detail screens should handle missing data.

## Scripts

- **`overview_fields_validators.py`** — walks all pages of `/artworks/search`
  for an artist and checks each result for null/empty `title`, `image_id`,
  or `date_display` (the fields required by the overview screen).
- **`check_detail_fields.py`** — fetches the full `/artworks/{id}` record for
  every work by an artist and checks `title`, `artist_display`,
  `date_display`, `medium_display`, `dimensions`, `place_of_origin`,
  `credit_line`, `image_id`, and `short_description`/`description`
  (the fields used by the detail screen).
- **`print_sample_description.py`** — scans an artist's works and prints the
  first one that contains descriptive text to inspect the API response.

Run with:

```bash
python <script>.py "Artist Name"
```

## Results — Rembrandt van Rijn (247 artworks)

### Overview fields (`title`, `image_id`, `date_display`)

**245 / 247 artworks (99.2%)** contain all required overview fields.

| Artwork ID | Issue |
| ---------- | ----- |
| 49156 | `date_display` is null |
| 49212 | `image_id` is null |

**Conclusion:** Overview data is highly reliable. The UI only needs two
safeguards:

- Show a fallback value (e.g. *"Date unknown"*) when `date_display` is missing.
- Display a placeholder or omit the image when `image_id` is missing.

### Detail fields

`artist_display`, `date_display`, `medium_display`, `dimensions`,
`place_of_origin`, `credit_line`, and `image_id` are consistently present,
aside from the two exceptions already identified above.

#### Description coverage

| Status | Count |
| ----------- | -----: |
| `description` present, `short_description` missing | 27 |
| Both `description` and `short_description` present | 2 |
| Both missing | 218 |
| At least one description field present | 29 |

Only **29 / 247 artworks (11.7%)** contain descriptive text, while
**218 / 247 artworks (88.3%)** contain neither `short_description`
nor `description`.


**Conclusion:** Treat descriptive text as optional enhancement content:

- Prefer `short_description` when available.
- Fall back to `description` when `short_description` is absent.
- If neither field exists, omit the section entirely.

## Caveat

Results are specific to **Rembrandt van Rijn**. Field completeness may vary
across artists and collections, so it is worth running a smaller audit
(e.g. `check_detail_fields.py --max 30`) before assuming the same ratios
apply elsewhere.
