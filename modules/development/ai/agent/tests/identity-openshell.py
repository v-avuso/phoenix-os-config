"""First protected-rootless stop/go gate; no gateway or provider is started."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

CONTAINER='phoenix-identity-keepid-gate'


def main(config):
    evidence=Path('/tmp/identity-openshell-evidence');evidence.mkdir(mode=0o700)
    stage='prepare';created=False;failure=None;proof=None
    remote=[config['podman'],'--remote','--url','unix:///run/phoenix-agent/private/podman.sock']
    def run(argv,*,timeout=10,agent=False,label=None,check=True):
        if agent:
            argv=[config['setpriv'],'--reuid='+str(config['uid']),'--regid='+str(config['gid']),'--init-groups',*argv]
        start=time.monotonic()
        try:
            result=subprocess.run(argv,env=config['environment'] if agent else None,stdin=subprocess.DEVNULL,
                capture_output=True,timeout=timeout)
        except subprocess.TimeoutExpired as error:
            if label:
                (evidence/(label+'.stderr')).write_bytes((error.stderr or b'')[-8192:])
                (evidence/(label+'.json')).write_text(json.dumps(dict(stage=stage,status='timeout',elapsed=time.monotonic()-start)))
            raise ValueError(stage+'-timeout') from None
        if label:
            (evidence/(label+'.stderr')).write_bytes(result.stderr[-8192:])
            (evidence/(label+'.stdout')).write_bytes(result.stdout[-16384:])
            (evidence/(label+'.json')).write_text(json.dumps(dict(stage=stage,status=result.returncode,elapsed=time.monotonic()-start)))
        if check and result.returncode:raise ValueError(stage+'-failed')
        return result
    try:
        assert config['phase']=='podman-keepid-gate' and config['uid']==980 and config['gid']==980
        workspace=Path(config['workspace']);workspace.mkdir(mode=0o700);os.chown(workspace,config['operatorUid'],100)
        spec=importlib.util.spec_from_file_location('identity_setup',config['setup']);setup=importlib.util.module_from_spec(spec);spec.loader.exec_module(setup)
        acl=dict(uid=config['uid'],operatorUid=config['operatorUid'],setfacl=config['setfacl'])
        setup.acl(acl,'/home/operator',writable=False);setup.acl(acl,str(workspace),recursive=True)
        assert not Path('/var/lib/phoenix-agent/data/containers/storage').exists(),'guest storage was not fresh'
        assert run([config['systemctl'],'is-active','--quiet','phoenix-agent-gateway.service'],check=False).returncode!=0
        stage='protected-api-start'
        run([config['systemctl'],'start','phoenix-agent-podman.service'],timeout=20,label='api-start')
        properties=run([config['systemctl'],'show','phoenix-agent-podman.service','-p','User','-p','Group','-p','ProtectHome','-p','Delegate','-p','BindPaths'],label='actual-unit').stdout.decode()
        assert 'User=phoenix-agent' in properties and 'Group=phoenix-agent' in properties
        assert 'ProtectHome=tmpfs' in properties and 'Delegate=yes' in properties
        stage='protected-api-info'
        run([*remote,'info','--format','json'],agent=True,label='api-info')
        stage='image-load'
        run([*remote,'load','--input',config['workload']['archive']],agent=True,timeout=60,label='image-load')
        stage='image-identity'
        loaded=run([*remote,'image','inspect','--format','{{.Id}}','sha256:'+config['workload']['id']],agent=True,label='image-identity').stdout.decode().strip()
        assert loaded.removeprefix('sha256:')==config['workload']['id'],'loaded image ID mismatch'
        stage='keepid-create';created=True
        run([*remote,'create','--pull=never','--network=none','--userns=keep-id:uid=1000,gid=1000',
             '--name',CONTAINER,'--label','phoenix.identity-fixture=keepid-gate','--cpus','2','--memory','512m','--pids-limit','512',
             '--volume',str(workspace)+':'+str(workspace)+':rw','--entrypoint','/bin/sh','sha256:'+config['workload']['id'],
             '-c','exec sleep 120'],agent=True,timeout=35,label='keepid-create')
        stage='keepid-start'
        run([*remote,'start',CONTAINER],agent=True,timeout=20,label='keepid-start')
        stage='keepid-exec'
        code='test "$(id -u)" = 1000 && printf "protected-identity-fixture\\n" > '+str(workspace)+'/agent-created && id -u'
        result=run([*remote,'exec',CONTAINER,'/bin/sh','-c',code],agent=True,timeout=15,label='keepid-exec')
        assert result.stdout==b'1000\n','unexpected workload UID'
        output=workspace/'agent-created'
        assert output.stat().st_uid==config['uid'],'workspace write has wrong host UID'
        assert output.read_text()=='protected-identity-fixture\n'
        stage='mount-proof'
        mounts=json.loads(run([*remote,'inspect','--format','{{json .Mounts}}',CONTAINER],agent=True,label='mounts').stdout)
        assert any(mount.get('Source')==str(workspace) and mount.get('Destination')==str(workspace) and mount.get('RW') is True for mount in mounts)
        stage='operator-workspace-access'
        edit=[config['setpriv'],'--reuid=1000','--regid=users','--init-groups',config['python'],'-c',"from pathlib import Path;Path("+repr(str(output))+").write_text('operator')"]
        run(edit,label='operator-edit')
        assert output.read_text()=='operator'
        assert run([config['systemctl'],'is-active','--quiet','phoenix-agent-gateway.service'],check=False).returncode!=0
        proof=dict(passed=True,phase=config['phase'],actualProtectedPodman=True,hostUid=config['uid'],containerUid=1000,
                   keepId=True,narrowWorkspaceBind=True,operatorACL=True,gateway=False,model=False,migration=False)
    except Exception as error:
        failure=str(error) if isinstance(error,(ValueError,AssertionError)) else type(error).__name__
    finally:
        stage='cleanup'
        try:
            if created:
                removed=run([*remote,'rm','--force',CONTAINER],agent=True,timeout=15,label='cleanup',check=False)
                if removed.returncode:failure=failure or 'cleanup-failed'
                listing=run([*remote,'ps','-aq','--filter','name=^'+CONTAINER+'$'],agent=True,timeout=5,label='cleanup-check',check=False)
                if listing.returncode or listing.stdout.strip():failure=failure or 'cleanup-incomplete'
        except Exception:failure=failure or 'cleanup-timeout'
        report=proof if failure is None else dict(passed=False,phase=config['phase'],failure=failure,gateway=False,model=False)
        report['cleanupAttempted']=created
        (evidence/'proof.json').write_text(json.dumps(report))
    print(json.dumps(report))
    return 0 if failure is None else 1


if __name__=='__main__':
    raise SystemExit(main(json.loads(Path(sys.argv[1]).read_text())))
