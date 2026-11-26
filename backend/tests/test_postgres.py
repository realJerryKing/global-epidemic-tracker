"""Optional staging-only integration test. Uses a new random schema."""
import os
import unittest
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from backend.store import Store, monday


@unittest.skipUnless(os.getenv('TEST_POSTGRES_URL'), 'no disposable PostgreSQL instance configured')
class PostgresTest(unittest.TestCase):
    def test_private_storage_and_worker(self):
        import psycopg
        from psycopg import sql
        from urllib.parse import urlsplit, parse_qsl, urlencode, urlunsplit
        base = os.environ['TEST_POSTGRES_URL']
        schema = 'pilot_test_' + uuid4().hex
        with psycopg.connect(base, autocommit=True) as admin:
            admin.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
            try:
                parts = urlsplit(base)
                opts = dict(parse_qsl(parts.query))
                opts['options'] = '-csearch_path=' + schema
                isolated = urlunsplit(parts._replace(query=urlencode(opts)))
                now = datetime(2026,11,25,tzinfo=timezone.utc)
                s = Store(isolated, 'x'*32, publish=True, clock=lambda:now)
                s.init()
                token = s.enroll(s.invite())
                day = monday(now)
                s.entry('put',token,day,'440106','none',None,True)
                self.assertEqual(s.entry('get',token,day)['region_code'],'440106')
                now += timedelta(weeks=1)
                s.maintain()
                self.assertEqual(s.latest('440106')['status'],'suppressed')
                s.entry('delete',token,day)
            finally:
                admin.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))
