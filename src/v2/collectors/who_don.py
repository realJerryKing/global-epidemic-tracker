import re
from datetime import datetime
from html import unescape
from urllib.parse import quote
from ..models import OutbreakReport, SourceType
from ..models.base import fetch_rows
from .locations import COUNTRY_COORDS
from .disease_aliases import DISEASE_ALIASES


def article_url(slug):
    return 'https://www.who.int/emergencies/disease-outbreak-news/item/' + quote(slug, safe='')


class WHODONCollector:
    SOURCE = SourceType.WHO_DON
    API_URL = 'https://www.who.int/api/news/diseaseoutbreaknews'

    def collect(self, max_pages=10):
        reports = []
        for page in range(max_pages):
            items = fetch_rows(self.API_URL, {'$orderby': 'PublicationDate desc', '$top': 50, '$skip': 50*page})
            reports.extend(self._parse_item(item) for item in items)
            if len(items) < 50:
                break
        return reports

    def _parse_item(self, item):
        slug = item['UrlName']
        title = unescape(item['Title']).strip()
        if not title or not slug:
            raise ValueError('DON notice missing title or URL identifier')
        day = datetime.fromisoformat(item['PublicationDate'].replace('Z', '+00:00')).date().isoformat()
        parts = re.split(r'\s+[-–—]\s+', title)
        # Only assign geography from an exact country segment in the title. An
        # incidental country in the narrative is not the scope of the report.
        locs = {part.lower(): COUNTRY_COORDS[part.lower()] for part in parts[1:] if part.lower() in COUNTRY_COORDS}
        name, (iso, lat, lon) = next(iter(locs.items())) if len(locs) == 1 and 'multi-country' not in title.lower() else ('Not specified', (None,None,None))
        disease = DISEASE_ALIASES.get(parts[0].lower(), parts[0])
        text = unescape(re.sub(r'<[^>]+>', ' ', item.get('Summary') or ''))
        return OutbreakReport(slug, disease, self.SOURCE, article_url(slug), 'publication', day, day,
                             iso, name.title(), lat, lon, description=' '.join(text.split())[:500])
