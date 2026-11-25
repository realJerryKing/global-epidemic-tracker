#!/usr/bin/env python3
"""Refresh the canonical published observation snapshot (standard library only)."""
import argparse
import json
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.collectors.aggregator import EpidemicAggregator, geojson


def publish(data, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    staged = {}
    try:
        for filename, value in [('epidemics.geojson', geojson(data)), ('epidemics.json', data)]:
            with NamedTemporaryFile('w', encoding='utf-8', dir=directory, delete=False) as tmp:
                staged[directory / filename] = Path(tmp.name)
                json.dump(value, tmp, ensure_ascii=False, indent=2, allow_nan=False)
                tmp.write('\n')
        for target, tmp in staged.items():
            tmp.replace(target)
    finally:
        for tmp in staged.values():
            tmp.unlink(missing_ok=True)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fetch', action='store_true', help='fetch configured sources')
    p.add_argument('--validate', action='store_true', help='attach unreviewed related news links')
    p.add_argument('--no-validate', action='store_true', help='skip optional news lookup (default)')
    p.add_argument('--max-validations', type=int, default=15)
    p.add_argument('--summary', action='store_true', help='print source report counts')
    p.add_argument('--export-json', action='store_true', help='write both matching snapshot formats')
    p.add_argument('--export-geojson', action='store_true', help='write both matching snapshot formats')
    p.add_argument('--output-dir', type=Path, default=ROOT / 'docs/data')
    p.add_argument('--json', action='store_true', help='print snapshot to stdout')
    args = p.parse_args(argv)
    try:
        data = EpidemicAggregator().fetch_all(args.validate and not args.no_validate, args.max_validations)
        if args.export_json or args.export_geojson or not any((args.fetch, args.summary, args.json)):
            publish(data, args.output_dir)
        if args.json:
            print(json.dumps(data))
        elif args.summary or not argv:
            print(json.dumps(data['summary']))
    except (ValueError, OSError) as exc:
        print(f'Refresh failed: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
