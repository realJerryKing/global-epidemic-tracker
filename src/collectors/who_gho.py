import re
from datetime import date
from ..models import OutbreakReport, SourceType, count
from ..models.base import fetch_rows
from .locations import COUNTRY_COORDS

GHO_INDICATORS = {'WHS3_62': 'Measles', 'WHS3_41': 'Diphtheria', 'WHS3_50': 'Yellow Fever',
                  'WHS3_49': 'Poliomyelitis', 'WHS3_56': 'Neonatal Tetanus', 'WHS3_57': 'Rubella',
                  'WHS3_53': 'Mumps', 'WHS3_42': 'Japanese Encephalitis'}
CENTERS = {iso: (name.title(), lat, lon) for name, (iso, lat, lon) in COUNTRY_COORDS.items()}


class WHOGHOCollector:
    SOURCE = SourceType.WHO_GHO
    BASE_URL = 'https://ghoapi.azureedge.net/api'

    def collect(self):
        reports = []
        self.indicator_metadata = {}
        for code, disease in GHO_INDICATORS.items():
            rows = fetch_rows(f'{self.BASE_URL}/{code}', {
                '$filter': "SpatialDimType eq 'COUNTRY' and TimeDim ge 2023 and NumericValue ne null",
                '$orderby': 'TimeDim desc,SpatialDim asc', '$top': 250})
            group = [r for row in rows if (r := self._parse_row(row, disease, code))]
            if rows and not group:
                raise ValueError(f'no usable country-year records for {code}')
            self.indicator_metadata[code] = {
                'record_count': len(group),
                'period_start': min((r.period_label for r in group), default=None),
                'period_end': max((r.period_label for r in group), default=None),
                'status': 'success' if group else 'empty',
            }
            # An HTTP-successful empty collection means no observations, not zero cases.
            reports.extend(group)
        return reports

    def _parse_row(self, row, disease, code):
        row = {k.lower():v for k,v in row.items()}
        iso = row['spatialdim']
        if row['spatialdimtype'] != 'COUNTRY' or row['timedimtype'] != 'YEAR' or any(row.get(f'dim{i}') for i in (1,2,3)):
            return None
        if not re.fullmatch('[A-Z]{3}', iso) or row['indicatorcode'] != code:
            raise ValueError(f'unexpected GHO dimensions for {code}')
        year = str(row['timedim'])
        if not re.fullmatch(r'\d{4}', year) or int(year) > date.today().year:
            raise ValueError('invalid GHO reporting year')
        cases = count(row['numericvalue'])
        if cases is None:
            return None
        name, lat, lon = CENTERS.get(iso, (iso,None,None))
        return OutbreakReport(f'gho_{iso}_{disease}_{year}', disease, self.SOURCE, f'{self.BASE_URL}/{code}',
                             'annual', year, country_iso3=iso, location=name, latitude=lat, longitude=lon, cases=cases)
