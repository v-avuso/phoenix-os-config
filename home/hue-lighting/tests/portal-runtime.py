import argparse, json, os, re, shlex, signal, subprocess, sys, tempfile, uuid
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sources
parser = argparse.ArgumentParser(description='Isolated Hue portal selection test; never replaces desktop services or controls lamps.')
parser.add_argument('--portal', required=True, help='Built patched Hyprland portal package')
parser.add_argument('--frontend', required=True, help='xdg-desktop-portal executable')
parser.add_argument('--picker-config', required=True, help='Built hypr/xdph.conf')
parser.add_argument('--probe-python', required=True, help='Python executable providing gi.repository.Gio')
parser.add_argument('--default-screen', type=int, default=2)
args = parser.parse_args()
portal, frontend, python = args.portal, args.frontend, args.probe_python
config_text = Path(args.picker_config).read_text()
picker = config_text.split('custom_picker_binary = ',1)[1].splitlines()[0].strip()
preferred = sources.default_monitor(sources.monitors(), args.default_screen)
original_runtime = os.environ['XDG_RUNTIME_DIR']
wayland = os.environ['WAYLAND_DISPLAY']
if not wayland.startswith('/'): wayland = original_runtime + '/' + wayland
processes = []
with tempfile.TemporaryDirectory(prefix='hue-portal-trial-') as directory:
    root=Path(directory); config=root/'config';config.mkdir()
    (config/'hypr').mkdir();(config/'xdg-desktop-portal').mkdir()
    runtime=root/'runtime';runtime.mkdir(mode=0o700)
    guarded_picker=root/'picker'
    text=Path(picker).read_text()
    assert portal+'/bin/hyprland-share-picker' in text
    text=text.replace(portal+'/bin/hyprland-share-picker', '/run/current-system/sw/bin/false')
    # Keep compositor IPC on the real session while preferences/state stay private.
    hyprctl = re.search(r'--hyprctl (\S+)', text).group(1)
    hyprctl_wrapper=root/'hyprctl'
    hyprctl_wrapper.write_text('#!/bin/sh\nexec env XDG_RUNTIME_DIR='+shlex.quote(original_runtime)+' '+shlex.quote(hyprctl)+' "$@"\n')
    hyprctl_wrapper.chmod(0o700)
    text=text.replace('--hyprctl '+hyprctl, '--hyprctl '+str(hyprctl_wrapper))
    guarded_picker.write_text(text);guarded_picker.chmod(0o700)
    (config/'hypr/xdph.conf').write_text('screencopy {\n custom_picker_binary = '+str(guarded_picker)+'\n}\n')
    (config/'xdg-desktop-portal/portals.conf').write_text('[preferred]\ndefault=hyprland\n')
    environment=dict(os.environ, XDG_CONFIG_HOME=str(config),XDG_DATA_HOME=str(root/'data'),XDG_CACHE_HOME=str(root/'cache'),XDG_CURRENT_DESKTOP='Hyprland',XDG_RUNTIME_DIR=str(runtime),WAYLAND_DISPLAY=wayland,PIPEWIRE_RUNTIME_DIR=original_runtime,XDG_DESKTOP_PORTAL_DIR=portal+'/share/xdg-desktop-portal/portals')
    with (root/'trial.log').open('wb') as log:
        try:
            bus=subprocess.Popen(['dbus-daemon','--session','--nofork','--print-address=1'],stdout=subprocess.PIPE,stderr=log,env=environment,start_new_session=True);processes.append(bus)
            address=bus.stdout.readline().decode().strip()
            assert address.startswith('unix:')
            environment['DBUS_SESSION_BUS_ADDRESS']=address
            backend=subprocess.Popen([portal+'/libexec/xdg-desktop-portal-hyprland'],stdout=log,stderr=log,env=environment,start_new_session=True);processes.append(backend)
            subprocess.run(['gdbus','wait','--session','--timeout','10','org.freedesktop.impl.portal.desktop.hyprland'],env=environment,check=True,timeout=12,stdout=log,stderr=log)
            front=subprocess.Popen([frontend],stdout=log,stderr=log,env=environment,start_new_session=True);processes.append(front)
            subprocess.run(['gdbus','wait','--session','--timeout','10','org.freedesktop.portal.Desktop'],env=environment,check=True,timeout=12,stdout=log,stderr=log)
            os.environ['XDG_RUNTIME_DIR']=str(runtime)
            try:sources.write_preference({'mode':'screen','output':preferred})
            finally:os.environ['XDG_RUNTIME_DIR']=original_runtime
            command=['systemd-run','--user','--scope','--quiet','--unit','app-'+sources.APP_ID+'-'+uuid.uuid4().hex,'env', 'DBUS_SESSION_BUS_ADDRESS='+address, 'XDG_CONFIG_HOME='+str(config), 'XDG_DATA_HOME='+str(root/'data'), 'XDG_CACHE_HOME='+str(root/'cache'), 'XDG_RUNTIME_DIR='+str(runtime),python,'-B',str(Path(__file__).with_name('portal-probe.py')),preferred]
            subprocess.run(command,check=True,timeout=45)
        except Exception:
            log.flush()
            print('Isolated portal trial failed; bounded diagnostics:')
            for line in (root/'trial.log').read_text(errors='replace').splitlines():
                if any(word in line for word in ('[ERR]', 'appid:', 'Failed to', 'not found', 'custom_picker')):
                    print(line[:300])
            raise
        finally:
            for process in reversed(processes):
                if process.poll() is None:
                    os.killpg(process.pid,signal.SIGTERM)
                    try:process.wait(timeout=3)
                    except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()
