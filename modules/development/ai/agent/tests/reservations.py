#!/usr/bin/env python3
import importlib.util
import multiprocessing as mp
import os
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest

spec = importlib.util.spec_from_file_location('reservations', Path(__file__).parents[1]/'reservations.py')
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)

class Reservations(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.now, self.boot, self.base = 100., 'boot-a', 'closure-a'
        self.e = self.engine('private', lease_seconds=10)
    def engine(self, name, **kwargs):
        return r.Engine(Path(self.tmp.name)/name, owner_uid=os.getuid(),
                        boot_id=lambda:self.boot, clock=lambda:self.now,
                        baseline=lambda:self.base, **kwargs)
    def tearDown(self): self.tmp.cleanup()
    def acquire(self, uid=1):
        return self.e.acquire(uid, 'task', 'deployment.test', self.base)
    def creds(self, a): return (a['generation'], a['capability'])
    def test_fifo(self):
        a,b,c = self.acquire(),self.acquire(2),self.acquire(3)
        self.e.release(1,*self.creds(a))
        self.assertEqual(self.e.poll(3,*self.creds(c))['state'],'queued')
        self.assertEqual(self.e.poll(2,*self.creds(b))['state'],'owned')
        self.e.release(2,*self.creds(b))
        self.assertEqual(self.e.poll(3,*self.creds(c))['state'],'owned')
    def test_dead_ticket_and_timeout(self):
        a,b = self.acquire(),self.acquire(2)
        self.now +=31
        self.assertEqual(self.e.status()['queue'],[])
        with self.assertRaises(r.Rejected): self.e.poll(2,*self.creds(b))
        e=self.engine('deadline',wait_seconds=2)
        a=e.acquire(1,'t','deployment.test',self.base)
        b=e.acquire(2,'t','deployment.test',self.base)
        self.now +=3
        with self.assertRaises(r.Rejected): e.poll(2,*self.creds(b))
    def test_authority_baseline_and_release(self):
        a=self.acquire()
        for uid,gen,token in [(2,a['generation'],a['capability']), (1,a['generation']+1,a['capability']), (1,a['generation'],'bad')]:
            with self.assertRaises(r.Rejected): self.e.renew(uid,gen,token)
        self.base='closure-b'
        with self.assertRaises(r.Rejected):
            with self.e.operation(1,*self.creds(a),'deployment.test'): pass
        self.e.release(1,*self.creds(a))
    def test_renew_expire_reboot_restart_cancel(self):
        a=self.acquire()
        self.now+=5
        self.e.renew(1,*self.creds(a),seconds=10)
        self.now+=6
        restarted=self.engine('private',lease_seconds=10)
        self.assertEqual(len(restarted.status()['owners']),1)
        b=self.acquire(2)
        self.e.cancel(2,*self.creds(b))
        self.boot='boot-b'
        self.assertEqual(self.e.status()['owners'],[])
        with self.assertRaises(r.Rejected): self.e.release(1,*self.creds(a))
        a=self.acquire()
        self.now+=11
        with self.assertRaises(r.Rejected): self.e.renew(1,*self.creds(a),seconds=10)
    def test_renew_limits(self):
        e=self.engine('limits',lease_seconds=10,max_total=20,max_renew=15)
        a=e.acquire(1,'t','deployment.test',self.base)
        with self.assertRaises(r.Rejected): e.renew(1,*self.creds(a),seconds=16)
        self.now+=9
        self.assertEqual(e.renew(1,*self.creds(a),seconds=15)['expires'],120)
        self.now=120
        with self.assertRaises(r.Rejected): e.renew(1,*self.creds(a),seconds=1)
    def test_stale_queue_mapping_and_own_advance(self):
        a,b=self.acquire(),self.acquire(2)
        with self.e.operation(1,*self.creds(a),'deployment.switch') as op:
            self.base='closure-b'
            op.advance_baseline()
        self.e.renew(1,*self.creds(a),seconds=10)
        self.e.release(1,*self.creds(a))
        with self.assertRaises(r.Rejected): self.e.poll(2,*self.creds(b))
        self.e.cancel(2,*self.creds(b))
        with self.assertRaises(r.Rejected): self.e.acquire(1,'t','deployment.build',self.base)
        e=self.engine('custom',mapping={'custom.write':'resource'})
        a=e.acquire(1,'t','custom.write',self.base)
        with e.operation(1,*self.creds(a),'custom.write'): pass
        e.mapping['custom.write']='changed'
        with self.assertRaises(r.Rejected): e.poll(1,*self.creds(a))
    def test_recovery_and_held_gate(self):
        a=self.acquire()
        with self.assertRaises(r.Rejected): self.e.force_unlock(a['generation']+1,'recover')
        with self.e.operation(1,*self.creds(a),'deployment.test'):
            self.e.force_unlock(a['generation'],'recover')
            b=self.acquire(2)
            with self.assertRaises(r.Busy):
                with self.e.operation(2,*self.creds(b),'deployment.switch'): pass
        with self.e.operation(2,*self.creds(b),'deployment.rollback'): pass
    def test_queue_bounds_and_secret_storage(self):
        e=self.engine('bounded',queue_limit=2,uid_queue_limit=1)
        a=e.acquire(1,'t','deployment.test',self.base)
        e.acquire(2,'t','deployment.test',self.base)
        with self.assertRaises(r.Rejected): e.acquire(2,'t','deployment.test',self.base)
        e.acquire(3,'t','deployment.test',self.base)
        with self.assertRaises(r.Rejected): e.acquire(4,'t','deployment.test',self.base)
        self.assertNotIn(a['capability'],repr(e.status()))
        self.assertNotIn(a['capability'],e.database.read_bytes().decode('latin1'))
    def test_private_state_validation(self):
        bad=Path(self.tmp.name)/'bad';bad.mkdir(mode=0o755)
        with self.assertRaises(r.Rejected): self.engine('bad')
        link=Path(self.tmp.name)/'link';link.symlink_to(self.e.directory)
        with self.assertRaises(r.Rejected): self.engine('link')
        os.chmod(self.e.database,0o644)
        with self.assertRaises(r.Rejected): self.e.status()
    def test_two_process_gate_and_expired_owner(self):
        a=self.acquire()
        recv,send=mp.Pipe(False)
        def child():
            with self.e.operation(1,*self.creds(a),'deployment.test'):
                send.send('held')
                time.sleep(.4)
        p=mp.Process(target=child);p.start()
        self.assertEqual(recv.recv(),'held')
        self.now+=11
        b=self.acquire(2)
        with self.assertRaises(r.Busy):
            with self.e.operation(2,*self.creds(b),'deployment.boot'): pass
        p.join(3);self.assertEqual(p.exitcode,0)
        with self.e.operation(2,*self.creds(b),'deployment.boot'): pass
    def test_poll_liveness_and_bounded_database_wait(self):
        a,b=self.acquire(),self.acquire(2)
        self.e.renew(1,*self.creds(a),seconds=100)
        self.now+=20
        self.e.poll(2,*self.creds(b))
        self.now+=20
        self.assertEqual(len(self.e.status()['queue']),1)
        self.now+=11
        self.assertEqual(self.e.status()['queue'],[])
        e=self.engine('busy',busy_seconds=.05)
        db=sqlite3.connect(e.database,isolation_level=None)
        try:
            db.execute('BEGIN IMMEDIATE')
            start=time.monotonic()
            with self.assertRaises(r.Busy): e.status()
            self.assertLess(time.monotonic()-start,.5)
        finally: db.close()
    def test_two_process_acquisition(self):
        output=mp.Queue()
        def child(uid):
            e=self.engine('concurrent')
            output.put(e.acquire(uid,'task','deployment.test',self.base)['state'])
        children=[mp.Process(target=child,args=(uid,)) for uid in (1,2)]
        for child in children: child.start()
        states=[output.get(timeout=3) for _ in children]
        for child in children:
            child.join(3)
            self.assertEqual(child.exitcode,0)
        self.assertEqual(sorted(states),['owned','queued'])
    def test_child_fd_survives_parent_exit(self):
        a=self.acquire()
        recv,send=mp.Pipe(False)
        def parent():
            with self.e.operation(1,*self.creds(a),'deployment.test') as op:
                import subprocess,sys
                child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(.6)'],pass_fds=(op.gate_fd,))
                send.send(child.pid)
                os._exit(0)
        p=mp.Process(target=parent);p.start();recv.recv();p.join(3)
        self.e.release(1,*self.creds(a));b=self.acquire(2)
        with self.assertRaises(r.Busy):
            with self.e.operation(2,*self.creds(b),'deployment.test'): pass
        time.sleep(.7)
        with self.e.operation(2,*self.creds(b),'deployment.test'): pass

if __name__=='__main__': unittest.main()
