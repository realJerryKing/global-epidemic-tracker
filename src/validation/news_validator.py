"""Optional search results are links for human review, never count corroboration."""
from urllib.parse import urlsplit
from xml.etree import ElementTree
from ..models.base import fetch_text


class NewsValidator:
    def search(self, report):
        xml = fetch_text('https://news.google.com/rss/search', {
            'q': f'{report.disease} {report.location} {report.period_label[:4]}',
            'hl': 'en', 'gl': 'US', 'ceid': 'US:en'})
        evidence = {}
        for item in ElementTree.fromstring(xml).findall('./channel/item')[:5]:
            url = item.findtext('link') or ''
            title = item.findtext('title') or ''
            if title and urlsplit(url).scheme == 'https' and urlsplit(url).hostname:
                evidence[url] = {'title': title, 'url': url, 'publisher': item.findtext('source'),
                                 'published': item.findtext('pubDate'), 'type': 'unreviewed_search_result'}
        return list(evidence.values())
