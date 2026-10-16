"""Protected Podman gate, optionally real gateway; no provider or migration."""
import importlib.util
import json
import os
import socket
from pathlib import Path
import subprocess
import sys
import time

CONTAINER='phoenix-identity-keepid-gate'


def bridge(config):
    # Fixed bridge replaces Codex/history semantics only. Caller args cannot select commands.
    if sys.argv[3:] != ['--','probe']: return 2
    code = 'id -u; printf gateway-proof > /home/operator/workspace/gateway-created; ' + config['admin'] + ' --task identity-gateway --reason "Disposable gateway identity proof" kernel-journal 5'
    return subprocess.run([config['cli'],'sandbox','exec','--name','identity-gateway','--timeout','15','--no-tty','--','/bin/sh','-c',code],stdin=subprocess.DEVNULL,timeout=25).returncode


def denied():
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as connection:
        connection.settimeout(5);connection.connect('/run/phoenix-admin/socket')
        connection.sendall(json.dumps(dict(args=['kernel-journal','5'],reason='Disposable UID denial proof')).encode()+b'\n')
        connection.shutdown(socket.SHUT_WR); data=bytearray()
        while True:
            try:block=connection.recv(8192)
            except ConnectionResetError:break
            if not block:break
            data.extend(block)
        assert not data or json.loads(data).get('ok') is False  # Root audit below independently proves denial.
    return 0


