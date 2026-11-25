# Official-source report snapshot (schema 2)

`epidemics.json` is the canonical published dataset. `epidemics.geojson` contains the subset with approximate country centers; these are not outbreak sites. The JSON `outbreaks` key is retained for web compatibility. Its elements are **source records**, not inferred active outbreaks, individuals or diagnoses. `summary.report_count` counts distinct `(source, outbreak_id)` pairs. Never add counts across these records or derive a global CFR.

| source | period_type | What each row means |
|---|---|---|
| `who_don` | `publication` | [WHO notice](https://www.who.int/emergencies/disease-outbreak-news); the date is publication, not onset. Counts, severity, and transmission are not inferred from prose. |
| `who_gho` | `annual` | Country-year count for the named [GHO indicator](https://ghoapi.azureedge.net/api/Indicator); `period_label` is the year, `date_reported` and deaths are null. |
| `owid` | `cumulative` | Latest available cumulative [mpox observation via OWID](https://github.com/owid/monkeypox) for each country, as of its own observation date, not that day's incidence. |

Counts are nullable nonnegative integers. `null` means unavailable or withheld, not zero. Search results (when requested) are links labeled `unreviewed_search_result`, not independent confirmations or counts. Source date and publication snapshot time (`last_update`, UTC) are separate. `coverage` describes limits; these records are not representative surveillance or a complete sample.

## Archived export

The initial v2 pair was migrated from `docs/data/epidemics.json` at revision `e4e5875b4ef0d233e18c632b68dbc1b04dab96e0`. `legacy: true` on snapshot and rows marks archived values, not a fresh upstream pull. The migration retains the old export timestamp and records the SHA-256 of the input bytes (line endings affect this hash). It drops non-country aggregates, reclassifies GHO rows by identifier, withholds ambiguous OWID zero deaths and all narrative-derived DON counts and locations. DON disease labels come from the archive and were not independently adjudicated.

To reproduce in a POSIX shell:

```sh
git show e4e5875b4ef0d233e18c632b68dbc1b04dab96e0:docs/data/epidemics.json > legacy-input.json
python scripts/normalize_legacy.py legacy-input.json --output-dir /tmp/normalized-reports
```

For a fresh capture run `python scripts/fetch_data.py --fetch --export-json --summary`. Both formats are generated from one in-memory snapshot; the workflow publishes only after every required feed (including every configured GHO indicator) succeeds. No community data is part of this artifact.
