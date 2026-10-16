"""Defining controller trial with explicit root/store/reviewer/executor doubles."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import tempfile
import types
import unittest
from unittest.mock import patch, Mock

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('commands',ROOT/'authorization/command-policy.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class Commands(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.root=Path(tmp.name)
        authority=self.root/'authority';authority.write_text('publication-a')
        current=self.root/'current';current.symlink_to(authority)
        self.config=dict(commands=dict(enable=True,entries={'status':dict(executable='/nix/store/'+'a'*32+'-program/bin/status',arguments=['--fixed'],rationale='Read fixed status',mode='review',timeout=1)}),
            clientUid=1000,operatorUid=1001,modelReviewEnabled=True,commandState=str(self.root),commandAuthority=str(authority),commandCurrentAuthority=str(current),model='gpt-6-luna',effort='high')
        self.request=dict(version=1,operation='status',task='fixture',reason='Inspect requested state',authority=hashlib.sha256(authority.read_bytes()).hexdigest())
        self.calls=[]; self.reviews=[]
        self.inspect=lambda entry:dict(path=entry['executable'],sha256='abc')
        real_lstat=Path.lstat
        def owned_path(path,*args,**kwargs):
            value=list(real_lstat(path,*args,**kwargs));value[4]=0;return os.stat_result(value)
        p=patch.object(Path,'lstat',owned_path);p.start();self.addCleanup(p.stop)
        real_fstat=os.fstat
        def owned(fd):
            value=real_fstat(fd);return types.SimpleNamespace(st_mode=value.st_mode,st_uid=0)
        for target,value in [('geteuid',lambda:0),('fstat',owned)]:
            p=patch.object(m.os,target,value);p.start();self.addCleanup(p.stop)
        p=patch.object(m,'immutable',lambda p:Path(p));p.start();self.addCleanup(p.stop)
        p=patch.object(m,'state_directory',lambda c:self.root);p.start();self.addCleanup(p.stop)
    def approve(self,entry,binding):
        self.reviews.append(binding);return dict(binding,approved=True,summary='bounded fixture')
    def run_command(self,**kw):
        return m.process(self.config,self.request,1000,inspect=self.inspect,reviewer=kw.pop('reviewer',self.approve),
            executor=lambda e,b:self.calls.append(b) or {'ok':True},**kw)
    def test_allowed_and_cached_exact_request(self):
        self.run_command();self.run_command();self.assertEqual(len(self.reviews),1) # root ownership is an explicit fixture double
        self.assertEqual(len(self.calls),2)
    def test_expired_cache_policy_and_revoked_publication(self):
        self.run_command(now=lambda:1000);self.run_command(now=lambda:1001)
        self.assertEqual(len(self.reviews),1)
        self.run_command(now=lambda:1121);self.assertEqual(len(self.reviews),2)
        self.config['commands']['entries']['status']['rationale']='Changed authority rationale'
        self.run_command(now=lambda:1122);self.assertEqual(len(self.reviews),3)
        (self.root/'current').unlink();(self.root/'current').symlink_to(self.root/'revoked')
        with self.assertRaises((m.Rejected,OSError)):self.run_command()
        self.assertEqual(len(self.calls),4)

    def test_denial_error_wrong_binding_do_not_execute(self):
        for reviewer in (lambda e,b:dict(b,approved=False,summary='no'),lambda e,b:dict(b,program='replacement',approved=True,summary='bad'),lambda e,b:(_ for _ in ()).throw(RuntimeError('SECRET'))):
            with self.assertRaises(m.Rejected):self.run_command(reviewer=reviewer)
        self.assertEqual(self.calls,[])
    def test_default_off_unknown_fields_wrong_uid(self):
        self.config['commands']['enable']=False
        with self.assertRaises(m.Rejected):self.run_command()
        self.config['commands']['enable']=True
        for request in (dict(self.request,operation='unknown'),dict(self.request,arguments=['evil']),dict(self.request,snapshot={})):
            with self.assertRaises(m.Rejected):m.selected(self.config,request,1000,inspect=self.inspect)
        with self.assertRaises(m.Rejected):m.selected(self.config,self.request,1001,inspect=self.inspect)
    def test_replaced_program_args_and_publication_during_review(self):
        for mutation in (lambda:self.config['commands']['entries']['status']['arguments'].append('new'),
                         lambda:self.config['commands']['entries']['status'].update(executable='/nix/store/'+'b'*32+'-new/bin/x'),
                         lambda:(self.root/'current').unlink()):
            original=copy.deepcopy(self.config)
            def review(e,b):mutation();return dict(b,approved=True,summary='old')
            with self.assertRaises((m.Rejected,OSError)):self.run_command(reviewer=review)
            self.config=original
        self.assertEqual(self.calls,[])
    def test_human_requires_explicit_operator_route(self):
        self.config['commands']['entries']['status']['mode']='human'
        with self.assertRaises(m.Rejected):self.run_command()
        result=m.process(self.config,self.request,1001,operator=True,inspect=self.inspect,executor=lambda e,b:{'ok':True})
        self.assertTrue(result['ok']);self.assertEqual(self.reviews,[])
    def test_no_shell_pipelines_or_extra_arguments(self):
        for value in ('x | sh','status --anything','../status'):
            with self.assertRaises(m.Rejected):m.selected(self.config,dict(self.request,operation=value),1000,inspect=self.inspect)
        self.config['commands']['entries']['status']['arguments']=['-c','anything']
        with self.assertRaises(m.Rejected):self.run_command()

class Cleanup(unittest.TestCase):
    def test_systemctl_cleanup_timeout_still_kills_reaps_and_closes(self):
        for failing,active in ((name,state) for name in ('stop','reset-failed') for state in (False,True)):
            with self.subTest(failing=failing,active=active):
                stdout=tempfile.TemporaryFile();stderr=tempfile.TemporaryFile()
                child=types.SimpleNamespace(stdout=stdout,stderr=stderr,pid=123456,wait=Mock(return_value=0))
                selector=Mock();selector.get_map.return_value=active
                selector.select.return_value=[(types.SimpleNamespace(fileobj=stdout),None)]
                config=dict(systemdRun='/systemd-run',systemctl='/systemctl',python='/python',commandExec='/exec')
                def run(argv,**kwargs):
                    if argv[1]==failing:raise m.subprocess.TimeoutExpired(argv,5)
                    return types.SimpleNamespace(returncode=0)
                try:
                    with patch.object(m.subprocess,'Popen',return_value=child),patch.object(m.subprocess,'run',side_effect=run),patch.object(m.selectors,'DefaultSelector',return_value=selector),patch.object(m.os,'killpg') as kill,patch.object(m.os,'read',return_value=b'xx'),patch.object(m,'MAX_OUTPUT',1):
                        with self.assertRaises(m.Rejected) as error:
                            m.execute(config,dict(timeout=1,arguments=[]),dict(program='/program',programTarget='/program'))
                        self.assertEqual(error.exception.code,'command-cleanup-timeout')
                        kill.assert_called_once_with(child.pid,m.signal.SIGKILL)
                        self.assertGreaterEqual(child.wait.call_count,1 if active else 2)
                        self.assertTrue(all(call.kwargs.get('timeout',0)>0 for call in child.wait.call_args_list))
                        selector.close.assert_called_once()
                        self.assertTrue(stdout.closed);self.assertTrue(stderr.closed)
                finally:
                    stdout.close();stderr.close()

if __name__=='__main__':unittest.main()
