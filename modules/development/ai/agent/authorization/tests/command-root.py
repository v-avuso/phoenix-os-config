"""Disposable root/controller/socket trial. No model or native authentication."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

config=json.loads(Path(sys.argv[1]).read_text())
spec=importlib.util.spec_from_file_location('commands',config['commandLibrary']);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
authority=hashlib.sha256(Path(config['commandAuthority']).read_bytes()).hexdigest()
def request(name):return dict(version=1,operation=name,task='fixture',reason='Bounded disposable proof',authority=authority)
def call(name,uid=1000,extra=None):
    read,write=os.pipe();pid=os.fork()
    if pid==0:
        try:
            os.close(read);os.setgid(100);os.setuid(uid)
            query=request(name);query.update(extra or {})
            with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as client:
                client.settimeout(330);client.connect('/run/command-root.sock');client.sendall(json.dumps({'command':query}).encode()+b'\n');client.shutdown(socket.SHUT_WR)
                data=bytearray()
                while True:
                    block=client.recv(8192)
                    if not block:break
                    data.extend(block)
                os.write(write,data)
        finally:os._exit(0)
    os.close(write);data=bytearray()
    while True:
        block=os.read(read,8192)
        if not block:break
        data.extend(block)
    os.close(read);os.waitpid(pid,0)
    return json.loads(data)

identity=m.program(config['commands']['entries']['identity'])
assert identity['path'].startswith('/nix/store/')
assert call('identity')['stdout']=='0\n' # actual multicall ELF argv[0]
for name in ('denied','error','wrong','timeout-review'):
    result=call(name);assert not result['ok'],result
assert call('timeout-review')['code']=='command-review-timeout'
assert not call('unknown')['ok']
assert not call('identity',uid=1001)['ok']
assert not call('identity',extra={'arguments':['-g']})['ok']
assert not call('identity',extra={'snapshot':{}})['ok']
assert not call('human')['ok']
assert call('reviewed')['ok'];visits=Path('/var/lib/command-review/visits').read_text().count('reviewed')
assert call('reviewed')['ok'];assert Path('/var/lib/command-review/visits').read_text().count('reviewed')==visits
for path in Path(config['commandState']).glob('*.json'):
    value=json.loads(path.read_text());value['created']=time.time()-130;value['expires']=time.time()-10;path.write_text(json.dumps(value))
assert call('reviewed')['ok'];assert Path('/var/lib/command-review/visits').read_text().count('reviewed')==visits+1
assert not call('flood')['ok']
controls=call('controls');assert controls['ok'] and '\x00' in controls['stdout']
assert len(json.dumps(controls).encode()) <= 6*65536+16384
start=time.monotonic();assert not call('slow')['ok'];assert time.monotonic()-start<10
# setsid grandchild must remain in and die with the fixed transient cgroup.
time.sleep(4);assert not Path('/tmp/escaped-command').exists()
# Fresh authentication is explicitly doubled; helper still checks operator UID.
data=json.dumps({'command':request('human')}).encode()+b'\n'
argv=[config['python'],'-I',config['controller'],sys.argv[1],'command-operator']
result=subprocess.run(argv,input=data,capture_output=True,env={'PKEXEC_UID':'1001'},check=True)
assert json.loads(result.stdout)['ok']
result=subprocess.run(argv,input=data,capture_output=True,env={'PKEXEC_UID':'1000'},check=True)
assert not json.loads(result.stdout)['ok']
# Ordinary authentication cannot masquerade as a critical review override.
review_data=json.dumps({'command':request('reviewed')}).encode()+b'\n'
result=subprocess.run(argv,input=review_data,capture_output=True,env={'PKEXEC_UID':'1001'},check=True)
assert not json.loads(result.stdout)['ok']
critical=[*argv[:-1],'command-critical']
result=subprocess.run(critical,input=review_data,capture_output=True,env={'PKEXEC_UID':'1001'},check=True)
assert json.loads(result.stdout)['ok']
result=subprocess.run(critical,input=review_data,capture_output=True,env={'PKEXEC_UID':'1000'},check=True)
assert not json.loads(result.stdout)['ok']
# Revoke while old daemon/helper/config/cache remain available.
current=Path(config['commandCurrentAuthority']);current.unlink();current.symlink_to(sys.argv[2])
assert not call('reviewed')['ok']
result=subprocess.run(argv,input=data,capture_output=True,env={'PKEXEC_UID':'1001'},check=True)
assert not json.loads(result.stdout)['ok']
Path('/tmp/command-root-proof.json').write_text(json.dumps(dict(passed=True,actualRootSocket=True,multicallELF=True,
    cacheReuseExpiry=True,oldHelperRevocation=True,setsidCgroupCleanup=True,model='explicit-double',authentication='explicit-double')))
