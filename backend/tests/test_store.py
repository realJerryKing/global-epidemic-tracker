import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from backend.regions import REGIONS, ancestry
from backend.statistics import release
from backend.store import Problem, Store, monday

DAY = date(2026, 11, 23)


class StoreTest(unittest.TestCase):
    def setUp(self):
        with tempfile.NamedTemporaryFile(dir=Path(__file__).parent, suffix='.db', delete=False) as temp:
            self.path = Path(temp.name)
        self.addCleanup(self.path.unlink, missing_ok=True)
        self.now = datetime(2026, 11, 22, 16, tzinfo=timezone.utc)
        self.s = Store('sqlite:///'+str(self.path), 'x'*32, publish=True, clock=lambda:self.now)
        self.s.init()
        self.inv = self.s.invite()
        self.token = self.s.enroll(self.inv)

    def test_calendar_regions(self):
        self.assertEqual(monday(self.now), DAY)
        self.assertEqual(monday(self.now-timedelta(seconds=1)), DAY-timedelta(days=7))
        self.assertEqual(sum(r['level']=='province' for r in REGIONS.values()), 31)
        self.assertEqual(list(ancestry('110108')), ['110108','110100','110000','000000'])
        self.assertEqual(list(ancestry('440106')), ['440106','440100','440000','000000'])

    def test_credentials(self):
        with self.assertRaises(Problem): self.s.enroll(self.inv)
        raw = self.path.read_bytes()
        self.assertNotIn(self.inv.encode(), raw)
        self.assertNotIn(self.token.encode(), raw)
        with self.assertRaises(Problem): self.s.entry('get',self.inv,DAY)
        inv = self.s.invite()
        self.now += timedelta(days=1)
        with self.assertRaises(Problem): self.s.enroll(inv)

    def test_concurrent_single_use(self):
        inv = self.s.invite()
        def use(_):
            try: return bool(self.s.enroll(inv))
            except Problem: return False
        with ThreadPoolExecutor(2) as pool:
            self.assertEqual(sum(pool.map(use,range(2))),1)

    def test_crud_owner_window(self):
        put = lambda d,r='440106',c=True: self.s.entry('put',self.token,d,r,'ongoing','more',c)
        for d,r,c in [(DAY,'110101',False),(DAY,'000000',True),(DAY,'999999',True),(DAY+timedelta(days=1),'110101',True),(DAY+timedelta(days=7),'110101',True)]:
            with self.assertRaises(Problem): put(d,r,c)
        put(DAY); put(DAY,'110108')
        token2 = self.s.enroll(self.s.invite())
        self.s.entry('delete',token2,DAY)
        with self.assertRaises(Problem): self.s.entry('get',token2,DAY)
        self.assertEqual(self.s.entry('get',self.token,DAY)['region_code'],'110108')
        self.now += timedelta(weeks=1)
        put(DAY)
        self.s.entry('delete',self.token,DAY)
        with self.assertRaises(Problem): put(DAY)
        self.s.entry('delete',self.token,DAY)
        put(DAY+timedelta(weeks=1))
        self.now += timedelta(weeks=8)
        self.s.maintain()
        with self.s.tx() as q: self.assertEqual(q('SELECT COUNT(*) FROM entries').fetchone()[0],0)

    def test_release_is_frozen(self):
        for i in range(30):
            token = self.token if i==0 else self.s.enroll(self.s.invite())
            self.s.entry('put', token, DAY, '110000','new' if i<10 else 'none','more',True)
        self.assertEqual(self.s.latest('110108')['status'],'unavailable')
        self.now += timedelta(weeks=1)
        self.s.maintain()
        first = self.s.latest('110108')
        self.assertEqual(first['region_code'],'110000')
        self.assertEqual(first['metrics'],dict(sample_band='30-59',new_share_band='30-39%',trend='insufficient_baseline'))
        self.s.entry('delete',self.token,DAY)
        self.s.maintain()
        self.assertEqual(self.s.latest('110108'),first)
        self.assertEqual(self.s.latest('000000')['status'],'suppressed')
        self.s.publish=False
        self.assertEqual(self.s.latest('110108')['status'],'unavailable')
        self.s.publish=True
        self.now+=timedelta(weeks=1)
        self.assertEqual(self.s.latest('110108')['status'],'unavailable')


class StatsTest(unittest.TestCase):
    def rows(self,n,positive,code='110108',weeks=1,offset=0):
        return [((DAY-timedelta(weeks=w)).isoformat(),f'm{i+offset}',code,'new' if i<(positive if w==0 else 5) else 'none') for w in range(weeks) for i in range(n)]

    def test_minimums(self):
        for n,p in [(29,10),(30,4),(30,26),(100,0)]:
            self.assertFalse(release(DAY,self.rows(n,p)))

    def test_complementary_suppression(self):
        data=self.rows(30,8)+self.rows(1,0,'110105',offset=30)
        out=release(DAY,data)
        self.assertIn('110100',out)
        self.assertNotIn('110108',out)

    def test_baseline_requires_repeated_cohort(self):
        data=self.rows(40,15,weeks=4)
        self.assertEqual(release(DAY,data)['110108']['trend'],'possible_rise')
        fresh=[(w,i+w,r,s) for w,i,r,s in data]
        self.assertEqual(release(DAY,fresh)['110108']['trend'],'insufficient_baseline')

    def test_national_mixing(self):
        mixed=self.rows(30,8)+self.rows(30,8,'440106',offset=30)+self.rows(30,8,'340000',offset=60)
        self.assertIn('000000',release(DAY,mixed))
        self.assertNotIn('000000',release(DAY,self.rows(90,25)+self.rows(5,2,'440106',offset=90)+self.rows(5,2,'340000',offset=95)))
