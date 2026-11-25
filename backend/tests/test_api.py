import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient
from backend.api import create_app
from backend.store import Store


class ApiTest(unittest.TestCase):
    def setUp(self):
        with tempfile.NamedTemporaryFile(dir=Path(__file__).parent, suffix='.db', delete=False) as tmp:
            path=Path(tmp.name)
        self.addCleanup(path.unlink,missing_ok=True)
        self.store=Store('sqlite:///'+str(path),'x'*32,clock=lambda:datetime(2026,11,25,tzinfo=timezone.utc))
        self.store.init()
        self.c=TestClient(create_app(self.store))
        self.addCleanup(self.c.close)
        self.route='/v1/checkins/2026-11-23'
        self.payload=dict(region_code='440106',symptom='new',consent=True)
        resp=self.c.post('/v1/enroll',json={'invite_code':self.store.invite()})
        self.assertEqual(resp.status_code,200)
        self.assertEqual(resp.headers['cache-control'],'no-store')
        self.headers={'Authorization':'Bearer '+resp.json()['token']}

    def test_http_lifecycle(self):
        self.assertEqual(self.c.get(self.route).status_code,401)
        self.assertEqual(self.c.get(self.route,headers=self.headers).status_code,404)
        result=self.c.put(self.route,headers=self.headers,json=self.payload)
        self.assertEqual(result.json(),dict(date='2026-11-23',region_code='440106',symptom='new',observation=None))
        self.assertNotIn('access-control-allow-origin', result.headers)
        self.payload.update(region_code='110108',observation='usual',symptom='none')
        self.assertEqual(self.c.put(self.route,headers=self.headers,json=self.payload).status_code,200)
        self.assertEqual(self.c.get(self.route,headers=self.headers).json()['observation'],'usual')
        self.assertEqual(self.c.delete(self.route,headers=self.headers).status_code,204)
        self.assertEqual(self.c.get(self.route,headers=self.headers).status_code,404)

    def test_invalid_no_echo(self):
        for patch in [dict(consent='true'),dict(consent=False),dict(region_code='000000'),dict(symptom='secret'),dict(gps='secret'),dict(observation='secret')]:
            resp=self.c.put(self.route,headers=self.headers,json={**self.payload,**patch})
            self.assertEqual(resp.status_code,422)
            self.assertNotIn('secret',resp.text)
        resp=self.c.get('/v1/checkins/20261123',headers=self.headers)
        self.assertEqual(resp.status_code,422)

    def test_public_shapes(self):
        resp=self.c.get('/v1/reports/latest?region_code=110108')
        self.assertEqual(resp.headers['access-control-allow-origin'],'*')
        self.assertEqual(resp.json(),dict(status='unavailable',requested_region_code='110108',requested_level='district',week_start=None,week_end=None,metrics=None,level=None,region_code=None))
        self.assertEqual(self.c.get('/v1/reports/latest?region_code=990099').status_code,422)
        self.assertTrue(any(r['code']=='440106' for r in self.c.get('/v1/regions').json()['regions']))
        self.assertEqual(self.c.get('/v1/checkins').status_code,404)
