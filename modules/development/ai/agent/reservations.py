"""Broker-private testing reservations; preparation only, no callers enabled.

All identities, baseline readers and semantic mappings must come from the server.
This module performs no authentication and never executes a caller-selected command.
"""
import contextlib
import fcntl
import hashlib
import hmac
import os
import re
from pathlib import Path
import secrets
import sqlite3
import stat
import subprocess
import time


class Rejected(Exception):
    pass


class Busy(Rejected):
    pass


DEFAULT_MAPPING = {f'deployment.{name}': 'system-testing' for name in
                   ('test', 'switch', 'boot', 'update', 'override', 'rollback')}


class Engine:
    def __init__(self, directory, *, baseline, mapping=None, owner_uid=0,
                 boot_id=None, clock=time.monotonic, lease_seconds=900,
                 max_renew=3600, max_total=14400, wait_seconds=3600,
                 ticket_live=30, busy_seconds=2, queue_limit=64, uid_queue_limit=4):
        self.directory = Path(directory)
        self.owner_uid = owner_uid
        self.baseline = baseline
        self.boot_id = boot_id or (lambda: Path('/proc/sys/kernel/random/boot_id').read_text().strip())
        self.clock = clock
        self.mapping = dict(DEFAULT_MAPPING if mapping is None else mapping)
        if not self.mapping or len(self.mapping)>64 or any(not isinstance(k, str) or not re.fullmatch(r'[a-z][a-z0-9-]*\.[a-z][a-z0-9-]*', k) or
                                   not isinstance(v, str) or not v or len(v)>128
                                   for k, v in self.mapping.items()):
            raise ValueError('invalid semantic mapping')
        for value, maximum in ((lease_seconds, 900), (max_renew, 3600),
                               (max_total, 14400), (wait_seconds, 3600),
                               (ticket_live, 30), (busy_seconds, 2),
                               (queue_limit, 256), (uid_queue_limit, 16)):
            if not 0 < value <= maximum:
                raise ValueError('reservation bound exceeded')
        self.lease_seconds, self.max_renew, self.max_total = lease_seconds, max_renew, max_total
        self.wait_seconds, self.ticket_live = wait_seconds, ticket_live
        self.busy_seconds = busy_seconds
        self.queue_limit, self.uid_queue_limit = queue_limit, uid_queue_limit
        # Directory ancestry must not traverse a symlink. The final private
        # directory protects SQLite sidecars as well as the database itself.
        for parent in [self.directory, *self.directory.parents]:
            if parent.is_symlink():
                raise Rejected('symlink state directory')
            if self.owner_uid == 0 and parent != self.directory and parent.exists():
                info = parent.stat()
                if info.st_uid != 0 or info.st_mode & 0o022:
                    raise Rejected('production state ancestry must be root-owned and non-writable')
        self.directory.mkdir(mode=0o700, parents=False, exist_ok=True)
        self._validate(self.directory, directory=True)
        self.database = self.directory / 'state.sqlite3'
        os.close(self._open_private(self.database))
        with self._transaction() as db:
            schema = '''CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS tickets (
 generation INTEGER PRIMARY KEY, uid INTEGER NOT NULL, task TEXT NOT NULL,
 command TEXT NOT NULL, resource TEXT NOT NULL, secret TEXT NOT NULL,
 baseline TEXT NOT NULL, state TEXT NOT NULL, created REAL NOT NULL,
 deadline REAL NOT NULL, live REAL NOT NULL, acquired REAL, expires REAL);
CREATE TABLE IF NOT EXISTS operations (
 resource TEXT PRIMARY KEY, generation INTEGER NOT NULL, command TEXT NOT NULL,
 started REAL NOT NULL, operation_id TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS recovery (
 generation INTEGER NOT NULL, reason_hash TEXT NOT NULL, at REAL NOT NULL);
'''
            for statement in schema.split(';'):
                if statement.strip():
                    db.execute(statement)
            db.execute("INSERT OR IGNORE INTO meta VALUES ('generation','0')")
            self._sweep(db)

    def _validate(self, path, directory=False):
        s = path.lstat()
        expected = stat.S_ISDIR if directory else stat.S_ISREG
        if not expected(s.st_mode) or s.st_uid != self.owner_uid or s.st_mode & 0o077:
            raise Rejected('state must be private and owned by configured server UID')
        if not directory and s.st_nlink != 1:
            raise Rejected('linked state file')

    def _open_private(self, path):
        fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
        try:
            self._validate(path)
            if os.fstat(fd).st_ino != path.lstat().st_ino:
                raise Rejected('state replaced')
        except BaseException:
            os.close(fd)
            raise
        return fd

    @contextlib.contextmanager
    def _transaction(self):
        self._validate(self.directory, directory=True)
        self._validate(self.database)
        for suffix in ('-journal', '-wal', '-shm'):
            sidecar = Path(str(self.database)+suffix)
            if sidecar.exists() or sidecar.is_symlink():
                self._validate(sidecar)
        db = sqlite3.connect(self.database, timeout=self.busy_seconds, isolation_level=None)
        db.row_factory = sqlite3.Row
        try:
            db.execute('BEGIN IMMEDIATE')
            yield db
            db.commit()
        except sqlite3.OperationalError as error:
            db.rollback()
            raise Busy('reservation database busy or unavailable') from error
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def _sweep(self, db):
        boot = self.boot_id()
        previous = db.execute("SELECT value FROM meta WHERE key='boot'").fetchone()
        if previous is None or previous[0] != boot:
            db.execute('DELETE FROM tickets')
            db.execute('DELETE FROM operations')
            db.execute("INSERT OR REPLACE INTO meta VALUES ('boot',?)", (boot,))
        now = self.clock()
        db.execute("DELETE FROM tickets WHERE (state='owned' AND expires<=?) OR "
                   "(state='queued' AND (deadline<=? OR live<=?))", (now, now, now))

    def _resource(self, command):
        try:
            return self.mapping[command]
        except (KeyError, TypeError):
            raise Rejected('unmapped semantic command') from None

    @staticmethod
    def _hash(capability):
        if not isinstance(capability, str) or len(capability)>128:
            raise Rejected('invalid capability')
        return hashlib.sha256(capability.encode()).hexdigest()

    def _ticket(self, db, uid, generation, capability):
        self._sweep(db)
        row = db.execute('SELECT * FROM tickets WHERE generation=?', (generation,)).fetchone()
        if row is None or row['uid'] != uid or not hmac.compare_digest(row['secret'], self._hash(capability)):
            raise Rejected('invalid or stale reservation')
        if self.mapping.get(row['command']) != row['resource']:
            raise Rejected('semantic mapping changed')
        return row

    def _promote(self, db, row):
        if row['state'] == 'owned':
            return row
        if row['baseline'] != self.baseline():
            raise Rejected('baseline changed; resubmit acquisition')
        first = db.execute("SELECT generation FROM tickets WHERE resource=? AND state='queued' "
                           'ORDER BY generation LIMIT 1', (row['resource'],)).fetchone()
        owner = db.execute("SELECT 1 FROM tickets WHERE resource=? AND state='owned'", (row['resource'],)).fetchone()
        if not owner and first and first[0] == row['generation']:
            now = self.clock()
            db.execute("UPDATE tickets SET state='owned', acquired=?, expires=? WHERE generation=?",
                       (now, now+self.lease_seconds, row['generation']))
        return db.execute('SELECT * FROM tickets WHERE generation=?', (row['generation'],)).fetchone()

    @staticmethod
    def _view(row):
        return {key: row[key] for key in ('generation', 'uid', 'task', 'command', 'resource',
                                         'state', 'deadline', 'acquired', 'expires')}

    def acquire(self, uid, task, command, expected_baseline):
        resource = self._resource(command)
        if type(uid) is not int or uid<0 or not isinstance(task, str) or not 0<len(task)<=256 or any(ord(c)<32 or ord(c)==127 for c in task):
            raise Rejected('invalid owner metadata')
        with self._transaction() as db:
            self._sweep(db)
            if expected_baseline != self.baseline():
                raise Rejected('baseline changed; resubmit acquisition')
            if db.execute("SELECT count(*) FROM tickets WHERE state='queued'").fetchone()[0]>=self.queue_limit or db.execute(
                    "SELECT count(*) FROM tickets WHERE state='queued' AND uid=?", (uid,)).fetchone()[0]>=self.uid_queue_limit:
                raise Rejected('reservation queue full')
            generation = int(db.execute("SELECT value FROM meta WHERE key='generation'").fetchone()[0])+1
            db.execute("UPDATE meta SET value=? WHERE key='generation'", (str(generation),))
            token, now = secrets.token_hex(32), self.clock()
            db.execute('INSERT INTO tickets VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
                       (generation, uid, task, command, resource, self._hash(token), expected_baseline,
                        'queued', now, now+self.wait_seconds, now+self.ticket_live, None, None))
            row = db.execute('SELECT * FROM tickets WHERE generation=?', (generation,)).fetchone()
            result = self._view(self._promote(db, row))
            result['capability'] = token
            return result

    def poll(self, uid, generation, capability):
        with self._transaction() as db:
            row = self._ticket(db, uid, generation, capability)
            if row['state']=='queued':
                db.execute('UPDATE tickets SET live=? WHERE generation=?',
                           (min(self.clock()+self.ticket_live, row['deadline']), generation))
            return self._view(self._promote(db, row))

    def renew(self, uid, generation, capability, *, seconds=900):
        if not 0<seconds<=self.max_renew:
            raise Rejected('renewal bound exceeded')
        with self._transaction() as db:
            row = self._ticket(db, uid, generation, capability)
            if row['state']!='owned' or row['baseline'] != self.baseline():
                raise Rejected('owner or baseline changed')
            expires = min(self.clock()+seconds, row['acquired']+self.max_total)
            if expires<=self.clock():
                raise Rejected('total lease bound reached')
            db.execute('UPDATE tickets SET expires=? WHERE generation=?', (expires, generation))
            return {'generation': generation, 'expires': expires}

    def _remove(self, uid, generation, capability, state):
        with self._transaction() as db:
            row = self._ticket(db, uid, generation, capability)
            if row['state']!=state:
                raise Rejected('unexpected reservation state')
            db.execute('DELETE FROM tickets WHERE generation=?', (generation,))

    def release(self, uid, generation, capability):
        self._remove(uid, generation, capability, 'owned')

    def cancel(self, uid, generation, capability):
        self._remove(uid, generation, capability, 'queued')

    def status(self):
        with self._transaction() as db:
            self._sweep(db)
            rows = db.execute('SELECT * FROM tickets ORDER BY generation').fetchall()
            return {'owners': [self._view(r) for r in rows if r['state']=='owned'],
                    'queue': [self._view(r) for r in rows if r['state']=='queued'],
                    'operations': [dict(r) for r in db.execute('SELECT * FROM operations')]}

    def force_unlock(self, expected_generation, reason):
        """Authenticated-operator adapter only. Never clears an execution flock."""
        if not isinstance(reason, str) or not 0<len(reason)<=512 or any(ord(c)<32 or ord(c)==127 for c in reason):
            raise Rejected('invalid recovery reason')
        with self._transaction() as db:
            self._sweep(db)
            row = db.execute("SELECT * FROM tickets WHERE generation=? AND state='owned'", (expected_generation,)).fetchone()
            if row is None:
                raise Rejected('owner generation changed')
            db.execute('DELETE FROM tickets WHERE resource=?', (row['resource'],))
            db.execute('INSERT INTO recovery VALUES (?,?,?)',
                       (expected_generation, self._hash(reason), self.clock()))
            # Keep audit bounded independently of server adapter logging.
            db.execute('DELETE FROM recovery WHERE rowid NOT IN (SELECT rowid FROM recovery ORDER BY rowid DESC LIMIT 64)')

    @contextlib.contextmanager
    def operation(self, uid, generation, capability, command):
        """Hold through mutation AND rollback. Detached children must inherit gate_fd.

        Use run_child for a foreground child; never exit this context while a
        mutation child can still run. The inherited descriptor is independently
        authoritative even if the parent dies, until all inheritors close it.
        """
        resource = self._resource(command)
        path = self.directory / ('gate-'+hashlib.sha256(resource.encode()).hexdigest())
        fd = self._open_private(path)
        operation_id = secrets.token_hex(16)
        try:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise Busy('mutation still running') from None
            with self._transaction() as db:
                row = self._ticket(db, uid, generation, capability)
                if row['state']!='owned' or row['resource']!=resource or row['baseline']!=self.baseline():
                    raise Rejected('operation owner, mapping or baseline changed')
                db.execute('INSERT OR REPLACE INTO operations VALUES (?,?,?,?,?)',
                           (resource, generation, command, self.clock(), operation_id))
            yield Operation(self, fd, uid, generation, capability, operation_id)
        finally:
            # Close, never explicitly LOCK_UN: an inherited child FD must retain
            # the lock if the parent disappears or unwinds unexpectedly.
            os.close(fd)
            with self._transaction() as db:
                db.execute('DELETE FROM operations WHERE operation_id=?', (operation_id,))


