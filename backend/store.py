"""Private pilot data. All SQL parameters are bound, including on SQLite."""
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
from uuid import uuid4

from .regions import REGIONS, ancestry

CHINA = timezone(timedelta(hours=8))
WEEK = timedelta(days=7)
SYMPTOMS = ('new', 'ongoing', 'none')
OBSERVATIONS = ('more', 'usual', 'less')
DDL = (
    'CREATE TABLE IF NOT EXISTS invites (digest TEXT PRIMARY KEY, expires BIGINT NOT NULL)',
    'CREATE TABLE IF NOT EXISTS members (id TEXT PRIMARY KEY, digest TEXT UNIQUE NOT NULL)',
    "CREATE TABLE IF NOT EXISTS entries (member TEXT NOT NULL REFERENCES members(id) ON DELETE CASCADE, week TEXT NOT NULL, region TEXT NOT NULL, symptom TEXT NOT NULL CHECK (symptom IN ('new','ongoing','none')), observation TEXT CHECK (observation IN ('more','usual','less')), PRIMARY KEY(member,week))",
    'CREATE INDEX IF NOT EXISTS entries_week ON entries(week)',
    'CREATE TABLE IF NOT EXISTS releases (week TEXT PRIMARY KEY, payload TEXT NOT NULL)',
)


class Problem(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def monday(now):
    day = now.astimezone(CHINA).date()
    return day - timedelta(days=day.weekday())


class Store:
    def __init__(self, url, key, retention=8, publish=False, clock=None):
        if len(key.encode()) < 32 or not (5 <= retention <= 26):
            raise ValueError('32-byte secret and retention between 5 and 26 weeks required')
        if not url.startswith(('sqlite:///', 'postgresql://')):
            raise ValueError('Unsupported database URL')
        self.url, self.key, self.retention, self.publish = url, key.encode(), retention, publish
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    @classmethod
    def configured(cls):
        return cls(os.environ['DATABASE_URL'], os.environ['TOKEN_PEPPER'],
                   int(os.getenv('RETENTION_WEEKS', '8')), os.getenv('PUBLISH_PILOT') == '1')

    @contextmanager
    def tx(self, write=False, snapshot=False):
        pg = self.url.startswith('postgresql://')
        if pg:
            import psycopg
            db = psycopg.connect(self.url)
        else:
            db = sqlite3.connect(self.url[len('sqlite:///'):], timeout=15)
        try:
            if pg and snapshot:
                db.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
            if not pg:
                db.execute('PRAGMA foreign_keys=ON')
                db.execute('BEGIN IMMEDIATE' if write else 'BEGIN')
            def query(sql, args=()):
                return db.execute(sql.replace('?', '%s') if pg else sql, args)
            yield query
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def init(self):
        with self.tx(True) as q:
            for sql in DDL:
                q(sql)

    def digest(self, role, value):
        return hmac.new(self.key, (role + ':' + value).encode(), hashlib.sha256).hexdigest()

    def invite(self):
        value = secrets.token_urlsafe(32)
        with self.tx(True) as q:
            q('INSERT INTO invites(digest,expires) VALUES (?,?)',
              (self.digest('invite', value), int(self.clock().timestamp()) + 86400))
        return value

    def enroll(self, invite):
        token = secrets.token_urlsafe(32)
        with self.tx(True) as q:
            used = q('DELETE FROM invites WHERE digest=? AND expires>?',
                     (self.digest('invite', invite), int(self.clock().timestamp())))
            if used.rowcount != 1:
                raise Problem(403, 'Invite unavailable')
            q('INSERT INTO members(id,digest) VALUES (?,?)', (str(uuid4()), self.digest('bearer', token)))
        return token

    def entry(self, action, token, day, region=None, symptom=None, observation=None, consent=False):
        current = monday(self.clock())
        with self.tx(action != 'get') as q:
            member = q('SELECT id FROM members WHERE digest=?', (self.digest('bearer', token),)).fetchone()
            if not member:
                raise Problem(401, 'Invalid credential')
            if day.weekday() or not current - WEEK*(self.retention-1) <= day <= current:
                raise Problem(422, 'Expected a Monday in the retention window')
            pk = member[0], day.isoformat()
            if action == 'delete':
                q('DELETE FROM entries WHERE member=? AND week=?', pk)
                return
            if action == 'put':
                if consent is not True or region not in REGIONS or region == '000000' or symptom not in SYMPTOMS or observation not in (None, *OBSERVATIONS):
                    raise Problem(422, 'Invalid check-in or consent')
                if day == current:
                    q('INSERT INTO entries(member,week,region,symptom,observation) VALUES (?,?,?,?,?) ON CONFLICT(member,week) DO UPDATE SET region=excluded.region,symptom=excluded.symptom,observation=excluded.observation', (*pk, region, symptom, observation))
                else:
                    q('UPDATE entries SET region=?,symptom=?,observation=? WHERE member=? AND week=?', (region,symptom,observation,*pk))
            elif action != 'get':
                raise ValueError('Invalid action')
            row = q('SELECT region,symptom,observation FROM entries WHERE member=? AND week=?', pk).fetchone()
            if not row:
                raise Problem(404, 'No check-in')
            return dict(date=pk[1], region_code=row[0], symptom=row[1], observation=row[2])

    def maintain(self):
        """Only compute the immediately preceding closed week; never revise a release."""
        now = self.clock()
        current = monday(now)
        target = current - WEEK
        cutoff = (current - WEEK*(self.retention-1)).isoformat()
        with self.tx(True, snapshot=True) as q:
            q('DELETE FROM entries WHERE week<?', (cutoff,))
            q('DELETE FROM invites WHERE expires<=?', (int(now.timestamp()),))
            q('DELETE FROM releases WHERE week<?', (cutoff,))
            if not self.publish or q('SELECT 1 FROM releases WHERE week=?', (target.isoformat(),)).fetchone():
                return
            from .statistics import release
            data = q('SELECT week,member,region,symptom FROM entries WHERE week>=? AND week<=?',
                     ((target - 3*WEEK).isoformat(), target.isoformat()))
            result = release(target, data)
            q('INSERT INTO releases(week,payload) VALUES (?,?) ON CONFLICT(week) DO NOTHING',
              (target.isoformat(), json.dumps(result,separators=(',',':'))))

    def latest(self, code):
        if code not in REGIONS:
            raise Problem(422, 'Unknown region')
        target = monday(self.clock()) - WEEK
        out = dict(status='unavailable', requested_region_code=code, requested_level=REGIONS[code]['level'],
                   region_code=None, level=None, week_start=None, week_end=None, metrics=None)
        if not self.publish:
            return out
        with self.tx() as q:
            row = q('SELECT payload FROM releases WHERE week=?', (target.isoformat(),)).fetchone()
        if row:
            out.update(status='suppressed', week_start=target.isoformat(), week_end=(target+timedelta(days=6)).isoformat())
            released = json.loads(row[0])
            for parent in ancestry(code):
                if parent in released:
                    out.update(status='available', region_code=parent, level=REGIONS[parent]['level'], metrics=released[parent])
                    break
        return out
