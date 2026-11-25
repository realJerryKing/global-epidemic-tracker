import csv
import io
import re
from datetime import date
from ..models import OutbreakReport, SourceType, count
from ..models.base import fetch_text
from .who_gho import CENTERS


class OWIDMpoxCollector:
    SOURCE = SourceType.OWID
    CSV_URL = 'https://raw.githubusercontent.com/owid/monkeypox/main/owid-monkeypox-data.csv'
    SOURCE_URL = 'https://github.com/owid/monkeypox'

    def collect(self):
        return self.parse_csv(fetch_text(self.CSV_URL))

    def parse_csv(self, text):
        reader = csv.DictReader(io.StringIO(text))
        required = {'location','iso_code','date','total_cases','total_deaths'}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError('unexpected OWID CSV schema')
        latest = {}
        for row in reader:
            iso = row['iso_code'] or ''
            if not re.fullmatch('[A-Z]{3}', iso):
                continue  # OWID_* regions and world are not countries
            day = date.fromisoformat(row['date']).isoformat()
            if iso in latest and day < latest[iso].period_label:
                continue
            cases, deaths = count(row['total_cases']), count(row['total_deaths'])
            if cases is None and deaths is None:
                continue
            _, lat, lon = CENTERS.get(iso, (None,None,None))
            report = OutbreakReport(f'owid_mpox_{iso}_{day}', 'Mpox', self.SOURCE, self.SOURCE_URL,
                                   'cumulative', day, day, iso, row['location'], lat, lon, cases, deaths)
            if iso in latest and day == latest[iso].period_label and latest[iso] != report:
                raise ValueError('conflicting OWID observations for same ISO and date')
            latest[iso] = report
        return list(latest.values())
