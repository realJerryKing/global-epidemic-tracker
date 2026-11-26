from collections import Counter
from datetime import datetime, timezone
from urllib.error import URLError
from xml.etree.ElementTree import ParseError
from .who_don import WHODONCollector
from .who_gho import WHOGHOCollector
from .owid import OWIDMpoxCollector
from ..validation.news_validator import NewsValidator


SOURCE_URLS = {
    'who_don': WHODONCollector.API_URL,
    'who_gho': WHOGHOCollector.BASE_URL,
    'owid': OWIDMpoxCollector.CSV_URL,
}


def snapshot(reports, timestamp, *, legacy=False, gho_indicators=None):
    unique = {}
    for report in reports:
        key = report.source, report.outbreak_id
        if key in unique and unique[key] != report:
            raise ValueError(f'conflicting records with identifier {key}')
        unique[key] = report
    rows = [r.to_dict() for r in sorted(unique.values(), key=lambda r: (r.source.value, r.outbreak_id))]
    counts = Counter(r['source'] for r in rows)
    provenance = {}
    for source, url in SOURCE_URLS.items():
        source_rows = [r for r in rows if r['source'] == source]
        periods = [r['period_label'] for r in source_rows if r['period_label']]
        provenance[source] = {'url': url, 'record_count': len(source_rows),
                              'period_type': source_rows[0]['period_type'] if source_rows else None,
                              'period_start': min(periods) if periods else None,
                              'period_end': max(periods) if periods else None,
                              'status': 'archived' if legacy else ('success' if source_rows else 'empty')}
        if source == 'who_gho' and not legacy:
            provenance[source]['indicators'] = gho_indicators or {}
    return {'schema_version': 2, 'legacy': legacy, 'last_update': timestamp,
            'coverage': ('Normalized from an archived export; not independently re-fetched. Legacy DON classifications are approximate; location and extracted counts withheld. Legacy OWID zero deaths may represent missing data and are withheld.' if legacy else
                         'Bounded sample: up to 500 latest WHO DON notices, up to 250 country-year observations since 2023 per WHO GHO indicator, latest available cumulative WHO/OWID mpox observation per country.'),
            'summary': {'report_count': len(rows), 'by_source': dict(counts), 'sources': provenance},
            'outbreaks': rows}


def geojson(data):
    return {'type':'FeatureCollection', 'last_update':data['last_update'], 'legacy':data['legacy'],
            'features':[{'type':'Feature','id':r['outbreak_id'], 'properties':r,
                         'geometry':{'type':'Point','coordinates':[r['longitude'], r['latitude']]}}
                        for r in data['outbreaks'] if r['latitude'] is not None and r['longitude'] is not None]}


class EpidemicAggregator:
    def __init__(self):
        self.collectors = [WHODONCollector(), WHOGHOCollector(), OWIDMpoxCollector()]

    def fetch_all(self, validate=False, max_validations=15):
        rows = []
        for collector in self.collectors:
            try:
                group = collector.collect()
                if not group:
                    raise ValueError('empty response')
            except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
                raise ValueError(f'{collector.SOURCE.value}: {exc}') from exc
            rows.extend(group)
        if validate:
            search = NewsValidator()
            for r in rows[:max(0, max_validations)]:
                try:
                    r.news_evidence = search.search(r)
                except (URLError, OSError, ParseError, ValueError):
                    pass  # Optional discovery failure is not evidence against a report.
        return snapshot(rows, datetime.now(timezone.utc).isoformat(timespec='seconds'),
                        gho_indicators=self.collectors[1].indicator_metadata)
