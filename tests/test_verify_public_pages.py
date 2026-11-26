from datetime import datetime, timedelta, timezone
import unittest

from scripts.verify_public_pages import verify


class PublicPagesTest(unittest.TestCase):
    dashboard = 'https://example.org/tracker/docs/v2.html'
    target = 'https://example.org/tracker/data/v2/epidemics.json'
    html = '<link id="official-snapshot" href="../data/v2/epidemics.json">'
    now = datetime(2026, 11, 26, 12, tzinfo=timezone.utc)
    max_age = timedelta(hours=15)

    def setUp(self):
        self.snapshot = {'schema_version': 2, 'legacy': False,
                         'last_update': '2026-11-26T08:00:00+00:00',
                         'summary': {'report_count': 1}, 'outbreaks': [{'id': 'record'}]}

    def check(self, *, html=None, live=None, expected=None):
        return verify(self.html if html is None else html,
                      self.snapshot if live is None else live,
                      self.snapshot if expected is None else expected,
                      self.dashboard, self.target, self.now, self.max_age)

    def test_matches_live_snapshot(self):
        stamp, count = self.check()
        self.assertEqual(self.now - stamp, timedelta(hours=4))
        self.assertEqual(count, 1)

    def test_rejects_old_path_even_when_body_matches(self):
        with self.assertRaisesRegex(ValueError, 'snapshot path'):
            self.check(html=self.html.replace('/v2', ''))

    def test_rejects_missing_or_duplicate_target(self):
        for html in ('', self.html * 2):
            with self.subTest(html=html), self.assertRaisesRegex(ValueError, 'exactly one'):
                self.check(html=html)

    def test_rejects_different_content_even_when_timestamp_and_count_match(self):
        with self.assertRaisesRegex(ValueError, 'differs'):
            self.check(live=dict(self.snapshot, outbreaks=[{'id': 'different'}]))

    def test_rejects_stale_even_when_live_and_repo_match(self):
        self.snapshot['last_update'] = '2026-11-25T19:00:00+00:00'
        with self.assertRaisesRegex(ValueError, 'stale'):
            self.check()

    def test_rejects_nonlive_snapshot(self):
        for change in ({'schema_version': 1}, {'legacy': True}, {'outbreaks': []},
                       {'last_update': '2026-11-27T00:00:00+00:00'},
                       {'last_update': '2026-11-26T08:00:00'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.check(live=dict(self.snapshot, **change))


if __name__ == '__main__':
    unittest.main()
