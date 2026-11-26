"""Verify that the public Pages dashboard serves the published official snapshot."""

import argparse
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
import time
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen


class Dashboard(HTMLParser):
    def __init__(self):
        super().__init__()
        self.targets = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'link' and attrs.get('id') == 'official-snapshot':
            self.targets.append(attrs.get('href'))


def snapshot_target(html, dashboard_url, expected_url):
    page = Dashboard()
    page.feed(html)
    if len(page.targets) != 1 or not page.targets[0]:
        raise ValueError('dashboard must declare exactly one official-snapshot link')
    target = urljoin(dashboard_url, page.targets[0])
    if target != expected_url:
        raise ValueError(f'dashboard snapshot path is {target!r}, expected {expected_url}')
    return target


def snapshot_info(snapshot, now, max_age):
    if snapshot.get('schema_version') != 2 or snapshot.get('legacy') is not False:
        raise ValueError('expected a live v2 snapshot, not a legacy export')
    rows = snapshot['outbreaks']
    count = snapshot['summary']['report_count']
    if type(count) is not int or not isinstance(rows, list) or not rows or len(rows) != count:
        raise ValueError('snapshot has inconsistent report count')
    stamp = datetime.fromisoformat(snapshot['last_update'])
    if stamp.utcoffset() is None or stamp > now + timedelta(minutes=5):
        raise ValueError('snapshot timestamp is invalid')
    if now - stamp > max_age:
        raise ValueError(f'snapshot is stale: collected at {stamp.isoformat()}, maximum age {max_age}')
    return stamp, count


def verify(html, live, expected, dashboard_url, expected_url, now, max_age):
    snapshot_target(html, dashboard_url, expected_url)
    stamp, count = snapshot_info(live, now, max_age)
    expected_stamp, _ = snapshot_info(expected, now, max_age)
    if live != expected:
        raise ValueError(f'public snapshot differs from the published file (public {stamp.isoformat()}, '
                         f'repository {expected_stamp.isoformat()})')
    return stamp, count


def fetch(url):
    request = Request(f'{url}?{urlencode({"verify": time.time_ns()})}', headers={
        'Cache-Control': 'no-cache', 'User-Agent': 'global-epidemic-tracker-pages-verifier',
    })
    with urlopen(request, timeout=20) as response:
        # Validate the effective URL too; a successful redirect may serve an old file.
        if response.url.split('?', 1)[0] != url:
            raise ValueError(f'unexpected redirect for {url}: {response.url}')
        return response.read().decode('utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site', default='https://realjerryking.github.io/global-epidemic-tracker/')
    parser.add_argument('--dashboard', required=True, help='Path to the deployed dashboard, relative to site root')
    parser.add_argument('--expected-file', type=Path, default=Path('data/v2/epidemics.json'))
    parser.add_argument('--max-age-hours', type=float, default=15)
    parser.add_argument('--attempts', type=int, default=1)
    parser.add_argument('--retry-delay', type=int, default=30)
    args = parser.parse_args()
    site = args.site.rstrip('/') + '/'
    dashboard_url = urljoin(site, args.dashboard)
    expected_url = urljoin(site, 'data/v2/epidemics.json')
    expected = json.loads(args.expected_file.read_text(encoding='utf-8'))
    max_age = timedelta(hours=args.max_age_hours)
    for attempt in range(1, args.attempts + 1):
        try:
            html = fetch(dashboard_url)
            target = snapshot_target(html, dashboard_url, expected_url)
            stamp, count = verify(html, json.loads(fetch(target)), expected, dashboard_url,
                                  expected_url, datetime.now(timezone.utc), max_age)
        except (OSError, ValueError, AttributeError, KeyError, TypeError) as exc:
            print(f'Attempt {attempt}/{args.attempts}: {exc}', flush=True)
            if attempt < args.attempts:
                time.sleep(args.retry_delay)
        else:
            print(f'{target} matches the published snapshot: {stamp.isoformat()}, {count} reports')
            return 0
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
