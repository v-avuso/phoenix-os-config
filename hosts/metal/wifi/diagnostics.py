"""Fixed, temporary WCN7850 diagnostics; never resets or reconnects the adapter."""
import json
import ipaddress
import concurrent.futures
from collections import deque
import logging
import logging.handlers
import os
from pathlib import Path
import queue
import re
import signal
import subprocess
import sys
import threading
import time

IFACE = 'wlp12s0'
MASK = Path('/sys/module/ath12k/parameters/debug_mask')
# WMI + QMI. MAC can dump keys; PCI prints on every external interrupt.
DEBUG_MASK = 0x42
TRACE = Path('/sys/kernel/tracing/instances/phoenix-wifi')
STATE = Path('/var/lib/phoenix-wifi-diagnostics')
RUNTIME = Path('/run/phoenix-wifi-diagnostics')
EVENTS = (
    'mac80211/drv_start', 'mac80211/drv_stop', 'mac80211/drv_config',
    'mac80211/drv_sta_state', 'mac80211/drv_flush',
    'mac80211/drv_return_int',
    'mac80211/drv_hw_scan', 'mac80211/drv_cancel_hw_scan',
    'mac80211/api_connection_loss',
    'cfg80211/cfg80211_send_auth_timeout',
    'cfg80211/cfg80211_send_assoc_failure', 'cfg80211/rdev_return_int',
)


