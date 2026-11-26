"""All fixtures are local; no upstream request is made by these tests."""
import io
import json
import unittest
from contextlib import redirect_stderr
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
from scripts import fetch_data
from src.collectors.aggregator import geojson, snapshot
from src.collectors.who_don import WHODONCollector
from src.collectors.who_gho import WHOGHOCollector
from src.collectors.owid import OWIDMpoxCollector
from src.models import count
from src.models.base import fetch_rows
from src.validation.news_validator import NewsValidator


class OfficialTests(unittest.TestCase):
    def notice(self, **updates):
        row = {'Title':'Cholera - China', 'PublicationDate':'2024-01-03T00:00:00Z',
               'UrlName':'2024-DON1', 'Summary':'32 suspected cases. No evidence of human-to-human transmission.'}
        return WHODONCollector()._parse_item({**row, **updates})

    def test_narrative_not_machine_counts(self):
        r = self.notice()
        self.assertEqual((r.period_type, r.country_iso3), ('publication', 'CHN'))
        self.assertEqual((r.cases, r.deaths), (None, None))
        self.assertNotIn('h2h_transmission', r.to_dict())
        self.assertIsNone(self.notice(Title='Cholera - Multi-country', Summary='China: 12 cases').latitude)
        with self.assertRaises(ValueError):
            self.notice(PublicationDate='unknown')

    def test_id_dedup_keeps_distinct_same_month_notices(self):
        a = self.notice()
        b = self.notice(UrlName='2024-DON2')
        data = snapshot([a, b, a], '2024-01-04')
        self.assertEqual(data['summary']['report_count'], 2)
        self.assertEqual(data['summary']['by_source'], {'who_don':2})
        self.assertEqual(data['summary']['sources']['who_don']['record_count'], 2)
        self.assertEqual(data['summary']['sources']['who_don']['period_start'], '2024-01-03')
        self.assertEqual(data['summary']['sources']['who_don']['status'], 'success')
        self.assertEqual(data['summary']['sources']['who_gho']['status'], 'empty')
        with self.assertRaisesRegex(ValueError, 'conflicting'):
            snapshot([a, replace(a, description='different')], '2024-01-04')

    def test_explicit_annual_zero_not_missing_deaths(self):
        row = dict(spatialDim='CHN', spatialDimType='COUNTRY', timeDim=2024, timeDimType='YEAR',
                   numericValue=0, indicatorCode='WHS3_62')
        parse = lambda row: WHOGHOCollector()._parse_row(row,'Measles','WHS3_62')
        r = parse(row)
        self.assertEqual((r.source.value, r.period_label, r.cases, r.deaths, r.date_reported),
                         ('who_gho','2024',0,None,None))
        self.assertIsNone(parse({**row,'spatialDimType':'REGION'}))
        self.assertIsNone(parse({**row,'numericValue':None}))
        self.assertIsNone(parse({**row,'dim1':'SEX_FEMALE'}))
        with patch('src.collectors.who_gho.fetch_rows', return_value=[]):
            collector = WHOGHOCollector()
            self.assertEqual(collector.collect(), [])
            self.assertEqual(collector.indicator_metadata['WHS3_62'], {
                'record_count': 0, 'period_start': None, 'period_end': None, 'status': 'empty'})
        with patch('src.collectors.who_gho.fetch_rows', return_value=[{'spatialDim':'CHN'}]), self.assertRaisesRegex(ValueError, 'incomplete GHO record for WHS3_62'):
            WHOGHOCollector().collect()

    def test_fetch_rows_rejects_invalid_envelopes(self):
        for payload in ('{}', '{"value":null}', '{"value":{}}', '{"value":[null]}'):
            with self.subTest(payload=payload), patch('src.models.base.fetch_text', return_value=payload), self.assertRaisesRegex(ValueError, 'array of source records'):
                fetch_rows('https://example.invalid')

    def test_latest_cumulative_per_country(self):
        csv = ('location,iso_code,date,total_cases,total_deaths\nChina,CHN,2024-01-03,2,\n'
               'China,CHN,2024-01-02,5,1\nWorld,OWID_WRL,2024-01-04,800,3\n'
               'Australia,AUS,2024-01-02,0,0\n')
        china, aus = OWIDMpoxCollector().parse_csv(csv)
        self.assertEqual((china.cases, china.deaths, china.period_type, china.date_reported), (2, None, 'cumulative','2024-01-03'))
        self.assertEqual((aus.cases, aus.deaths), (0,0))
        for bad in ('1.5',-1,'NaN','Infinity','hi',True,2**53):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                count(bad)

    def test_news_is_unreviewed_evidence_only(self):
        xml = '<rss><channel><item><title>20 cases?</title><link>https://example.org/a</link><source>A</source></item><item><title>B</title><link>javascript:alert(1)</link></item></channel></rss>'
        with patch('src.validation.news_validator.fetch_text', return_value=xml):
            r = self.notice()
            links = NewsValidator().search(r)
        self.assertEqual([(l['type'],l['url']) for l in links], [('unreviewed_search_result','https://example.org/a')])
        self.assertIsNone(r.cases)

    def test_missing_required_source_preserves_both_outputs(self):
        directory = Path(__file__).resolve().parents[1] / 'docs/data'
        before = {p:p.read_bytes() for p in directory.glob('epidemics.*json')}
        with patch.object(WHODONCollector,'collect',return_value=[self.notice()]), patch.object(WHOGHOCollector,'collect',side_effect=ValueError('source unavailable')), patch.object(fetch_data,'publish') as publish, redirect_stderr(io.StringIO()) as err:
            self.assertEqual(fetch_data.main(['--export-json']), 1)
        self.assertIn('who_gho',err.getvalue())
        publish.assert_not_called()
        self.assertEqual(before,{p:p.read_bytes() for p in before})

    def test_checked_in_pair(self):
        directory = Path(__file__).resolve().parents[1] / 'docs/data'
        data = json.loads((directory/'epidemics.json').read_text(encoding='utf-8'))
        geo = json.loads((directory/'epidemics.geojson').read_text(encoding='utf-8'))
        self.assertEqual(geo, geojson(data))
        rows = data['outbreaks']
        self.assertEqual(len(rows), len({(r['source'],r['outbreak_id']) for r in rows}))
        self.assertEqual(data['summary']['report_count'],len(rows))
        self.assertEqual(set(data['summary']['by_source']), {'who_gho','who_don','owid'})
        if 'sources' in data['summary']:
            self.assertEqual(set(data['summary']['sources']), {'who_gho','who_don','owid'})
            if data['legacy']:
                self.assertTrue(all(s['status'] == 'archived' for s in data['summary']['sources'].values()))
            else:
                self.assertTrue(all(s['status'] in ('success', 'empty') for s in data['summary']['sources'].values()))
                self.assertEqual(data['summary']['sources']['who_gho']['indicators']['WHS3_49']['status'], 'empty')
        self.assertTrue(all(r['legacy'] == data['legacy'] and 'cfr' not in r for r in rows))
        self.assertTrue(all(f['geometry']['coordinates'] != [0,0] for f in geo['features']))
        self.assertTrue(all(r['deaths'] is None and r['cases'] is None for r in rows if r['source']=='who_don'))
