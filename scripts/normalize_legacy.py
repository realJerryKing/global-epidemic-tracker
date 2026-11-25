"""One-time offline migration of a pre-v2 JSON export, not a fresh source fetch."""
import argparse
import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path
from fetch_data import publish
from src.collectors.aggregator import snapshot
from src.collectors.who_don import article_url
from src.collectors.who_gho import CENTERS, GHO_INDICATORS, WHOGHOCollector
from src.collectors.owid import OWIDMpoxCollector
from src.models import OutbreakReport, SourceType, count
import re


def normalize(raw):
    old = json.loads(raw)
    if 'schema_version' in old:
        raise ValueError('expected a pre-v2 export')
    reports = []
    codes = {d:c for c,d in GHO_INDICATORS.items()}
    for r in old['outbreaks']:
        ident, disease, iso = r['outbreak_id'], r['disease'], r['country_iso3']
        day = date.fromisoformat(r['date_reported']).isoformat()
        kwargs = {'legacy': True}
        if ident.startswith('gho_') or r['source'] == 'owid':
            if not re.fullmatch('[A-Z]{3}', iso) or iso in {'AFR','AMR','EMR','EUR','WPR'}:
                continue  # archive also included income groups, regions and World
            name, lat, lon = CENTERS.get(iso, (r['location'], None, None))
            kwargs.update(country_iso3=iso, location=name, latitude=lat, longitude=lon, cases=count(r['cases']))
            if ident.startswith('gho_'):
                source, period, label = SourceType.WHO_GHO, 'annual', day[:4]
                url = f'{WHOGHOCollector.BASE_URL}/{codes[disease]}'
            else:
                source, period, label = SourceType.OWID, 'cumulative', day
                url = OWIDMpoxCollector.SOURCE_URL
                kwargs.update(date_reported=day, deaths=count(r['deaths']) or None)
        else:
            if r['source'] != 'who_don':
                raise ValueError('unexpected archived source')
            source, period, label = SourceType.WHO_DON, 'publication', day
            url = article_url(ident)
            kwargs.update(date_reported=day, description=r['description'])
        reports.append(OutbreakReport(ident, disease, source, url, period, label, **kwargs))
    stamp = datetime.fromisoformat(old['last_update'])
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)  # pre-v2 exporter used utcnow()
    data = snapshot(reports, stamp.isoformat(), legacy=True)
    data['legacy_input_sha256'] = hashlib.sha256(raw).hexdigest()
    return data


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('input', type=Path)
    p.add_argument('--output-dir', required=True, type=Path)
    args = p.parse_args()
    publish(normalize(args.input.read_bytes()), args.output_dir)