def buffer_kib(cpus):
    if not 1 <= cpus <= 8192:
        raise ValueError('CPU count exceeds the 32 MiB trace budget')
    # Reserve half for native ring-buffer padding; verify actual allocation too.
    return max(4, (16384 // cpus // 4) * 4)


class Incident:
    def __init__(self):
        self.deadline = None
        self.armed = False

    def arm(self):
        self.armed = True

    def observe(self, message, now):
        if IFACE + ': CTRL-EVENT-CONNECTED' in message:
            self.arm()
        # NetworkManager deliberately leaves during suspend/manual disconnect.
        # A peer-originated leave or kernel-reported connection loss still counts.
        planned_leave = ('CTRL-EVENT-DISCONNECTED' in message
                         and re.search(r'\breason=3\b', message)
                         and re.search(r'\blocally_generated=1\b', message))
        loss = self.armed and not planned_leave and IFACE + ':' in message and (
            'CTRL-EVENT-DISCONNECTED' in message or
            ('Connection to AP ' in message and ' lost' in message))
        if loss and self.deadline is None:
            self.deadline = now + 60
            return True
        return False

    def finished(self, now):
        return self.deadline is not None and now >= self.deadline


def make_log(directory, size=8 * 1024 * 1024):
    os.umask(0o027)
    log = logging.getLogger('phoenix-wifi-' + str(directory))
    log.setLevel(logging.INFO)
    handler = logging.handlers.RotatingFileHandler(
        directory / 'events.jsonl', maxBytes=size, backupCount=3)
    handler.setFormatter(logging.Formatter('%(message)s'))
    log.addHandler(handler)
    return log


def record(log, kind, **fields):
    log.info(json.dumps(dict(time=time.time(), monotonic=time.monotonic(),
                            kind=kind, **fields)))


def run(args):
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=3)
        return dict(rc=result.returncode, out=result.stdout[:65536],
                    err=result.stderr[:2048])
    except (OSError, subprocess.TimeoutExpired) as error:
        return dict(error=type(error).__name__)


def setup_trace():
    # cpu/possible includes offline CPUs, which also own allocated trace buffers.
    ranges = Path('/sys/devices/system/cpu/possible').read_text().strip().split(',')
    cpus = sum(int(r.split('-')[-1]) - int(r.split('-')[0]) + 1 for r in ranges)
    TRACE.mkdir()  # Refuse to take over an existing tracing instance.
    (RUNTIME / 'trace-owned').touch()
    (TRACE / 'tracing_on').write_text('0')
    (TRACE / 'buffer_size_kb').write_text(str(buffer_kib(cpus)))
    actual = int((TRACE / 'buffer_total_size_kb').read_text())
    if actual > 32768:
        raise RuntimeError('kernel trace allocation exceeds the 32 MiB limit')
    (TRACE / 'trace_clock').write_text('mono')
    for event in EVENTS:
        (TRACE / 'events' / event / 'enable').write_text('1')
    (TRACE / 'tracing_on').write_text('1')


def read_tail(stream, limit):
    chunks = deque()
    size = total = 0
    while chunk := stream.read(65536):
        chunks.append(chunk)
        size += len(chunk)
        total += len(chunk)
        while size > limit:
            first = chunks.popleft()
            excess = min(len(first), size - limit)
            if excess < len(first):
                chunks.appendleft(first[excess:])
            size -= excess
    return b''.join(chunks), total


def snapshot(name, log):
    if not (RUNTIME / 'trace-owned').exists():
        return
    (TRACE / 'tracing_on').write_text('0')
    try:
        # Reading trace, unlike trace_pipe, is non-consuming and bounded.
        with (TRACE / 'trace').open('rb') as source:
            data, total = read_tail(source, 16 * 1024 * 1024)
        (STATE / name).write_bytes(data)
        record(log, 'trace-snapshot', file=name, bytes=len(data),
               formatted_bytes=total, truncated=total > len(data))
    finally:
        (TRACE / 'tracing_on').write_text('1')


def remember(path, text):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(text)
    temporary.replace(path)


def cleanup():
    failures = []
    network = RUNTIME / 'network-logging.json'
    if network.exists():
        try:
            level, domains = json.loads(network.read_text())
            result = run(['nmcli', 'general', 'logging', 'level', level, 'domains', domains])
            if result.get('rc') != 0:
                raise RuntimeError('NetworkManager unavailable')
            network.unlink()
        except (OSError, ValueError, RuntimeError):
            failures.append('could not restore NetworkManager logging')
    # Restore independent state even when another cleanup action fails.
    previous = RUNTIME / 'previous-mask'
    if previous.exists():
        try:
            if MASK.exists():
                MASK.write_text(previous.read_text())
            previous.unlink()
        except OSError:
            failures.append('could not restore driver debug mask')
    owned = RUNTIME / 'trace-owned'
    if owned.exists():
        try:
            if TRACE.exists():
                (TRACE / 'tracing_on').write_text('0')
                (TRACE / 'events/enable').write_text('0')
                TRACE.rmdir()
            owned.unlink()
        except OSError:
            failures.append('could not remove owned trace instance')
    if failures:
        raise RuntimeError('; '.join(failures))


def sample(log):
    # A module reload resets the mask. Re-enable only the default zero value.
    try:
        if MASK.exists() and int(MASK.read_text(), 0) == 0:
            MASK.write_text(str(DEBUG_MASK))
    except OSError as error:
        record(log, 'debug-mask-unavailable', error=type(error).__name__)
    commands = {
        'link': ['iw', 'dev', IFACE, 'link'],
        'station': ['iw', 'dev', IFACE, 'station', 'dump'],
        'power_save': ['iw', 'dev', IFACE, 'get', 'power_save'],
        'device': ['nmcli', '-f', 'GENERAL.STATE,GENERAL.CONNECTION,IP4.GATEWAY',
                   'device', 'show', IFACE],
        'routes': ['ip', '-4', 'route', 'show', 'default', 'dev', IFACE],
    }
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        futures = {key: pool.submit(run, args) for key, args in commands.items()}
        values = {key: job.result() for key, job in futures.items()}
    words = values['routes'].get('out', '').split()
    if 'via' in words:
        try:
            gateway = str(ipaddress.IPv4Address(words[words.index('via') + 1]))
            values['gateway_ping'] = run(['ping', '-n', '-I', IFACE, '-c', '1', '-W', '1', gateway])
        except (ValueError, IndexError):
            values['gateway_ping'] = dict(error='invalid-gateway')
    values['external_ping'] = run(['ping', '-n', '-I', IFACE, '-c', '1', '-W', '1', '1.1.1.1'])
    for path in sorted(Path('/sys/kernel/debug/ath12k').glob('*/device_dp_stats'))[:4]:
        # This file exposes local counters; no HTT requests or reset writes.
        values[str(path)] = run(['head', '-c', '65536', str(path)])
    values['devcoredumps'] = [str(p) for p in Path('/sys/class/devcoredump').glob('devcd*')]
    record(log, 'sample', values=values)
    return values


def main():
    os.umask(0o027)
    if sys.argv[1:] == ['cleanup']:
        cleanup()
        return
    if sys.argv[1:]:
        raise SystemExit('No capture arguments are supported')
    log = make_log(STATE)
    # Fail clearly on a kernel without debug support, before changing its mask.
    for _ in range(60):
        if list(Path('/sys/kernel/debug/ath12k').glob('*/device_dp_stats')):
            break
        time.sleep(1)
    else:
        raise SystemExit('ath12k debugfs counters unavailable: diagnostic kernel required')
    previous = RUNTIME / 'previous-mask'
    remember(previous, MASK.read_text())
    incident = Incident()
    stop = threading.Event()
    for signum in (signal.SIGTERM, signal.SIGINT):
        signal.signal(signum, lambda *_: stop.set())
    events = queue.Queue(maxsize=1024)
    reader_done = threading.Event()
    reader_errors = []
    journal = None
    try:
        setup_trace()
        journal = subprocess.Popen([
            'journalctl', '--follow', '--since=now', '--output=json', '--no-pager',
            '_TRANSPORT=kernel', '+', '_SYSTEMD_UNIT=NetworkManager.service',
            '+', '_SYSTEMD_UNIT=wpa_supplicant.service'],
            stdout=subprocess.PIPE, text=True)

        def read_events():
            for line in journal.stdout:
                if stop.is_set():
                    break
                # Kernel debug messages are short; reject oversized records.
                if len(line) > 16384:
                    reader_errors.append('oversized journal record')
                    stop.set()
                    break
                if len(line) <= 16384:
                    try:
                        events.put(line, timeout=1)
                    except queue.Full:
                        reader_errors.append('journal queue overflow')
                        stop.set()  # Never silently drop an overflowing capture.
                        break
            reader_done.set()

        threading.Thread(target=read_events, daemon=True).start()
        original = run(['nmcli', '-t', '-e', 'no', '-f', 'LEVEL,DOMAINS', 'general', 'logging'])
        if original.get('rc') != 0:
            raise RuntimeError('cannot read NetworkManager logging baseline')
        level, domains = original['out'].strip().split(':', 1)
        remember(RUNTIME / 'network-logging.json', json.dumps([level, domains]))
        selected = {'WIFI', 'WIFI_SCAN', 'SUPPLICANT', 'DEVICE'}
        expanded = [v for v in domains.split(',') if v.split(':')[0] not in selected]
        expanded += [v + ':DEBUG' for v in sorted(selected)]
        result = run(['nmcli', 'general', 'logging', 'level', 'KEEP', 'domains', ','.join(expanded)])
        if result.get('rc') != 0:
            raise RuntimeError('cannot enable NetworkManager diagnostic logging')
        MASK.write_text(str(DEBUG_MASK))
        record(log, 'start', kernel=os.uname().release,
               boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
               debug_mask=DEBUG_MASK,
               events=EVENTS, duration_seconds=86400)
        deadline = time.monotonic() + 86400
        next_sample = 0
        volume = 0
        while not stop.is_set() and time.monotonic() < deadline:
            now = time.monotonic()
            if incident.finished(now):
                break
            if now >= next_sample:
                values = sample(log)
                if 'authorized:\tyes' in values['station'].get('out', ''):
                    incident.arm()
                next_sample = time.monotonic() + 10
            try:
                line = events.get(timeout=0.5)
            except queue.Empty:
                if reader_done.is_set():
                    raise RuntimeError('journal reader ended unexpectedly')
                continue
            event = json.loads(line)
            message = event.get('MESSAGE', '')
            if not isinstance(message, str):
                continue
            if event.get('_TRANSPORT') != 'kernel' or re.search(r'ath12|wlp12s0', message):
                volume += len(line)
                record(log, 'journal', journal=event)
                if incident.observe(message, time.monotonic()):
                    snapshot('incident-before.trace', log)
            if incident.finished(time.monotonic()) or volume >= 256 * 1024 * 1024:
                break
        record(log, 'stop', incident=incident.deadline is not None, input_bytes=volume, errors=reader_errors)
        if reader_errors:
            raise RuntimeError('; '.join(reader_errors))
    finally:
        stop.set()
        if journal:
            journal.terminate()
            try:
                journal.wait(timeout=3)
            except subprocess.TimeoutExpired:
                journal.kill()
                journal.wait()
        try:
            snapshot('incident-after.trace', log)
        except OSError as error:
            record(log, 'snapshot-error', error=type(error).__name__)
        cleanup()


if __name__ == '__main__':
    main()