class Operation:
    def __init__(self, engine, gate_fd, uid, generation, capability, operation_id):
        self.engine, self.gate_fd = engine, gate_fd
        self.uid, self.generation, self.capability = uid, generation, capability
        self.operation_id = operation_id

    def run_child(self, argv, *, timeout, **kwargs):
        """Server-selected argv only; finite timeout, child always reaped.

        Rollback remains the adapter's responsibility inside the operation context.
        Detached grandchildren require an adapter that explicitly preserves gate_fd.
        """
        if not 0<timeout<=14400 or 'pass_fds' in kwargs or 'start_new_session' in kwargs:
            raise Rejected('invalid child lifetime')
        return subprocess.run(argv, timeout=timeout, pass_fds=(self.gate_fd,), **kwargs)

    def advance_baseline(self):
        """Call only after the server proves its own successful mutation."""
        with self.engine._transaction() as db:
            row = self.engine._ticket(db, self.uid, self.generation, self.capability)
            record = db.execute('SELECT 1 FROM operations WHERE operation_id=? AND generation=?',
                                (self.operation_id, self.generation)).fetchone()
            if row['state']!='owned' or not record:
                raise Rejected('operation no longer owned')
            db.execute('UPDATE tickets SET baseline=? WHERE generation=?',
                       (self.engine.baseline(), self.generation))
