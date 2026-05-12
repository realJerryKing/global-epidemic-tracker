#!/usr/bin/env python3
import argparse
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.collectors.aggregator import EpidemicAggregator


def main():
    parser = argparse.ArgumentParser(description="Global Epidemic Tracker - Data Pipeline")
    parser.add_argument("--fetch", action="store_true", help="Fetch latest data from WHO DON")
    parser.add_argument("--validate", action="store_true", default=True, help="Cross-validate with news")
    parser.add_argument("--no-validate", action="store_true", help="Skip news validation")
    parser.add_argument("--max-validations", type=int, default=15, help="Max outbreaks to validate")
    parser.add_argument("--export-json", action="store_true", help="Export JSON")
    parser.add_argument("--export-geojson", action="store_true", help="Export GeoJSON")
    parser.add_argument("--output-dir", default="data/processed/", help="Output directory")
    parser.add_argument("--summary", action="store_true", help="Print summary")
    parser.add_argument("--disease", type=str, help="Filter by disease")
    parser.add_argument("--country", type=str, help="Filter by country ISO3")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    if not any([args.fetch, args.export_json, args.export_geojson, args.summary]):
        args.fetch = True
        args.summary = True
        args.export_json = True
        args.export_geojson = True

    agg = EpidemicAggregator(cache_dir="data/cache")

    validate = not args.no_validate
    print("Fetching data from WHO Disease Outbreak News...")
    agg.fetch_all(validate=validate, max_validations=args.max_validations)

    outbreaks = agg.get_outbreaks(disease=args.disease, country=args.country)

    if args.json:
        print(json.dumps([o.to_dict() for o in outbreaks], indent=2, default=str))
        return

    if args.summary:
        summary = agg.get_global_summary()
        print()
        print("=" * 65)
        print("  GLOBAL EPIDEMIC TRACKER - SUMMARY")
        print("=" * 65)
        print(f"  Active Outbreaks:    {summary.total_active_outbreaks}")
        print(f"  Total Cases:         {summary.total_cases:,}")
        print(f"  Total Deaths:        {summary.total_deaths:,}")
        print(f"  Global CFR:          {summary.global_cfr:.2%}")
        print(f"  Countries Affected:  {summary.countries_affected}")
        print(f"  Diseases Tracked:    {len(summary.diseases_tracked)}")
        print(f"  Highest Severity:    {summary.highest_severity.value}")
        print(f"  Last Update:         {summary.last_update.strftime('%Y-%m-%d %H:%M UTC')}")
        print()

        print("  DISEASES:")
        for disease, data in agg.get_disease_summary().items():
            h2h = " [H2H]" if data["h2h_transmission"] else ""
            print(f"    {disease:30s} {data['cases']:>7,} cases  {data['deaths']:>5,} deaths  "
                  f"CFR {data['cfr']:.1%}  {data['outbreaks']} outbreaks  {data['countries']} countries{h2h}")

        print()
        print("  TOP OUTBREAKS:")
        for o in sorted(outbreaks, key=lambda x: -x.cases)[:15]:
            v = "✓" if o.news_verified else "?"
            h2h = " [H2H]" if o.h2h_transmission else ""
            print(f"    {v} {o.disease:25s} | {o.location:20s} | {o.cases:>7,} cases | "
                  f"{o.deaths:>5,} deaths | {o.severity.value:10s}{h2h}")
            if o.news_summary:
                print(f"      News: {o.news_summary[:100]}")

        val_summary = agg.get_validation_summary()
        print()
        print(f"  NEWS VALIDATION: {val_summary['verified']}/{val_summary['total_validated']} verified "
              f"({val_summary['verification_rate']})")

    if args.export_json:
        path = agg.to_json(f"{args.output_dir}/epidemics.json")
        print(f"\n  JSON: {path}")

    if args.export_geojson:
        path = agg.to_geojson(f"{args.output_dir}/epidemics.geojson")
        print(f"  GeoJSON: {path}")

    import shutil
    site_data = Path(__file__).parent.parent / "docs" / "data"
    site_data.mkdir(parents=True, exist_ok=True)
    if Path(f"{args.output_dir}/epidemics.json").exists():
        shutil.copy2(f"{args.output_dir}/epidemics.json", site_data / "epidemics.json")
    if Path(f"{args.output_dir}/epidemics.geojson").exists():
        shutil.copy2(f"{args.output_dir}/epidemics.geojson", site_data / "epidemics.geojson")
    print(f"  Dashboard data copied to {site_data}/")


if __name__ == "__main__":
    main()
