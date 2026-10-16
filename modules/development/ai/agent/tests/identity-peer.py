"""Distinct guest identities, actual transport/broker, fixed OpenShell backend double."""
import array
import importlib.util
import json
import os
from pathlib import Path
import select
import signal
import socket
import subprocess
import sys
import time


def backend(config, args):
    workspace=Path(config['workspace'])
    with (workspace/'visits').open('a') as stream:stream.write('visit\n')
    mode=args[1] if len(args)==2 and args[0]=='--' else None
    if mode=='cancel':
        child=subprocess.Popen([config['python'],'-c','import time;time.sleep(30)'])
        (workspace/'child.pid').write_text(str(child.pid))
        def stop(*_):
            try:child.wait(timeout=3)
            except subprocess.TimeoutExpired:child.kill();child.wait(timeout=3)
            (workspace/'stopped').write_text('stopped');raise SystemExit(0)
        signal.signal(signal.SIGTERM,stop)
        print('READY',flush=True)
        time.sleep(30);return 1
    if mode!='probe':return 1
    incoming=sys.stdin.readline().strip()
    diagnostic=subprocess.run([config['admin'],'--task','identity-peer','--reason','Bounded disposable identity proof','kernel-journal','5'],capture_output=True,timeout=15)
    hidden=False
    try:Path('/home/operator/unrelated-secret').read_text()
    except OSError:hidden=True
    (workspace/'agent-created').write_text('agent')
    print('fixture-stderr',file=sys.stderr)
    print(json.dumps(dict(uid=os.getuid(),cwd=str(Path.cwd()),stdin=incoming,
                         diagnosticOk=diagnostic.returncode==0,unrelatedHomeHidden=hidden)))
    return 7


def as_user(config, uid, argv, **kwargs):
    # Noninteractive probes must not inherit the driver TTY across user IDs.
    if "input" not in kwargs and "stdin" not in kwargs: kwargs["stdin"]=subprocess.DEVNULL
    return subprocess.run([config['setpriv'],'--reuid='+str(uid),'--regid=users','--init-groups',*argv],**kwargs)


def direct_broker():
    # No human helper/preflight can obscure the socket's actual execution decision.
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as connection:
        connection.connect('/run/phoenix-admin/socket')
        connection.sendall(json.dumps(dict(args=['kernel-journal','5'],reason='Bounded UID denial proof')).encode()+b'\n')
        connection.shutdown(socket.SHUT_WR);data=bytearray()
        while True:
            try:block=connection.recv(8192)
            except ConnectionResetError:break
            if not block:break
            data.extend(block)
        response=json.loads(data) if data else {'ok':False}
    print(json.dumps(dict(socketReachable=True,executionAllowed=response.get('ok',False))))
    return 0


def malformed_rights(config):
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as connection:
        connection.settimeout(5);connection.connect('/run/phoenix-agent/launch.sock')
        with open('/dev/null','rb') as source:
            frame=json.dumps(dict(args=['probe'],cwd=config['workspace'])).encode()+b'\n'
            connection.sendmsg([frame],[(socket.SOL_SOCKET,socket.SCM_RIGHTS,array.array('i',[source.fileno(),source.fileno()]))])
        try:reply=connection.recv(1024)
        except ConnectionResetError:reply=b''
    if reply:raise ValueError('malformed-rights-accepted')
    return 0


