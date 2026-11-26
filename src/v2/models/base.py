"""HTTP helpers. HTTP, network and schema errors must reach the refresh command."""
import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def fetch_text(url, params=None):
    if params:
        url += '?' + urlencode(params)
    req = Request(url, headers={'User-Agent': 'GlobalEpidemicTracker/2.0'})
    with urlopen(req, timeout=45) as response:
        return response.read().decode('utf-8-sig')


def fetch_rows(url, params=None):
    payload = json.loads(fetch_text(url, params))
    rows = payload.get('value') if isinstance(payload, dict) else payload
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise ValueError('expected an array of source records')
    return rows