def main(config):
    evidence=Path('/tmp/identity-openshell-evidence');evidence.mkdir(mode=0o700)
    stage='prepare';created=False;failure=None;proof=None;attached=None;gateway=config['phase']=='gateway-gate'
    remote=[config['podman'],'--remote','--url','unix:///run/phoenix-agent/private/podman.sock']
    def run(argv,*,timeout=10,agent=False,label=None,check=True,cwd=None):
        if agent:
            argv=[config['setpriv'],'--reuid='+str(config['uid']),'--regid='+str(config['gid']),'--init-groups',*argv]
        start=time.monotonic()
        if label:print(json.dumps(dict(event='probe-start',stage=stage,label=label,timeout=timeout)),flush=True)
        try:
            result=subprocess.run(argv,env=config['environment'] if agent else None,stdin=subprocess.DEVNULL,
                capture_output=True,timeout=timeout,cwd=cwd)
        except subprocess.TimeoutExpired as error:
            if label:
                (evidence/(label+'.stderr')).write_bytes((error.stderr or b'')[-8192:])
                (evidence/(label+'.json')).write_text(json.dumps(dict(stage=stage,status='timeout',elapsed=time.monotonic()-start)))
            print(json.dumps(dict(event='probe-timeout',stage=stage,label=label,elapsed=time.monotonic()-start)),flush=True)
            raise ValueError((label or stage)+'-timeout') from None
        if label:
            print(json.dumps(dict(event='probe-complete',stage=stage,label=label,status=result.returncode,elapsed=time.monotonic()-start)),flush=True)
            (evidence/(label+'.stderr')).write_bytes(result.stderr[-8192:])
            (evidence/(label+'.stdout')).write_bytes(result.stdout[-16384:])
            (evidence/(label+'.json')).write_text(json.dumps(dict(stage=stage,status=result.returncode,elapsed=time.monotonic()-start)))
        if check and result.returncode:
            print('SYNTHETIC_PROBE_DIAGNOSTIC '+str(label)+' '+result.stdout.decode(errors='replace')[-2048:]+' '+result.stderr.decode(errors='replace')[-2048:],flush=True)
            raise ValueError(stage+'-failed')
        return result
    try:
        assert config['phase'] in ('podman-keepid-gate','gateway-gate') and config['uid']==980 and config['gid']==980
        workspace=Path(config['workspace']);workspace.mkdir(mode=0o700);os.chown(workspace,config['operatorUid'],100)
        spec=importlib.util.spec_from_file_location('identity_setup',config['setup']);setup=importlib.util.module_from_spec(spec);spec.loader.exec_module(setup)
        acl=dict(uid=config['uid'],operatorUid=config['operatorUid'],setfacl=config['setfacl'])
        setup.acl(acl,'/home/operator',writable=False);setup.acl(acl,str(workspace),recursive=True)
        assert not Path('/var/lib/phoenix-agent/data/containers/storage').exists(),'guest storage was not fresh'
        assert run([config['systemctl'],'is-active','--quiet','phoenix-agent-gateway.service'],check=False).returncode!=0
        public=Path('/home/operator/public-unrelated');public.write_text('public guest canary');public.chmod(0o644)
        stage='protected-api-start'
        run([config['systemctl'],'start','phoenix-agent-podman.service'],timeout=20,label='api-start')
        properties=run([config['systemctl'],'show','phoenix-agent-podman.service','-p','User','-p','Group','-p','ProtectHome','-p','Delegate','-p','BindPaths'],label='actual-unit').stdout.decode()
        assert 'User=phoenix-agent' in properties and 'Group=phoenix-agent' in properties
        assert 'ProtectHome=tmpfs' in properties and 'Delegate=yes' in properties
        stage='manager-boundary'
        assert config['environment']['XDG_RUNTIME_DIR']=='/run/user/980'
        assert Path('/run/user/980/systemd/private').exists()
        managerProbe='import os;from pathlib import Path;assert os.getenv("XDG_DATA_HOME")=="/var/lib/phoenix-agent/data";assert os.getenv("HOME")=="/var/lib/phoenix-agent/home";assert not Path("/home/operator/public-unrelated").exists();assert Path("/home/operator/workspace").is_dir();print("manager-boundary-passed")'
        run([config['systemdRun'],'--user','--wait','--pipe','--collect','--unit=identity-manager-probe',config['python'],'-c',managerProbe],agent=True,timeout=15,label='manager-probe')
        run([config['systemctl'],'--user','start','speech-dispatcher.service'],agent=True,label='excluded-service-start')
        skipped=run([config['systemctl'],'--user','show','speech-dispatcher.service','-p','ConditionResult'],agent=True,label='excluded-service-condition').stdout
        assert b'ConditionResult=no' in skipped and not Path('/tmp/unexpected-agent-desktop').exists()
        run([config['setpriv'],'--reuid=1000','--regid=users','--init-groups',config['systemdAnalyze'],'condition','ConditionUser=!phoenix-agent'],label='operator-condition')
        ordering=run([config['systemctl'],'show','phoenix-agent-podman.service','-p','Requires','-p','After'],label='manager-ordering').stdout
        assert b'user@980.service' in ordering
        stage='protected-api-info'
        run([*remote,'info','--format','json'],agent=True,label='api-info')
        stage='image-load'
        run([*remote,'load','--input',config['workload']['archive']],agent=True,timeout=60,label='image-load')
        stage='image-identity'
        loaded=run([*remote,'image','inspect','--format','{{.Id}}','sha256:'+config['workload']['id']],agent=True,label='image-identity').stdout.decode().strip()
        assert loaded.removeprefix('sha256:')==config['workload']['id'],'loaded image ID mismatch'
        if gateway:
            for name,image in config['images'].items():
                stage='load-'+name
                run([*remote,'load','--input',image['archive']],agent=True,timeout=60,label=stage)
                assert run([*remote,'image','inspect','--format','{{.Id}}','sha256:'+image['id']],agent=True,label=name+'-id').stdout.decode().strip().removeprefix('sha256:')==image['id']
            assert config['gatewayEnvironment']['OPENSHELL_GATEWAY_CONFIG']==config['gatewayConfig']
            assert Path(config['gatewayConfig']).is_file() and not Path(config['gatewayConfig']).is_symlink()
            stage='gateway-ready'
            ready=Path('/var/lib/phoenix-agent/identity-ready');ready.touch();os.chown(ready,980,980)
            run([config['systemctl'],'start','phoenix-agent-gateway.service'],timeout=35,label='gateway-start')
            run([config['cli'],'gateway','add','--local','--name','openshell','https://127.0.0.1:17670'],agent=True,timeout=15,label='gateway-register')
            stage='sandbox-create'
            argv=[config['setpriv'],'--reuid=980','--regid=980','--init-groups',config['cli'],'sandbox','create','--name','identity-gateway','--no-auto-providers','--no-tty','--from','sha256:'+config['workload']['id'],'--policy',config['policy'],'--driver-config-json',Path(config['mounts']).read_text(),'--cpu','2','--memory','512Mi','--','/bin/sh','-c','echo GATEWAY_READY; exec sleep 180']
            stream=(evidence/'sandbox-create.stdout').open('wb');errors=(evidence/'sandbox-create.stderr').open('wb')
            attached=subprocess.Popen(argv,env=config['environment'],stdin=subprocess.DEVNULL,stdout=stream,stderr=errors)
            deadline=time.monotonic()+60
            while b'GATEWAY_READY' not in (evidence/'sandbox-create.stdout').read_bytes():
                if attached.poll() is not None:raise ValueError('sandbox-create-exited')
                if time.monotonic()>deadline:raise ValueError('sandbox-create-timeout')
                time.sleep(.5)
            healthDiagnostic=config.get('healthCheckInterval') is not None
            healthPassed=False;timerResults=[]
            if healthDiagnostic:
                stage='healthcheck-proof'
                records=json.loads(run([*remote,'ps','-a','--filter','label=openshell.managed=true','--format','json'],agent=True,label='gateway-records').stdout)
                healthResults=[];timerResults=[]
                for record in records:
                    identifier=record['Id']
                    inspected=json.loads(run([*remote,'inspect',identifier],agent=True,label='healthcheck-config-'+identifier[:12]).stdout)[0]
                    test=(inspected.get('Config',{}).get('Healthcheck') or {}).get('Test',[])
                    configured=bool(test) and test != ['NONE']
                    if configured:
                        deadline=time.monotonic()+30
                        while True:
                            observed=json.loads(run([*remote,'inspect',identifier],agent=True,label='healthcheck-wait').stdout)[0]
                            health=observed.get('State',{}).get('Health',{})
                            successful=sum(entry.get('ExitCode')==0 for entry in health.get('Log',[]))
                            if health.get('Status')=='healthy' and successful:
                                timerResults.append(dict(id=identifier,healthy=True,successfulLogs=successful));break
                            if time.monotonic()>deadline:raise ValueError('configured-healthcheck-readiness-timeout')
                            time.sleep(.5)
                    checked=run([*remote,'healthcheck','run',identifier],agent=True,timeout=10,label='healthcheck-'+identifier[:12],check=False)
                    healthResults.append(dict(id=identifier,configured=configured,test=test,status=checked.returncode,diagnostic=checked.stderr.decode(errors='replace')[-1000:],result=checked.stdout.decode(errors='replace')[-1000:]))
                (evidence/'healthcheck-results.json').write_text(json.dumps(healthResults))
                print('SYNTHETIC_HEALTHCHECK_RESULTS '+json.dumps(healthResults),flush=True)
                (evidence/'timer-healthcheck-results.json').write_text(json.dumps(timerResults))
                print('SYNTHETIC_TIMER_HEALTHCHECK_RESULTS '+json.dumps(timerResults),flush=True)
                healthPassed=any(result['configured'] and result['status']==0 for result in healthResults)

                timers=run([config['systemctl'],'--user','list-timers','--all','--full','--no-pager'],agent=True,label='healthcheck-timers').stdout
                assert any(record['Id'].encode() in timers for record in records), 'healthcheck timer missing'
            stage='operator-launcher'
            result=run([config['setpriv'],'--reuid=1000','--regid=users','--init-groups','/run/current-system/sw/bin/phoenix-agent-launch','probe'],timeout=35,label='operator-launcher',cwd=workspace)
            assert result.stdout.startswith(b'1000\n'), 'unexpected sandbox uid'
            target=workspace/'gateway-created';assert target.read_text()=='gateway-proof' and target.stat().st_uid==980
            for uid in (1000,1001):
                stage='broker-negative-'+str(uid)
                run([config['setpriv'],'--reuid='+str(uid),'--regid=users','--init-groups',config['python'],'-I',__file__,sys.argv[1],'denied'],label=stage)
            stage='broker-audit'
            audit=run(['journalctl','-t','phoenix-admin','--output=cat','--no-pager'],label='broker-audit').stdout.decode()
            for uid,outcome in ((980,'allowed'),(1000,'denied'),(1001,'denied')):
                assert any('"uid": '+str(uid) in line and '"outcome": "'+outcome+'"' in line for line in audit.splitlines())
            print('GATEWAY_LAUNCHER_BROKER_CHAIN_PASSED',flush=True)
            if healthDiagnostic:assert healthPassed, 'no configured healthcheck succeeded'
            proof=dict(passed=True,phase=config['phase'],actualProtectedPodman=True,hostUid=980,containerUid=1000,gateway=True,actualBroker=True,operatorLauncher=True,testBridge=True,regularHealthDiagnostic=healthDiagnostic,manualConfiguredHealthcheck=healthDiagnostic and healthPassed,timerDrivenHealthcheck=bool(timerResults),model=False,migration=False)
        else:
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
            if gateway:
                deadline=time.monotonic()+180
                def cleanup_run(argv,*,timeout=10,label,check=True):
                    remaining=deadline-time.monotonic()
                    if remaining<=0:raise ValueError('gateway-cleanup-deadline')
                    return run(argv,agent=True,timeout=min(timeout,remaining),label=label,check=check)
                records=cleanup_run([*remote,'ps','-aq','--no-trunc','--filter','label=openshell.managed=true'],label='gateway-container-ids').stdout.decode().split()
                assert all(len(identifier)==64 and all(c in '0123456789abcdef' for c in identifier) for identifier in records), 'invalid-captured-container-id'
                original=cleanup_run([config['cli'],'sandbox','list','--ids'],label='gateway-sandbox-ids').stdout.decode().split()
                if attached:
                    assert len(original)==1, 'expected one captured gateway sandbox'
                    stage='cleanup-delete'
                    # Let the owning gateway serialize/fence deletion, remove supervisor
                    # first and retain its 45s per-container stop safety net.
                    cleanup_run([config['cli'],'sandbox','delete','identity-gateway'],timeout=180,label='gateway-delete')
                stage='cleanup-disappearance'
                while True:
                    remaining=cleanup_run([*remote,'ps','-aq','--no-trunc','--filter','label=openshell.managed=true'],label='gateway-cleanup-check').stdout.decode().split()
                    listed=cleanup_run([config['cli'],'sandbox','list','--ids'],label='gateway-cleanup-records').stdout.decode().split()
                    if not remaining and not set(original).intersection(listed):break
                    if time.monotonic()+.5>=deadline:
                        print(json.dumps(dict(event='disappearance-timeout',remainingContainerCount=len(remaining),capturedGatewayIdCount=len(set(original).intersection(listed)))),flush=True)
                        raise ValueError('gateway-disappearance-timeout')
                    time.sleep(.5)
                timers=cleanup_run([config['systemctl'],'--user','list-units','--type=timer','--all','--full','--no-pager'],label='cleanup-timers').stdout
                assert not any(identifier.encode() in timers for identifier in records), 'owned-healthcheck-timer-remains'
                if attached:
                    try:attached.wait(timeout=5)
                    except subprocess.TimeoutExpired:attached.kill();attached.wait(timeout=3)
                stage='cleanup-gateway-stop'
                run([config['systemctl'],'stop','phoenix-agent-gateway.service'],timeout=10,label='gateway-stop')
            if created:
                removed=run([*remote,'rm','--force',CONTAINER],agent=True,timeout=15,label='cleanup',check=False)
                if removed.returncode:failure=failure or 'cleanup-failed'
                listing=run([*remote,'ps','-aq','--filter','name=^'+CONTAINER+'$'],agent=True,timeout=5,label='cleanup-check',check=False)
                if listing.returncode or listing.stdout.strip():failure=failure or 'cleanup-incomplete'
        except Exception as error:
            cleanupFailure=(str(error) or type(error).__name__) if isinstance(error,(ValueError,AssertionError)) else type(error).__name__
            print(json.dumps(dict(event='cleanup-failed',stage=stage,code=cleanupFailure)),flush=True)
            failure=failure or cleanupFailure
        report=proof if failure is None else dict(passed=False,phase=config['phase'],failure=failure,gateway=False,model=False)
        report['cleanupAttempted']=created or gateway
        if gateway and failure is None:report.update(ownedContainersCleaned=True,ownedTimersCleaned=True,gatewayRecordRemoved=True)
        (evidence/'proof.json').write_text(json.dumps(report))
    if failure and gateway:
        detail=evidence/'sandbox-create.stderr'
        if detail.exists():print('SYNTHETIC_CREATE_DIAGNOSTIC '+detail.read_text(errors='replace')[-4096:])
    print(json.dumps(report))
    return 0 if failure is None else 1


if __name__=='__main__':
    config=json.loads(Path(sys.argv[1]).read_text())
    raise SystemExit(bridge(config) if sys.argv[2:3]==['bridge'] else denied() if sys.argv[2:3]==['denied'] else main(config))