def driver(config):
    workspace=Path(config['workspace']);workspace.mkdir(mode=0o700)
    os.chown(workspace,config['operatorUid'],100)
    secret=Path('/home/operator/unrelated-secret');secret.write_text('disposable-private');secret.chmod(0o600);os.chown(secret,config['operatorUid'],100)
    private=Path('/var/lib/phoenix-agent/private-canary');private.write_text('disposable-private');private.chmod(0o600);os.chown(private,config['agentUid'],config['agentGid'])
    spec=importlib.util.spec_from_file_location('setup',config['setup']);setup=importlib.util.module_from_spec(spec);spec.loader.exec_module(setup)
    # Real descriptor-relative ACL helper, not full identity migration/setup.
    acl=dict(uid=config['agentUid'],operatorUid=config['operatorUid'],setfacl=config['setfacl'])
    setup.acl(acl,'/home/operator',writable=False);setup.acl(acl,str(workspace),recursive=True)
    launch='/run/current-system/sw/bin/phoenix-agent-launch'
    first=as_user(config,1000,[launch,'probe'],cwd=workspace,input=b'descriptor-fixture\n',capture_output=True,timeout=20)
    assert first.returncode==7,first.stderr.decode()
    result=json.loads(first.stdout)
    assert result==dict(uid=config['agentUid'],cwd=str(workspace),stdin='descriptor-fixture',diagnosticOk=True,unrelatedHomeHidden=True),result
    assert first.stderr==b'fixture-stderr\n',first.stderr
    # Operator remains able to use its original home and edit normally-created files.
    edit="from pathlib import Path;Path('agent-created').write_text('operator');assert Path('/home/operator/unrelated-secret').read_text()=='disposable-private'"
    assert as_user(config,1000,[config['python'],'-c',edit],cwd=workspace).returncode==0
    read="from pathlib import Path;Path('/var/lib/phoenix-agent/private-canary').read_text()"
    assert as_user(config,1000,[config['python'],'-c',read],capture_output=True).returncode!=0
    for uid in (1000,1001):
        query=as_user(config,uid,[config['python'],'-I',__file__,sys.argv[1],'direct-broker'],capture_output=True,timeout=10)
        assert query.returncode==0,query.stderr
        assert json.loads(query.stdout)==dict(socketReachable=True,executionAllowed=False)
    print('identity-peer stage=uid-negative-complete',flush=True)
    assert as_user(config,1001,[launch,'probe'],cwd='/tmp',capture_output=True,timeout=10).returncode!=0
    print('identity-peer stage=outsider-launch-denied',flush=True)
    before=(workspace/'visits').read_text()
    assert as_user(config,1000,[config['python'],'-I',__file__,sys.argv[1],'bad-rights'],capture_output=True,timeout=10).returncode==0
    print('identity-peer stage=bad-rights-denied',flush=True)
    assert (workspace/'visits').read_text()==before
    assert as_user(config,1000,[launch,'probe'],cwd='/tmp',capture_output=True,timeout=10).returncode!=0
    print('identity-peer stage=outside-workspace-denied',flush=True)
    # Signal forwarding through real client/service must reap the fixed backend group.
    argv=[config['setpriv'],'--reuid=1000','--regid=users','--init-groups',launch,'cancel']
    process=subprocess.Popen(argv,cwd=workspace,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        assert select.select([process.stdout],[],[],10)[0]
        assert process.stdout.readline()==b'READY\n'
        print('identity-peer stage=cancellation-ready',flush=True)
        child=int((workspace/'child.pid').read_text())
        process.terminate();process.communicate(timeout=12)
        assert process.returncode==0
        assert (workspace/'stopped').exists()
        assert not Path('/proc/'+str(child)).exists()
    finally:
        if process.poll() is None:process.kill();process.communicate(timeout=5)
    print('identity-peer stage=cancellation-cleaned',flush=True)
    Path('/tmp/identity-peer-proof.json').write_text(json.dumps(dict(passed=True,operatorUid=1000,agentUid=config['agentUid'],
        realTransport=True,realBrokerDiagnostic=True,directUIDDenied=True,narrowHomeMask=True,workspaceACL=True,
        malformedRightsDenied=True,cancellationReaped=True,openshell='explicit-backend/readiness-double',
        migration=False,model=False,exactCodexPackageAdmission=False)))
    return 0


if __name__=='__main__':
    config=json.loads(Path(sys.argv[1]).read_text());mode=sys.argv[2]
    if mode=='backend':raise SystemExit(backend(config,sys.argv[3:]))
    if mode=='direct-broker':raise SystemExit(direct_broker())
    if mode=='bad-rights':raise SystemExit(malformed_rights(config))
    if mode=='driver':raise SystemExit(driver(config))
    raise SystemExit('invalid fixture mode')
