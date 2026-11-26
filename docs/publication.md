# Official snapshot publication

- [Current dashboard](https://realjerryking.github.io/global-epidemic-tracker/docs/v2.html) and the DSH sidebar share [the v2 JSON endpoint](https://realjerryking.github.io/global-epidemic-tracker/data/v2/epidemics.json). The dashboard's `official-snapshot` link declares the path consumed by its JavaScript.
- [The original dashboard](https://realjerryking.github.io/global-epidemic-tracker/) and legacy integrations remain on their existing data format. Do not write v2 content over a legacy endpoint.
- Snapshot time describes collection, not when the reported events happened. The report count mixes notices and observations, not comparable case totals. No community check-in service is published by this workflow.

## Verification and recovery

[Update Epidemic Data](https://github.com/realJerryKing/global-epidemic-tracker/actions/workflows/update-data.yml) is scheduled every six hours. [Verify public epidemic dashboard](https://github.com/realJerryKing/global-epidemic-tracker/actions/workflows/verify-public-pages.yml) checks the public path and content, waits briefly for CDN and Pages propagation, and verifies that Chromium renders the same snapshot. The independent schedule checks freshness even if a collection or deployment does not happen. A snapshot older than 15 hours fails verification; an unchanged reporting period in a freshly collected source is not a failure.

1. Check the latest collection and verifier runs. Read the failing step's output; a collection failure should leave its last usable snapshot available.
2. For a public/repository mismatch, compare the latest Pages deployment revision with `main`. Use the workflow's **Run workflow** button to retry verification after deployment. For a path mismatch, check both the dashboard link and the actual browser network request.
3. For a stale snapshot, inspect the collector log, fix the failing source/transport, and dispatch **Update Epidemic Data**. Do not edit timestamps or publish empty data to silence the verifier.

Failures are visible as red Actions runs. Maintainers who need delivery outside the Actions page should enable their GitHub Actions notifications.
